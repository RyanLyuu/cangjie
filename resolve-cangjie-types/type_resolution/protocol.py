from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, TextIO

from .models import (
    PROTOCOL_VERSION,
    ResolutionDecision,
    TargetType,
    ToolObservation,
    TypeEvidence,
)


def parse_protocol_rows(rows: Iterable[dict[str, Any]]) -> tuple[list[ToolObservation], list[ResolutionDecision]]:
    observations: list[ToolObservation] = []
    decisions: list[ResolutionDecision] = []
    for row in rows:
        kind = row.get("kind")
        version = str(row.get("protocol_version", PROTOCOL_VERSION))
        if version != PROTOCOL_VERSION:
            raise ValueError(f"unsupported type-resolution protocol version: {version}")
        if kind == "tool_observation":
            observations.append(ToolObservation.from_dict(dict(row.get("tool_observation", {}))))
        elif kind == "resolution_decision":
            decisions.append(ResolutionDecision.from_dict(dict(row.get("resolution_decision", {}))))
        elif kind in {"occurrence", "tool_request", "resolution", None}:
            legacy = _legacy_decision(row)
            if legacy:
                decisions.append(legacy)
        else:
            raise ValueError(f"unsupported type-resolution event kind: {kind}")
    return observations, decisions


def load_protocol_events(path: str | Path | None) -> tuple[list[ToolObservation], list[ResolutionDecision]]:
    if not path:
        return [], []
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"protocol event file not found: {source}")
    text = source.read_text(encoding="utf-8").strip()
    if not text:
        return [], []
    if source.suffix == ".jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        value = json.loads(text)
        rows = value if isinstance(value, list) else value.get("events", value.get("overrides", []))
    return parse_protocol_rows(rows)


def read_jsonl(stream: TextIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream if line.strip()]


def write_jsonl(stream: TextIO, rows: Iterable[dict[str, Any]]) -> None:
    for row in rows:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _legacy_decision(row: dict[str, Any]) -> ResolutionDecision | None:
    target_value = row.get("cangjie_type") or row.get("base_cangjie_type")
    if not row.get("occurrence_id") or not target_value:
        return None
    usage: list[str] = []
    nullability = str(row.get("nullability", ""))
    if nullability:
        usage.append(f"source-nullability:{nullability}")
    reason = str(row.get("reasoning") or row.get("nullability_reason") or "explicit legacy decision")
    return ResolutionDecision(
        occurrence_id=str(row["occurrence_id"]),
        target=TargetType(str(target_value), tuple(row.get("imports", ()))),
        authority="llm",
        reasoning=reason,
        usage_requirements=tuple(usage),
        translation_guidance=tuple(row.get("translation_guidance", ())),
    )
