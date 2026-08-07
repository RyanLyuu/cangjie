from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TypeOccurrence:
    occurrence_id: str
    schema_file: str
    source_path: str
    class_key: str
    fragment_kind: str
    fragment_key: str
    variation: str
    identifier: str
    source_type: str
    role: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    context_before: tuple[str, ...] = ()
    source_line: str = ""
    context_after: tuple[str, ...] = ()

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], *, schema_file: str, source_path: str
    ) -> "TypeOccurrence":
        return cls(
            occurrence_id=str(data["occurrence_id"]),
            schema_file=schema_file,
            source_path=source_path,
            class_key=str(data["class_key"]),
            fragment_kind=str(data["fragment_kind"]),
            fragment_key=str(data["fragment_key"]),
            variation=str(data["variation"]),
            identifier=str(data.get("identifier", data["occurrence_id"])),
            source_type=str(data.get("source_type", "")),
            role=str(data.get("role", "body-type")),
            start_line=int(data.get("start_line", 0) or 0),
            start_column=int(data.get("start_column", 0) or 0),
            end_line=int(data.get("end_line", 0) or 0),
            end_column=int(data.get("end_column", 0) or 0),
            context_before=tuple(data.get("context_before", ())),
            source_line=str(data.get("source_line", "")),
            context_after=tuple(data.get("context_after", ())),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["context_before"] = list(self.context_before)
        data["context_after"] = list(self.context_after)
        return data


@dataclass(frozen=True)
class TypeDecision:
    occurrence_id: str
    translated_target_type: str
    imports: tuple[str, ...] = ()
    reasoning: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TypeDecision":
        imports = data.get("imports", ())
        if isinstance(imports, str):
            imports = [line for line in imports.splitlines() if line.strip()]
        return cls(
            occurrence_id=str(data.get("occurrence_id", "")).strip(),
            translated_target_type=str(data.get("translated_target_type", "")).strip(),
            imports=tuple(str(item).strip() for item in imports if str(item).strip()),
            reasoning=str(data.get("reasoning", "")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_id": self.occurrence_id,
            "translated_target_type": self.translated_target_type,
            "imports": list(self.imports),
            "reasoning": self.reasoning,
        }


@dataclass(frozen=True)
class ProbeResult:
    success: bool
    diagnostic: str = ""
    command: tuple[str, ...] = ()
    source: str = ""


@dataclass
class OccurrenceResolution:
    occurrence: TypeOccurrence
    decision: TypeDecision
    attempts: int
    probe: ProbeResult
    status: str = "resolved"
    feedback: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence": self.occurrence.to_dict(),
            "decision": self.decision.to_dict(),
            "attempts": self.attempts,
            "status": self.status,
            "feedback": list(self.feedback),
            "probe": {
                "success": self.probe.success,
                "diagnostic": self.probe.diagnostic,
                "command": list(self.probe.command),
            },
        }
