from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .core import TypeResolutionCore
from .models import (
    PROTOCOL_VERSION,
    ResolutionDecision,
    ToolObservation,
    TypeResolutionRecord,
    protocol_event,
)
from .protocol import load_protocol_events
from .schema_adapter import collect_project_types, extract_occurrences, materialize_records


class TypeResolutionService:
    """Project I/O around the pure TypeResolutionCore state machine."""

    def __init__(self, core: TypeResolutionCore | None = None):
        self.core = core or TypeResolutionCore()

    def resolve_project(
        self,
        schema_dir: str | Path,
        *,
        project: str,
        include_tests: bool = False,
        events_path: str | Path | None = None,
        overrides_path: str | Path | None = None,
        observations: Iterable[ToolObservation] = (),
        decisions: Iterable[ResolutionDecision] = (),
        apply: bool = False,
        output_dir: str | Path | None = None,
    ) -> tuple[list, list[TypeResolutionRecord], dict[str, Any]]:
        schema_dir = Path(schema_dir)
        occurrences = extract_occurrences(schema_dir, include_tests=include_tests)
        project_types = collect_project_types(schema_dir, include_tests=include_tests)
        input_path = events_path or overrides_path
        file_observations, file_decisions = load_protocol_events(input_path)
        all_observations = [*observations, *file_observations]
        all_decisions = [*decisions, *file_decisions]
        records, requests = self.core.finalize(
            occurrences,
            project_types=project_types,
            observations=all_observations,
            decisions=all_decisions,
        )

        materialized = materialize_records(schema_dir, occurrences, records) if apply else 0
        summary = summarize(
            project, schema_dir, occurrences, records, requests, materialized, include_tests
        )
        if output_dir:
            write_run(
                output_dir, occurrences, records, requests, summary, input_path,
                all_observations, all_decisions,
            )
        return occurrences, records, summary


def summarize(project, schema_dir, occurrences, records, requests, materialized, include_tests) -> dict[str, Any]:
    status = Counter(record.status for record in records)
    authorities = Counter(record.decision_authority or "none" for record in records)
    roles = Counter(record.role for record in records)
    channels = Counter(request.channel for request in requests)
    nullability = Counter(record.source_facts.nullability for record in records)
    topics = Counter(
        topic for record in records for topic in record.retrieval_route.topics
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "project": project,
        "schema_dir": str(schema_dir),
        "include_tests": include_tests,
        "occurrences": len(occurrences),
        "resolution_status": dict(sorted(status.items())),
        "decision_authority": dict(sorted(authorities.items())),
        "roles": dict(sorted(roles.items())),
        "source_nullability": dict(sorted(nullability.items())),
        "retrieval_topics": dict(sorted(topics.items())),
        "tool_requests": len(requests),
        "tool_request_channels": dict(sorted(channels.items())),
        "materialized": materialized,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_run(
    output_dir,
    occurrences,
    records,
    requests,
    summary,
    events_path,
    observations,
    decisions,
) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    occurrence_events = [protocol_event("occurrence", item) for item in occurrences]
    request_events = [protocol_event("tool_request", item) for item in requests]
    observation_events = [protocol_event("tool_observation", item) for item in observations]
    decision_events = [protocol_event("resolution_decision", item) for item in decisions]
    resolution_events = [protocol_event("resolution", item) for item in records]
    _write_jsonl(output / "occurrences.jsonl", occurrence_events)
    _write_jsonl(output / "tool_requests.jsonl", request_events)
    _write_jsonl(output / "resolutions.jsonl", resolution_events)
    _write_jsonl(
        output / "events.jsonl",
        occurrence_events + request_events + observation_events + decision_events + resolution_events,
    )
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    manifest = {
        "protocol_version": PROTOCOL_VERSION,
        "schema_dir": summary["schema_dir"],
        "project": summary["project"],
        "events_path": str(events_path or ""),
        "records": len(records),
        "tool_requests": len(requests),
        "format": "type-resolution-jsonl",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    path.write_text(content, encoding="utf-8")
