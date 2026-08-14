"""A dependency-free stdio MCP server for Cangjie skeleton generation."""

from __future__ import annotations

import json
import sys
from typing import Any

from .skeleton_service import SkeletonRequest, generate_skeleton


SERVER_INFO = {"name": "x2cangjie-skeleton", "version": "1.0.0"}
TOOL_NAME = "generate_cangjie_skeleton"
TOOL_DESCRIPTION = (
    "Generate the Cangjie TODO skeleton from finalized Java-to-Cangjie type "
    "contracts, create required compatibility placeholders, and run cjpm build. "
    "This tool writes only under the current repository data/java directory."
)
INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "project": {"type": "string"},
        "model": {"type": "string"},
        "temperature": {"type": "string"},
        "suffix": {"type": "string", "default": ""},
        "include_tests": {"type": "boolean", "default": False},
        "compile_timeout": {"type": "integer", "minimum": 1, "maximum": 3600},
        "request_id": {"type": "string", "description": "UUID supplied by the workflow controller."},
    },
    "required": ["project", "model", "temperature", "request_id"],
}


def _response(message_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _error(message_id: Any, code: int, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0", "id": message_id,
        "error": {"code": code, "message": message},
    }


def handle_message(message: dict[str, Any]) -> dict[str, Any] | None:
    """Handle one JSON-RPC request; notifications intentionally return no reply."""
    message_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return _error(message_id, -32600, "request method must be a string")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        protocol_version = str(message.get("params", {}).get("protocolVersion", "2025-03-26"))
        return _response(message_id, {
            "protocolVersion": protocol_version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": SERVER_INFO,
        })
    if method == "ping":
        return _response(message_id, {})
    if method == "tools/list":
        return _response(message_id, {
            "tools": [{
                "name": TOOL_NAME,
                "description": TOOL_DESCRIPTION,
                "inputSchema": INPUT_SCHEMA,
            }]
        })
    if method != "tools/call":
        return _error(message_id, -32601, f"unsupported method: {method}")

    params = message.get("params", {})
    if params.get("name") != TOOL_NAME:
        return _error(message_id, -32602, "unknown tool")
    arguments = params.get("arguments", {})
    if not isinstance(arguments, dict):
        return _error(message_id, -32602, "tool arguments must be an object")
    try:
        result = generate_skeleton(SkeletonRequest.from_dict(arguments))
    except (TypeError, ValueError) as exc:
        return _error(message_id, -32602, str(exc))
    failed = result["status"] != "success"
    return _response(message_id, {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
        "structuredContent": result,
        "isError": failed,
    })


def main() -> int:
    for raw in sys.stdin:
        try:
            message = json.loads(raw)
            if not isinstance(message, dict):
                raise ValueError("JSON-RPC payload must be an object")
            response = handle_message(message)
        except Exception as exc:  # Protocol errors must not terminate the stdio server.
            response = _error(None, -32700, f"invalid JSON-RPC message: {exc}")
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
