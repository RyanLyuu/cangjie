from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


PROTOCOL_VERSION = "2.0"

ResolutionStatus = Literal["resolved", "unresolved"]
RequestChannel = Literal["lsp", "web"]
NullabilityStatus = Literal["nullable", "non-null", "unknown", "not-applicable"]


@dataclass(frozen=True)
class TypeEvidence:
    kind: str
    detail: str
    source: str = "schema"
    confidence: Literal["high", "medium", "low"] = "medium"
    evidence_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value != ""}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TypeEvidence":
        return cls(
            kind=str(data.get("kind", "observation")),
            detail=str(data.get("detail", "")),
            source=str(data.get("source", "schema")),
            confidence=str(data.get("confidence", "medium")),
            evidence_id=str(data.get("evidence_id", "")),
        )


@dataclass(frozen=True)
class SourceFacts:
    """Structured Java-side facts used for retrieval routing, not target decisions."""

    nullable: bool | None
    nullability: NullabilityStatus
    primitive: bool
    reference_type: bool
    array: bool
    generic: bool
    wildcard: bool
    external: bool
    project_type: bool
    type_parameter: bool
    bounded_type_parameter: bool
    collection_like: bool
    functional_interface_like: bool
    binding_mutable: bool | None
    nullability_conflict: bool = False
    operations: tuple[str, ...] = ()
    evidence: tuple[TypeEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "nullable": self.nullable,
            "nullability": self.nullability,
            "primitive": self.primitive,
            "reference_type": self.reference_type,
            "array": self.array,
            "generic": self.generic,
            "wildcard": self.wildcard,
            "external": self.external,
            "project_type": self.project_type,
            "type_parameter": self.type_parameter,
            "bounded_type_parameter": self.bounded_type_parameter,
            "collection_like": self.collection_like,
            "functional_interface_like": self.functional_interface_like,
            "binding_mutable": self.binding_mutable,
            "nullability_conflict": self.nullability_conflict,
            "operations": list(self.operations),
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class RetrievalRoute:
    topics: tuple[str, ...]
    channels: tuple[RequestChannel, ...]
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "topics": list(self.topics),
            "channels": list(self.channels),
            "reasons": list(self.reasons),
        }


@dataclass(frozen=True)
class TypeOccurrence:
    occurrence_id: str
    schema_file: str
    source_path: str
    class_key: str
    fragment_kind: Literal["class", "field", "method"]
    fragment_key: str
    variation: Literal[
        "types", "return_types", "parameters", "body_types",
        "extends", "implements", "type_parameters",
    ]
    identifier: str
    source_type: str
    source_fqn: str
    role: Literal[
        "field", "return", "parameter", "body-type",
        "extends", "implements", "type-parameter",
    ]
    symbol: str
    start_line: int
    end_line: int
    body: str
    annotations: tuple[str, ...] = ()
    modifiers: tuple[str, ...] = ()
    parameter_name: str = ""
    import_map: dict[str, str] = field(default_factory=dict, compare=False, repr=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("import_map", None)
        data["annotations"] = list(self.annotations)
        data["modifiers"] = list(self.modifiers)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TypeOccurrence":
        return cls(
            occurrence_id=str(data["occurrence_id"]),
            schema_file=str(data["schema_file"]),
            source_path=str(data.get("source_path", "")),
            class_key=str(data["class_key"]),
            fragment_kind=str(data["fragment_kind"]),
            fragment_key=str(data["fragment_key"]),
            variation=str(data["variation"]),
            identifier=str(data["identifier"]),
            source_type=str(data.get("source_type", "")),
            source_fqn=str(data.get("source_fqn", "")),
            role=str(data["role"]),
            symbol=str(data.get("symbol", "")),
            start_line=int(data.get("start_line", 0)),
            end_line=int(data.get("end_line", 0)),
            body=str(data.get("body", "")),
            annotations=tuple(data.get("annotations", ())),
            modifiers=tuple(data.get("modifiers", ())),
            parameter_name=str(data.get("parameter_name", "")),
            import_map=dict(data.get("import_map", {})),
        )


@dataclass(frozen=True)
class TargetType:
    type: str
    imports: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "imports": list(self.imports)}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TargetType | None":
        if not data or not str(data.get("type", "")).strip():
            return None
        return cls(str(data["type"]).strip(), tuple(data.get("imports", ())))


