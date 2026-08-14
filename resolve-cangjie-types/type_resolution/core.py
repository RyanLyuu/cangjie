from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import replace
from typing import Iterable

from .models import (
    ResolutionDecision,
    RetrievalRoute,
    SourceFacts,
    TargetType,
    ToolObservation,
    ToolRequest,
    TypeEvidence,
    TypeOccurrence,
    TypeResolutionRecord,
)


SOURCE_FACT_TYPES = {
    "byte": "Int8",
    "short": "Int16",
    "int": "Int32",
    "long": "Int64",
    "float": "Float32",
    "double": "Float64",
    "boolean": "Bool",
    "char": "Rune",
    "void": "Unit",
    "Byte": "Int8",
    "Short": "Int16",
    "Integer": "Int32",
    "Long": "Int64",
    "Float": "Float32",
    "Double": "Float64",
    "Boolean": "Bool",
    "Character": "Rune",
    "Void": "Unit",
    "String": "String",
    "Object": "Any",
}

PRIMITIVES = {"byte", "short", "int", "long", "float", "double", "boolean", "char", "void"}
COMPLEX_HINTS = re.compile(r"[<>,?]|\b(?:extends|super)\b")
COLLECTION_NAMES = {
    "Collection", "List", "ArrayList", "LinkedList", "Vector", "Set", "HashSet",
    "SortedSet", "TreeSet", "Map", "HashMap", "SortedMap", "TreeMap", "Deque",
    "Queue", "Iterator", "Iterable", "Optional",
}
FUNCTIONAL_INTERFACE_NAMES = {
    "Runnable", "Callable", "Supplier", "Consumer", "Predicate", "Function",
    "BiConsumer", "BiPredicate", "BiFunction", "UnaryOperator", "BinaryOperator",
    "Comparator",
}
NUMERIC_NAMES = set(PRIMITIVES) | {
    "Byte", "Short", "Integer", "Long", "Float", "Double", "Number",
    "BigInteger", "BigDecimal",
}
VALUE_ROLES = {"field", "return", "parameter", "body-type"}


