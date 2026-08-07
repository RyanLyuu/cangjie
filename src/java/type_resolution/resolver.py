from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .agent import AgentRunner
from .models import OccurrenceResolution, ProbeResult, TypeDecision, TypeOccurrence
from .probe import CangjieTypeProbe
from .schema import (
    collect_project_types,
    load_occurrences,
    materialize_resolutions,
    schema_paths,
)


TYPE_DECISIONS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "decisions": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "occurrence_id": {"type": "string"},
                    "translated_target_type": {"type": "string"},
                    "imports": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {"type": "string"},
                },
                "required": [
                    "occurrence_id", "translated_target_type", "imports", "reasoning"
                ],
            },
        }
    },
    "required": ["decisions"],
}


@dataclass
class TypeResolutionService:
    runner: AgentRunner
    probe: CangjieTypeProbe
    workspace: Path
    project: str
    max_attempts: int = 3
    _sessions: dict[str, str] = field(default_factory=dict, init=False)
    _attempts: dict[str, int] = field(default_factory=dict, init=False)
    _feedback: dict[str, list[str]] = field(default_factory=dict, init=False)
    _resolutions: dict[str, OccurrenceResolution] = field(default_factory=dict, init=False)
    _project_types: set[str] = field(default_factory=set, init=False)

    def resolve_project(
        self,
        schema_dir: str | Path,
        *,
        include_tests: bool = False,
        output_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        paths = schema_paths(schema_dir, include_tests=include_tests)
        if not paths:
            raise ValueError(f"no schema files found in {schema_dir}")
        self.probe.ensure_available()
        self._project_types = collect_project_types(paths)
        file_summaries = []
        for path in paths:
            file_summaries.append(self.resolve_schema(path))
        summary = {
            "project": self.project,
            "schema_dir": str(schema_dir),
            "files": len(paths),
            "occurrences": len(self._resolutions),
            "resolved": sum(item.status.startswith("resolved") for item in self._resolutions.values()),
            "fallback": sum(item.status.startswith("fallback") for item in self._resolutions.values()),
            "file_results": file_summaries,
        }
        if output_dir:
            output = Path(output_dir)
            output.mkdir(parents=True, exist_ok=True)
            (output / "summary.json").write_text(
                json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            rows = [item.to_dict() for item in self._resolutions.values()]
            (output / "resolutions.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )
        return summary

    def resolve_schema(self, path: str | Path) -> dict[str, Any]:
        path = Path(path)
        schema, occurrences = load_occurrences(path)
        pending = {item.occurrence_id: item for item in occurrences}
        for occurrence in occurrences:
            self._attempts.setdefault(occurrence.occurrence_id, 0)
            self._feedback.setdefault(occurrence.occurrence_id, [])

        while pending and any(
            self._attempts[occurrence_id] < self.max_attempts for occurrence_id in pending
        ):
            active = [
                item for item in pending.values()
                if self._attempts[item.occurrence_id] < self.max_attempts
            ]
            prompt = self._initial_prompt(schema, active) if not self._sessions.get(path.name) else (
                self._retry_prompt(active)
            )
            result = self.runner.run(
                prompt,
                TYPE_DECISIONS_SCHEMA,
                workspace=self.workspace,
                session_id=self._sessions.get(path.name, ""),
            )
            if result.session_id:
                self._sessions[path.name] = result.session_id
            for occurrence in active:
                self._attempts[occurrence.occurrence_id] += 1

            if result.status != "success" or result.content is None:
                diagnostic = result.stderr or f"agent failed with return code {result.returncode}"
                for occurrence in active:
                    self._feedback[occurrence.occurrence_id].append(diagnostic)
                continue

            decisions, errors = self._parse_decisions(result.content, active)
            for occurrence in active:
                oid = occurrence.occurrence_id
                preserved = self._preserve_project_type(occurrence)
                if oid in errors and preserved is None:
                    self._feedback[oid].append(errors[oid])
                    continue
                decision = preserved or decisions.get(oid)
                if decision is None:
                    self._feedback[oid].append("Agent omitted this occurrence from decisions.")
                    continue
                probe = self.probe.probe(
                    occurrence, decision, project_types=self._project_types
                )
                if not probe.success:
                    self._feedback[oid].append(
                        "Candidate failed isolated Cangjie compilation:\n" + probe.diagnostic
                    )
                    continue
                status = "resolved-project" if preserved else "resolved"
                resolution = OccurrenceResolution(
                    occurrence=occurrence,
                    decision=decision,
                    attempts=self._attempts[oid],
                    probe=probe,
                    status=status,
                    feedback=list(self._feedback[oid]),
                )
                self._resolutions[oid] = resolution
                pending.pop(oid, None)

        for occurrence in pending.values():
            resolution = self._fallback(occurrence)
            self._resolutions[occurrence.occurrence_id] = resolution

        file_resolutions = [self._resolutions[item.occurrence_id] for item in occurrences]
        materialize_resolutions(path, file_resolutions)
        return {
            "schema_file": path.name,
            "occurrences": len(occurrences),
            "fallback": sum(item.status.startswith("fallback") for item in file_resolutions),
            "session_id": self._sessions.get(path.name, ""),
        }

    def repair_schema(self, path: str | Path, build_diagnostic: str) -> int:
        """Use remaining occurrence attempts to repair one combined skeleton failure."""
        path = Path(path)
        schema, occurrences = load_occurrences(path)
        active = [
            item for item in occurrences
            if self._attempts.get(item.occurrence_id, 0) < self.max_attempts
        ]
        if not active:
            return 0
        current = {
            item.occurrence_id: self._resolutions[item.occurrence_id].decision.to_dict()
            for item in active if item.occurrence_id in self._resolutions
        }
        prompt = (
            "The combined TODO skeleton failed cjpm build. Revise only type decisions or imports "
            "that can explain the diagnostic. Return one decision for every supplied occurrence.\n\n"
            f"BUILD DIAGNOSTIC:\n{build_diagnostic}\n\n"
            f"CURRENT DECISIONS:\n{json.dumps(current, indent=2, ensure_ascii=False)}\n\n"
            f"OCCURRENCES:\n{json.dumps([item.to_dict() for item in active], indent=2, ensure_ascii=False)}"
        )
        result = self.runner.run(
            prompt,
            TYPE_DECISIONS_SCHEMA,
            workspace=self.workspace,
            session_id=self._sessions.get(path.name, ""),
        )
        if result.session_id:
            self._sessions[path.name] = result.session_id
        for occurrence in active:
            self._attempts[occurrence.occurrence_id] = self._attempts.get(occurrence.occurrence_id, 0) + 1
        if result.status != "success" or result.content is None:
            return 0
        decisions, _ = self._parse_decisions(result.content, active)
        changed = []
        for occurrence in active:
            oid = occurrence.occurrence_id
            decision = self._preserve_project_type(occurrence) or decisions.get(oid)
            if decision is None:
                continue
            old = self._resolutions.get(oid)
            if old and old.decision == decision:
                continue
            probe = self.probe.probe(occurrence, decision, project_types=self._project_types)
            if not probe.success:
                self._feedback.setdefault(oid, []).append(probe.diagnostic)
                continue
            resolution = OccurrenceResolution(
                occurrence, decision, self._attempts[oid], probe, "resolved-build-repair",
                list(self._feedback.get(oid, ())),
            )
            self._resolutions[oid] = resolution
            changed.append(resolution)
        if changed:
            materialize_resolutions(path, changed)
        return len(changed)

    def fallback_schema(self, path: str | Path) -> int:
        _, occurrences = load_occurrences(path)
        resolutions = []
        for occurrence in occurrences:
            preserved = self._preserve_project_type(occurrence)
            if preserved:
                probe = ProbeResult(True, "project type name preserved")
                resolution = OccurrenceResolution(
                    occurrence, preserved, self._attempts.get(occurrence.occurrence_id, 0),
                    probe, "resolved-project", list(self._feedback.get(occurrence.occurrence_id, ())),
                )
            else:
                resolution = self._fallback(occurrence)
            self._resolutions[occurrence.occurrence_id] = resolution
            resolutions.append(resolution)
        materialize_resolutions(path, resolutions)
        return len(resolutions)

    def _fallback(self, occurrence: TypeOccurrence) -> OccurrenceResolution:
        preserved = self._preserve_project_type(occurrence)
        if preserved:
            decision = preserved
            status = "resolved-project"
            probe = ProbeResult(True, "project type name preserved")
        elif occurrence.role in {"extends", "implements"}:
            suffix = re.sub(
                r"[^A-Za-z0-9_]", "_", occurrence.occurrence_id.removeprefix("occ-")[:10]
            )
            name = "X2CangjieType_" + suffix
            imports = self._placeholder_import(occurrence, name)
            decision = TypeDecision(
                occurrence.occurrence_id,
                name,
                imports,
                "deterministic structural fallback after three failed attempts",
            )
            probe_decision = TypeDecision(
                occurrence.occurrence_id,
                name,
                (),
                decision.reasoning,
            )
            probe = self.probe.probe(
                occurrence, probe_decision, project_types=self._project_types,
                placeholder_names=(name,),
            )
            status = "fallback-placeholder"
        elif occurrence.role == "type-parameter":
            name = re.split(r"\s+(?:extends|super)\s+|\s+", occurrence.source_type, 1)[0]
            name = name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name or "") else "T"
            decision = TypeDecision(
                occurrence.occurrence_id, name, (),
                "deterministic unbounded type-parameter fallback after three failed attempts",
            )
            probe = self.probe.probe(occurrence, decision, project_types=self._project_types)
            status = "fallback-type-parameter"
        else:
            decision = TypeDecision(
                occurrence.occurrence_id, "Any", (),
                "deterministic value-position fallback after three failed attempts",
            )
            probe = self.probe.probe(occurrence, decision, project_types=self._project_types)
            status = "fallback-any"
        if not probe.success:
            raise RuntimeError(
                f"deterministic fallback did not compile for {occurrence.occurrence_id}: "
                f"{probe.diagnostic}"
            )
        return OccurrenceResolution(
            occurrence=occurrence,
            decision=decision,
            attempts=self._attempts.get(occurrence.occurrence_id, 0),
            probe=probe,
            status=status,
            feedback=list(self._feedback.get(occurrence.occurrence_id, ())),
        )

    def _preserve_project_type(self, occurrence: TypeOccurrence) -> TypeDecision | None:
        source = occurrence.source_type.strip()
        if any(token in source for token in ("<", "[", "]", "?", " extends ", " super ")):
            return None
        short = source.split(".")[-1]
        if source not in self._project_types and short not in self._project_types:
            return None
        return TypeDecision(
            occurrence.occurrence_id,
            short,
            (),
            "project-defined type: preserve the source name without translation",
        )

    def _placeholder_import(self, occurrence: TypeOccurrence, name: str) -> tuple[str, ...]:
        path = occurrence.source_path.replace("\\", "/")
        relative = path.rsplit("/java/", 1)[-1] if "/java/" in path else path
        if "/" not in relative:
            return ()
        package = self.project.replace("-", "_")
        return (f"import {package}.{name}",)

    def _initial_prompt(self, schema: dict, occurrences: list[TypeOccurrence]) -> str:
        return (
            "Translate every supplied Java type occurrence to a concrete Cangjie type. You are "
            "resolving a compile-only TODO skeleton, not translating method bodies. You may inspect "
            "the read-only workspace and use available LSP, terminal, or web tools. Preserve project "
            "types by name. Imports must be complete Cangjie import statements. Decisions are local "
            "to occurrence_id; do not merge identical source strings. Return exactly one decision for "
            "every occurrence and no extra occurrences.\n\n"
            f"PROJECT TYPES:\n{json.dumps(sorted(self._project_types), ensure_ascii=False)}\n\n"
            f"FILE SCHEMA:\n{json.dumps(schema, indent=2, ensure_ascii=False)}\n\n"
            f"TYPE OCCURRENCES:\n{json.dumps([item.to_dict() for item in occurrences], indent=2, ensure_ascii=False)}"
        )

    def _retry_prompt(self, occurrences: list[TypeOccurrence]) -> str:
        payload = []
        for item in occurrences:
            payload.append({
                "occurrence": item.to_dict(),
                "compiler_feedback": self._feedback.get(item.occurrence_id, []),
            })
        return (
            "Revise the failed type decisions below using the isolated Cangjie compiler feedback. "
            "Return exactly one decision for every listed occurrence. Do not repeat occurrences that "
            "are not listed.\n\n" + json.dumps(payload, indent=2, ensure_ascii=False)
        )

    @staticmethod
    def _parse_decisions(
        content: dict[str, Any], occurrences: list[TypeOccurrence]
    ) -> tuple[dict[str, TypeDecision], dict[str, str]]:
        expected = {item.occurrence_id for item in occurrences}
        decisions = {}
        errors = {}
        rows = content.get("decisions", [])
        if not isinstance(rows, list):
            return {}, {oid: "Agent response decisions is not an array." for oid in expected}
        for row in rows:
            if not isinstance(row, dict):
                continue
            decision = TypeDecision.from_dict(row)
            oid = decision.occurrence_id
            if oid not in expected:
                continue
            if oid in decisions:
                errors[oid] = "Agent returned duplicate decisions for this occurrence."
                decisions.pop(oid, None)
                continue
            if not decision.translated_target_type:
                errors[oid] = "Agent returned an empty translated_target_type."
                continue
            decisions[oid] = decision
        return decisions, errors