@dataclass(frozen=True)
class ToolRequest:
    request_id: str
    occurrence_id: str
    channel: RequestChannel
    operation: str
    query: dict[str, Any]
    route_topics: tuple[str, ...] = ()
    read_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolRequest":
        return cls(
            request_id=str(data["request_id"]),
            occurrence_id=str(data["occurrence_id"]),
            channel=str(data["channel"]),
            operation=str(data["operation"]),
            query=dict(data.get("query", {})),
            route_topics=tuple(data.get("route_topics", ())),
            read_only=bool(data.get("read_only", True)),
        )


@dataclass(frozen=True)
class ToolObservation:
    observation_id: str
    request_id: str
    occurrence_id: str
    channel: RequestChannel
    payload: dict[str, Any]
    evidence: tuple[TypeEvidence, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "request_id": self.request_id,
            "occurrence_id": self.occurrence_id,
            "channel": self.channel,
            "payload": self.payload,
            "evidence": [item.to_dict() for item in self.evidence],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolObservation":
        return cls(
            observation_id=str(data["observation_id"]),
            request_id=str(data["request_id"]),
            occurrence_id=str(data["occurrence_id"]),
            channel=str(data["channel"]),
            payload=dict(data.get("payload", {})),
            evidence=tuple(TypeEvidence.from_dict(item) for item in data.get("evidence", ())),
        )


@dataclass(frozen=True)
class ResolutionDecision:
    occurrence_id: str
    target: TargetType
    authority: Literal["target-fact", "llm"]
    reasoning: str
    usage_requirements: tuple[str, ...] = ()
    translation_guidance: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "occurrence_id": self.occurrence_id,
            "target": self.target.to_dict(),
            "authority": self.authority,
            "reasoning": self.reasoning,
            "usage_requirements": list(self.usage_requirements),
            "translation_guidance": list(self.translation_guidance),
            "evidence_ids": list(self.evidence_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResolutionDecision":
        target = TargetType.from_dict(data.get("target"))
        if target is None:
            raise ValueError("resolution decision requires target.type")
        authority = str(data.get("authority", ""))
        if authority not in {"target-fact", "llm"}:
            raise ValueError("resolution decision authority must be target-fact or llm")
        return cls(
            occurrence_id=str(data["occurrence_id"]),
            target=target,
            authority=authority,
            reasoning=str(data.get("reasoning", "")),
            usage_requirements=tuple(data.get("usage_requirements", ())),
            translation_guidance=tuple(data.get("translation_guidance", ())),
            evidence_ids=tuple(data.get("evidence_ids", ())),
        )


@dataclass(frozen=True)
class TypeResolutionRecord:
    resolution_id: str
    occurrence_id: str
    symbol: str
    source_type: str
    source_fqn: str
    role: str
    status: ResolutionStatus
    target: TargetType | None
    source_facts: SourceFacts
    retrieval_route: RetrievalRoute
    usage_requirements: tuple[str, ...] = ()
    translation_guidance: tuple[str, ...] = ()
    evidence: tuple[TypeEvidence, ...] = ()
    request_ids: tuple[str, ...] = ()
    observation_ids: tuple[str, ...] = ()
    decision_authority: str = ""
    reasoning: str = ""

    @property
    def cangjie_type(self) -> str:
        return self.target.type if self.target else ""

    @property
    def imports(self) -> tuple[str, ...]:
        return self.target.imports if self.target else ()

    @property
    def mapping_status(self) -> str:
        return self.status

    @property
    def mapping_kind(self) -> str:
        return self.decision_authority or "unresolved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "resolution_id": self.resolution_id,
            "occurrence_id": self.occurrence_id,
            "symbol": self.symbol,
            "source_type": self.source_type,
            "source_fqn": self.source_fqn,
            "role": self.role,
            "status": self.status,
            "target": self.target.to_dict() if self.target else None,
            "source_facts": self.source_facts.to_dict(),
            "retrieval_route": self.retrieval_route.to_dict(),
            "usage_requirements": list(self.usage_requirements),
            "translation_guidance": list(self.translation_guidance),
            "evidence": [item.to_dict() for item in self.evidence],
            "request_ids": list(self.request_ids),
            "observation_ids": list(self.observation_ids),
            "decision_authority": self.decision_authority,
            "reasoning": self.reasoning,
        }


def protocol_event(kind: str, payload: Any) -> dict[str, Any]:
    value = payload.to_dict() if hasattr(payload, "to_dict") else payload
    return {"protocol_version": PROTOCOL_VERSION, "kind": kind, kind: value}