def _stable_id(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    return prefix + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def _strip_annotations(value: str) -> str:
    value = re.sub(r"@[\w.]+(?:\([^)]*\))?\s*", "", value or "")
    return re.sub(r"\s+", " ", value).strip()


def _base_type(value: str) -> str:
    source = _strip_annotations(value)
    if re.search(r"\s+(?:extends|super)\s+", source) and "<" not in source:
        source = re.split(r"\s+(?:extends|super)\s+", source, maxsplit=1)[0]
    source = source.removesuffix("...").strip()
    while source.endswith("[]"):
        source = source[:-2].strip()
    return source.split("<", 1)[0].strip()


def _short_type(value: str) -> str:
    return _base_type(value).replace("$", ".").split(".")[-1]


class TypeResolutionCore:
    """Pure two-phase resolver; it never executes LSP, web, or model tools."""

    def analyze(
        self,
        occurrences: Iterable[TypeOccurrence],
        *,
        project_types: set[str] | None = None,
    ) -> tuple[list[TypeResolutionRecord], list[ToolRequest]]:
        project_types = project_types or set()
        records: list[TypeResolutionRecord] = []
        requests: list[ToolRequest] = []
        for occurrence in occurrences:
            source_facts = self._source_facts(occurrence, project_types)
            target, authority, evidence = self._source_fact_target(
                occurrence, source_facts
            )
            route = self._retrieval_route(
                occurrence, source_facts, needs_tools=target is None
            )
            usage, guidance = self._source_requirements(occurrence, source_facts)
            occurrence_requests: list[ToolRequest] = []
            if target is None:
                occurrence_requests = self._requests_for(occurrence, route)
                requests.extend(occurrence_requests)
            records.append(
                self._record(
                    occurrence,
                    target=target,
                    authority=authority,
                    evidence=evidence,
                    requests=occurrence_requests,
                    source_facts=source_facts,
                    retrieval_route=route,
                    usage_requirements=usage,
                    translation_guidance=guidance,
                )
            )
        return records, requests

    def finalize(
        self,
        occurrences: Iterable[TypeOccurrence],
        *,
        project_types: set[str] | None = None,
        observations: Iterable[ToolObservation] = (),
        decisions: Iterable[ResolutionDecision] = (),
    ) -> tuple[list[TypeResolutionRecord], list[ToolRequest]]:
        occurrences = list(occurrences)
        baseline, requests = self.analyze(occurrences, project_types=project_types)
        by_occurrence = {item.occurrence_id: item for item in occurrences}
        requests_by_id = {item.request_id: item for item in requests}
        observations_by_occurrence: dict[str, list[ToolObservation]] = defaultdict(list)
        observation_ids: set[str] = set()
        for observation in observations:
            if observation.observation_id in observation_ids:
                raise ValueError(f"duplicate observation id: {observation.observation_id}")
            observation_ids.add(observation.observation_id)
            if observation.occurrence_id not in by_occurrence:
                raise ValueError(f"unknown observation occurrence: {observation.occurrence_id}")
            request = requests_by_id.get(observation.request_id)
            if request is None:
                raise ValueError(f"observation references unknown request: {observation.request_id}")
            if request.occurrence_id != observation.occurrence_id:
                raise ValueError("observation occurrence does not match its request")
            if request.channel != observation.channel:
                raise ValueError("observation channel does not match its request")
            observations_by_occurrence[observation.occurrence_id].append(observation)
        decisions_by_occurrence: dict[str, ResolutionDecision] = {}
        for decision in decisions:
            if decision.occurrence_id not in by_occurrence:
                raise ValueError(f"unknown decision occurrence: {decision.occurrence_id}")
            if decision.occurrence_id in decisions_by_occurrence:
                raise ValueError(f"duplicate decision occurrence: {decision.occurrence_id}")
            decisions_by_occurrence[decision.occurrence_id] = decision

        result: list[TypeResolutionRecord] = []
        for baseline_record in baseline:
            oid = baseline_record.occurrence_id
            decision = decisions_by_occurrence.get(oid)
            seen = sorted(observations_by_occurrence.get(oid, ()), key=lambda item: item.observation_id)
            if decision is None:
                if seen:
                    result.append(replace(
                        baseline_record,
                        evidence=baseline_record.evidence + tuple(
                            evidence for item in seen for evidence in item.evidence
                        ),
                        observation_ids=tuple(item.observation_id for item in seen),
                    ))
                else:
                    result.append(baseline_record)
                continue

            available_evidence = {
                item.evidence_id
                for observation in seen
                for item in observation.evidence
                if item.evidence_id
            }
            missing = sorted(set(decision.evidence_ids) - available_evidence)
            if missing:
                raise ValueError(f"decision for {oid} cites unknown evidence: {', '.join(missing)}")
            if decision.authority == "target-fact" and not decision.evidence_ids:
                raise ValueError(f"target-fact decision for {oid} requires observed evidence")
            occurrence = by_occurrence[oid]
            if (
                occurrence.role == "type-parameter"
                and re.search(r"\s+extends\s+", occurrence.source_type)
                and " where " not in decision.target.type
            ):
                raise ValueError(
                    f"bounded type-parameter decision for {oid} must include a finalized where clause"
                )
            source_usage, source_guidance = self._source_requirements(
                occurrence, baseline_record.source_facts
            )
            result.append(
                self._record(
                    occurrence,
                    target=decision.target,
                    authority=decision.authority,
                    evidence=tuple(evidence for item in seen for evidence in item.evidence),
                    requests=[request for request in requests if request.occurrence_id == oid],
                    observations=seen,
                    source_facts=baseline_record.source_facts,
                    retrieval_route=baseline_record.retrieval_route,
                    usage_requirements=source_usage + decision.usage_requirements,
                    translation_guidance=source_guidance + decision.translation_guidance,
                    reasoning=decision.reasoning,
                )
            )
        return result, requests

    def _source_facts(
        self, occurrence: TypeOccurrence, project_types: set[str]
    ) -> SourceFacts:
        source = _strip_annotations(occurrence.source_type)
        base = _base_type(source)
        short = _short_type(source)
        identity = occurrence.source_fqn or base
        identity_short = _short_type(identity)
        type_parameter = occurrence.role == "type-parameter"
        bounded_type_parameter = type_parameter and bool(
            re.search(r"\s+(?:extends|super)\s+", source)
        )
        primitive = base in PRIMITIVES
        value_occurrence = occurrence.role in VALUE_ROLES
        reference_type = value_occurrence and not primitive
        array = source.endswith("...") or source.endswith("[]")
        generic = ("<" in source and ">" in source) or bounded_type_parameter
        wildcard = "?" in source or bool(
            "<" in source and re.search(r"\b(?:extends|super)\b", source)
        )
        if "." in identity:
            project_type = identity in project_types
        else:
            project_type = any(
                candidate and candidate in project_types
                for candidate in (base, short, identity, identity_short)
            )
        external = "." in identity and not project_type

        annotations = " ".join(
            (occurrence.source_type, *occurrence.annotations, *occurrence.modifiers)
        ).lower()
        nullable_annotation = any(
            marker in annotations
            for marker in ("nullable", "checkfornull", "nullallowed")
        )
        non_null_annotation = any(
            marker in annotations
            for marker in ("nonnull", "notnull", "nullmarked")
        )
        body = occurrence.body or ""
        operations: list[str] = []
        evidence: list[TypeEvidence] = []

        if occurrence.role == "field" and re.search(r"=\s*null\b", body):
            operations.append("initialized-null")
            evidence.append(TypeEvidence(
                "nullability", "field initializer is null", "schema", "high"
            ))
        if occurrence.role == "return" and re.search(r"\breturn\s+null\s*;", body):
            operations.append("returned-null")
            evidence.append(TypeEvidence(
                "nullability", "method has a null return path", "schema", "high"
            ))
        if occurrence.role == "parameter" and occurrence.parameter_name:
            name = re.escape(occurrence.parameter_name)
            if re.search(
                rf"(?:\b{name}\s*[!=]=\s*null\b|\bnull\s*[!=]=\s*{name}\b)",
                body,
            ):
                operations.append("compared-with-null")
                evidence.append(TypeEvidence(
                    "nullability",
                    f"parameter {occurrence.parameter_name} is compared with null",
                    "schema",
                    "medium",
                ))

        nullable_path = bool(operations)
        if nullable_annotation:
            evidence.append(TypeEvidence(
                "nullability", "explicit nullable annotation", "schema", "high"
            ))
        if non_null_annotation:
            evidence.append(TypeEvidence(
                "nullability", "explicit non-null annotation", "schema", "high"
            ))

        nullable: bool | None
        nullability: str
        conflict = reference_type and (nullable_annotation or nullable_path) and non_null_annotation
        if not value_occurrence or primitive:
            nullable = None
            nullability = "not-applicable"
        elif conflict:
            nullable = None
            nullability = "unknown"
            evidence.append(TypeEvidence(
                "nullability-conflict",
                "nullable and non-null source evidence conflict",
                "schema",
                "high",
            ))
        elif nullable_annotation or nullable_path:
            nullable = True
            nullability = "nullable"
        elif non_null_annotation:
            nullable = False
            nullability = "non-null"
        else:
            nullable = None
            nullability = "unknown"

        binding_mutable = (
            False
            if occurrence.role == "field" and "final" in occurrence.modifiers
            else None
        )
        return SourceFacts(
            nullable=nullable,
            nullability=nullability,
            primitive=primitive,
            reference_type=reference_type,
            array=array,
            generic=generic,
            wildcard=wildcard,
            external=external,
            project_type=project_type,
            type_parameter=type_parameter,
            bounded_type_parameter=bounded_type_parameter,
            collection_like=short in COLLECTION_NAMES or identity_short in COLLECTION_NAMES,
            functional_interface_like=(
                short in FUNCTIONAL_INTERFACE_NAMES
                or identity_short in FUNCTIONAL_INTERFACE_NAMES
            ),
            binding_mutable=binding_mutable,
            nullability_conflict=conflict,
            operations=tuple(dict.fromkeys(operations)),
            evidence=tuple(evidence),
        )

    def _retrieval_route(
        self,
        occurrence: TypeOccurrence,
        source_facts: SourceFacts,
        *,
        needs_tools: bool,
    ) -> RetrievalRoute:
        topics: list[str] = []
        reasons: list[str] = []

        def add(topic: str, reason: str) -> None:
            if topic not in topics:
                topics.append(topic)
                reasons.append(reason)

        if source_facts.reference_type and (
            source_facts.nullable is True
            or source_facts.nullability == "unknown"
            or source_facts.nullability_conflict
        ):
            add("nullability", f"source_facts.nullability={source_facts.nullability}")
        if source_facts.collection_like:
            add("collection", "source_facts.collection_like=true")
        if (
            source_facts.generic
            or source_facts.wildcard
            or source_facts.bounded_type_parameter
        ):
            add("generic", "source type contains generic, wildcard, or bound structure")
        if source_facts.functional_interface_like:
            add("functional-interface", "source_facts.functional_interface_like=true")
        if _short_type(occurrence.source_fqn or occurrence.source_type) in NUMERIC_NAMES:
            add("numeric", "source base type is numeric")
        if source_facts.array:
            add("array", "source_facts.array=true")
        if occurrence.role in {"extends", "implements"}:
            add("inheritance", f"occurrence.role={occurrence.role}")
        if source_facts.project_type:
            add("project-type", "source_facts.project_type=true")
        if needs_tools:
            add("target-api", "no deterministic target fact resolved this occurrence")

        channels = ("lsp", "web") if needs_tools else ()
        return RetrievalRoute(tuple(topics), channels, tuple(reasons))

    def _source_fact_target(
        self,
        occurrence: TypeOccurrence,
        source_facts: SourceFacts,
    ) -> tuple[TargetType | None, str, tuple[TypeEvidence, ...]]:
        source = _strip_annotations(occurrence.source_type)
        if occurrence.role == "type-parameter":
            declaration = re.split(r"\s+(?:extends|super)\s+", source, maxsplit=1)
            name = declaration[0].strip()
            if len(declaration) > 1:
                return None, "", ()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
                return TargetType(name), "source-fact", (
                    TypeEvidence("type-parameter", f"preserve declared parameter {name}", "schema", "high"),
                )
        if source.endswith("..."):
            source = source[:-3].strip() + "[]"
        depth = 0
        while source.endswith("[]"):
            depth += 1
            source = source[:-2].strip()
        short = source.replace("$", ".").split(".")[-1]
        identity = occurrence.source_fqn or source
        if source in PRIMITIVES:
            target = SOURCE_FACT_TYPES[source]
        elif "." not in identity or identity.startswith("java.lang."):
            target = SOURCE_FACT_TYPES.get(source) or SOURCE_FACT_TYPES.get(short)
        else:
            target = None
        if target is None and not COMPLEX_HINTS.search(source) and source_facts.project_type:
            target = short
        if target is None:
            return None, "", ()
        for _ in range(depth):
            target = f"Array<{target}>"
        if source_facts.nullable is True and target != "Unit" and not target.startswith("?"):
            target = f"?{target}"
        return TargetType(target), "source-fact", (
            TypeEvidence("target-type-fact", f"deterministic target spelling {target}", "built-in-facts", "high"),
        )

    def _source_requirements(
        self, occurrence: TypeOccurrence, source_facts: SourceFacts
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        source = _strip_annotations(occurrence.source_type)
        requirements: list[str] = []
        guidance: list[str] = []
        if source_facts.nullability_conflict:
            requirements.append("source-nullability-conflict")
            guidance.append("Resolve conflicting Java nullability evidence before translating uses.")
        elif source_facts.nullable is True:
            requirements.append("source-nullable")
            guidance.append("Preserve Java null paths in the target representation.")
        elif source_facts.nullable is False:
            requirements.append("source-non-null")
        elif source_facts.nullability == "unknown":
            requirements.append("source-nullability-unknown")
        if occurrence.role == "type-parameter" and re.search(r"\s+extends\s+", source):
            bound = source.split(" extends ", 1)[1].strip()
            requirements.append(f"generic-upper-bound:{bound}")
            guidance.append("Translate the generic bound only after target constraint facts are available.")
        return tuple(requirements), tuple(guidance)

    def _requests_for(
        self, occurrence: TypeOccurrence, route: RetrievalRoute
    ) -> list[ToolRequest]:
        common = {
            "source_path": occurrence.source_path,
            "line": occurrence.start_line,
            "symbol": occurrence.symbol,
            "source_type": occurrence.source_type,
            "source_fqn": occurrence.source_fqn,
            "route_topics": list(route.topics),
        }
        requests: list[ToolRequest] = []
        if "lsp" in route.channels:
            requests.append(ToolRequest(
                _stable_id("req-", occurrence.occurrence_id, "lsp", "hover-definition"),
                occurrence.occurrence_id,
                "lsp",
                "hover-definition",
                common,
                route.topics,
            ))
        if "web" in route.channels:
            requests.append(ToolRequest(
                _stable_id("req-", occurrence.occurrence_id, "web", "target-api-search"),
                occurrence.occurrence_id,
                "web",
                "target-api-search",
                {
                    "source_type": occurrence.source_fqn or occurrence.source_type,
                    "question": "Find authoritative Cangjie target type/API facts; do not infer a mapping.",
                    "route_topics": list(route.topics),
                },
                route.topics,
            ))
        return requests

    def _record(
        self,
        occurrence: TypeOccurrence,
        *,
        target: TargetType | None,
        authority: str,
        evidence: tuple[TypeEvidence, ...],
        requests: Iterable[ToolRequest],
        source_facts: SourceFacts,
        retrieval_route: RetrievalRoute,
        observations: Iterable[ToolObservation] = (),
        usage_requirements: tuple[str, ...] = (),
        translation_guidance: tuple[str, ...] = (),
        reasoning: str = "",
    ) -> TypeResolutionRecord:
        request_ids = tuple(sorted(item.request_id for item in requests))
        observation_ids = tuple(sorted(item.observation_id for item in observations))
        target_text = target.type if target else ""
        resolution_id = _stable_id(
            "res-", occurrence.occurrence_id, target_text, authority,
            source_facts.nullability, *retrieval_route.topics,
            *usage_requirements, *translation_guidance,
        )
        return TypeResolutionRecord(
            resolution_id=resolution_id,
            occurrence_id=occurrence.occurrence_id,
            symbol=occurrence.symbol,
            source_type=occurrence.source_type,
            source_fqn=occurrence.source_fqn,
            role=occurrence.role,
            status="resolved" if target else "unresolved",
            target=target,
            source_facts=source_facts,
            retrieval_route=retrieval_route,
            usage_requirements=tuple(dict.fromkeys(usage_requirements)),
            translation_guidance=tuple(dict.fromkeys(translation_guidance)),
            evidence=evidence,
            request_ids=request_ids,
            observation_ids=observation_ids,
            decision_authority=authority,
            reasoning=reasoning,
        )
