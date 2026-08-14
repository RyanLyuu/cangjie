"""Agent-facing skeleton stage that proves an MCP tool was invoked."""

from __future__ import annotations

import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.java.type_resolution.agent import AgentResult, AgentRunner, CodexRunner

from .skeleton_service import SkeletonRequest, _cangjie_environment, receipt_path_for


SKELETON_STAGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "request_id": {"type": "string"},
        "called_tool": {"type": "boolean"},
        "build_status": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["request_id", "called_tool", "build_status", "summary"],
}


@dataclass(frozen=True)
class SkeletonStageResult:
    status: str
    request_id: str
    build_returncode: int = 1
    diagnostic: str = ""
    receipt: dict[str, Any] | None = None


def mcp_config_args(workspace: str | Path | None = None) -> list[str]:
    """Return Codex CLI config overrides that launch this repository's MCP server."""
    root = Path(workspace or Path.cwd()).resolve()
    args = [
        "-c", f"mcp_servers.x2cangjie_skeleton.command={json.dumps(sys.executable)}",
        "-c", "mcp_servers.x2cangjie_skeleton.args=[\"-m\", \"src.java.translation.skeleton_mcp_server\"]",
        "-c", f"mcp_servers.x2cangjie_skeleton.cwd={json.dumps(str(root))}",
        "-c", "mcp_servers.x2cangjie_skeleton.tools.generate_cangjie_skeleton.approval_mode=\"auto\"",
        "-c", (
            f"projects.{json.dumps(str(root))}.trust_level=\"trusted\""
        ),
    ]
    # Codex launches the stdio MCP process independently.  Pass the resolved
    # SDK environment explicitly so the child can load libcangjie-runtime.so
    # even when the caller's shell setup is not inherited by Codex.
    environment = _cangjie_environment()
    for key in ("CANGJIE_HOME", "CANGJIE_SDK_HOME", "PATH", "LD_LIBRARY_PATH"):
        value = environment.get(key, "")
        if value:
            args.extend([
                "-c",
                f"mcp_servers.x2cangjie_skeleton.env.{key}={json.dumps(value)}",
            ])
    return args


def build_skeleton_prompt(request: SkeletonRequest) -> str:
    return f"""You are the skeleton-generation stage of a Java-to-Cangjie workflow.

The type-resolution stage has completed. You must now call the MCP tool
`x2cangjie_skeleton.generate_cangjie_skeleton` exactly once. It is the only
authorized way to generate or modify the Cangjie TODO skeleton. Do not edit
schemas or Cangjie files yourself, and do not run cjpm manually.

Call it with these exact arguments:
{json.dumps({
    'project': request.project,
    'model': request.model,
    'temperature': request.temperature,
    'suffix': request.suffix,
    'include_tests': request.include_tests,
    'compile_timeout': request.compile_timeout,
    'request_id': request.request_id,
}, ensure_ascii=False, indent=2)}

After the tool responds, output only the required JSON. Set `called_tool` to
true only if you invoked the tool; copy its request_id and status into
`request_id` and `build_status`. Summarize the tool result without suggesting
an alternative implementation."""


def new_skeleton_runner(
    *, executable: str, model: str, timeout: int,
    workspace: str | Path | None = None,
) -> CodexRunner:
    return CodexRunner(
        executable=executable,
        model=model,
        sandbox="workspace-write",
        timeout=timeout,
        extra_args=mcp_config_args(workspace),
        # Non-interactive Codex otherwise cancels write-capable MCP calls.
        # The MCP tool itself validates all paths and command inputs; the
        # agent prompt forbids direct shell/file edits.
        bypass_approvals_and_sandbox=True,
    )


def _read_receipt(request: SkeletonRequest, workspace: Path) -> dict[str, Any] | None:
    path = receipt_path_for(request, workspace)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def run_skeleton_stage(
    runner: AgentRunner,
    request: SkeletonRequest,
    *,
    workspace: str | Path,
) -> SkeletonStageResult:
    """Ask an agent to invoke the tool, then trust only the MCP receipt."""
    workspace = Path(workspace).resolve()
    agent_result: AgentResult = runner.run(
        build_skeleton_prompt(request), SKELETON_STAGE_SCHEMA, workspace=workspace
    )
    receipt = _read_receipt(request, workspace)
    if agent_result.status != "success" or agent_result.content is None:
        return SkeletonStageResult(
            "agent_failed", request.request_id,
            diagnostic=agent_result.stderr or "skeleton agent did not return structured output",
            receipt=receipt,
        )
    if str(agent_result.content.get("request_id", "")) != request.request_id:
        return SkeletonStageResult(
            "agent_invalid_response", request.request_id,
            diagnostic="skeleton agent returned a mismatched request_id", receipt=receipt,
        )
    if agent_result.content.get("called_tool") is not True or receipt is None:
        return SkeletonStageResult(
            "tool_not_called", request.request_id,
            diagnostic="skeleton agent did not produce an MCP tool receipt", receipt=receipt,
        )
    if receipt.get("request_id") != request.request_id:
        return SkeletonStageResult(
            "invalid_receipt", request.request_id,
            diagnostic="skeleton MCP receipt has a mismatched request_id", receipt=receipt,
        )
    expected = {
        "project": request.project,
        "schema_dir": str(
            Path(workspace)
            / "data" / "java" / f"schemas{request.suffix}"
            / request.model / request.temperature / request.project
        ),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            return SkeletonStageResult(
                "invalid_receipt", request.request_id,
                diagnostic=f"skeleton MCP receipt has mismatched {key}", receipt=receipt,
            )
    if (
        receipt.get("tool_name") != "generate_cangjie_skeleton"
        or receipt.get("tool_call_count") != 1
    ):
        return SkeletonStageResult(
            "invalid_receipt", request.request_id,
            diagnostic="skeleton MCP tool must be called exactly once for this request",
            receipt=receipt,
        )
    build = receipt.get("build", {})
    if agent_result.content.get("build_status") != receipt.get("status"):
        return SkeletonStageResult(
            "invalid_receipt", request.request_id,
            diagnostic="skeleton agent build_status does not match MCP receipt",
            receipt=receipt,
        )
    return SkeletonStageResult(
        str(receipt.get("status", "generation_failed")),
        request.request_id,
        build_returncode=int(build.get("returncode", 1)),
        diagnostic=str(build.get("diagnostic", receipt.get("diagnostic", ""))),
        receipt=receipt,
    )


def new_request(
    *, project: str, model: str, temperature: str, suffix: str,
    include_tests: bool, compile_timeout: int,
) -> SkeletonRequest:
    request = SkeletonRequest(
        project=project,
        model=model,
        temperature=temperature,
        suffix=suffix,
        include_tests=include_tests,
        compile_timeout=compile_timeout,
        request_id=str(uuid.uuid4()),
    )
    request.validate()
    return request
