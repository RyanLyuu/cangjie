from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import TypeResolutionCore
from .models import protocol_event
from .protocol import parse_protocol_rows
from .schema_adapter import collect_project_types
from .service import TypeResolutionService


def handle_request(message: dict[str, Any]) -> dict[str, Any]:
    """Thin MCP-host facade. Hosts own transport and external tool execution."""
    method = message.get("method")
    if method not in {"type_resolution/analyze", "type_resolution/finalize"}:
        raise ValueError(f"unsupported MCP facade method: {method}")
    params = dict(message.get("params", {}))
    schema_dir = Path(params["schema_dir"])
    output_dir = params.get("output_dir")
    observations, decisions = parse_protocol_rows(params.get("events", []))
    occurrences, records, summary = TypeResolutionService().resolve_project(
        schema_dir,
        project=str(params["project"]),
        include_tests=bool(params.get("include_tests", False)),
        events_path=params.get("events_path"),
        observations=observations,
        decisions=decisions,
        apply=bool(params.get("apply", False)),
        output_dir=output_dir,
    )
    _, requests = TypeResolutionCore().analyze(
        occurrences,
        project_types=collect_project_types(
            schema_dir, include_tests=bool(params.get("include_tests", False))
        ),
    )
    return {
        "protocol_version": "2.0",
        "summary": summary,
        "events": [
            *[protocol_event("occurrence", item) for item in occurrences],
            *[protocol_event("tool_request", item) for item in requests],
            *[protocol_event("resolution", item) for item in records],
        ],
        "events_path": str(Path(output_dir) / "events.jsonl") if output_dir else "",
    }
