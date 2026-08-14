from __future__ import annotations

import argparse
import json
from pathlib import Path

from .adapter import default_run_dir
from .agent import CodexRunner
from .probe import CangjieTypeProbe
from .resolver import TypeResolutionService
from .schema import load_schema, schema_paths
from src.java.translation.skeleton_stage import (
    new_request as new_skeleton_request,
    new_skeleton_runner,
    run_skeleton_stage,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve Java type occurrences, then have a Codex agent invoke the "
            "MCP skeleton generator and build it"
        )
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--model", required=True, help="Schema namespace used by create_schema")
    parser.add_argument("--temperature", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--agent-model", default="", help="Codex model override; default uses Codex config")
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--cjc-executable", default="cjc")
    parser.add_argument("--agent-timeout", type=int, default=1800)
    parser.add_argument("--compile-timeout", type=int, default=300)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument(
        "--max-occurrences-per-prompt", type=int, default=128,
        help="Bound one type-resolution prompt for large schema files.",
    )
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--types-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path.cwd().resolve()
    schema_dir = Path(
        f"data/java/schemas{args.suffix}/{args.model}/{args.temperature}/{args.project}"
    )
    if not schema_dir.is_dir():
        raise SystemExit(f"schema directory not found: {schema_dir}")
    output_dir = Path(args.output_dir) if args.output_dir else default_run_dir(
        args.project, args.model, args.temperature, args.suffix
    )

    service = TypeResolutionService(
        runner=CodexRunner(
            executable=args.codex_executable,
            model=args.agent_model,
            timeout=args.agent_timeout,
        ),
        probe=CangjieTypeProbe(args.cjc_executable, min(args.compile_timeout, 300)),
        workspace=workspace,
        project=args.project,
        max_attempts=args.max_attempts,
        max_occurrences_per_prompt=args.max_occurrences_per_prompt,
    )
    summary = service.resolve_project(
        schema_dir,
        include_tests=args.include_tests,
        output_dir=output_dir,
    )
    if args.types_only:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    paths = schema_paths(schema_dir, include_tests=args.include_tests)
    skeleton_runner = new_skeleton_runner(
        executable=args.codex_executable,
        model=args.agent_model,
        timeout=args.agent_timeout,
        workspace=workspace,
    )
    last_build = None
    build_attempts = 0
    for build_attempt in range(1, 4):
        build_attempts = build_attempt
        stage = run_skeleton_stage(
            skeleton_runner,
            new_skeleton_request(
                project=args.project, model=args.model, temperature=args.temperature,
                suffix=args.suffix, include_tests=args.include_tests,
                compile_timeout=args.compile_timeout,
            ),
            workspace=workspace,
        )
        if stage.status == "success":
            _refresh_resolution_counts(summary, service)
            summary["skeleton_build"] = {
                "status": "success",
                "attempts": build_attempt,
                "fallback_pass": False,
                "via": "mcp-agent",
                "request_id": stage.request_id,
            }
            _write_summary(output_dir, summary)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            return 0
        if stage.status != "build_failed":
            raise SystemExit(
                f"skeleton MCP stage failed ({stage.status}): {stage.diagnostic}"
            )
        last_build = _BuildResult(stage.build_returncode, stage.diagnostic)
        impacted = _impacted_schema_paths(paths, stage.diagnostic)
        changed = sum(service.repair_schema(path, stage.diagnostic) for path in impacted)
        if changed == 0:
            break

    impacted = _impacted_schema_paths(paths, last_build.output if last_build else "")
    for path in impacted:
        service.fallback_schema(path)
    final_stage = run_skeleton_stage(
        skeleton_runner,
        new_skeleton_request(
            project=args.project, model=args.model, temperature=args.temperature,
            suffix=args.suffix, include_tests=args.include_tests,
            compile_timeout=args.compile_timeout,
        ),
        workspace=workspace,
    )
    build_attempts += 1
    _refresh_resolution_counts(summary, service)
    summary["skeleton_build"] = {
        "status": "success" if final_stage.status == "success" else "failed",
        "attempts": build_attempts,
        "fallback_pass": True,
        "via": "mcp-agent",
        "request_id": final_stage.request_id,
        "diagnostic": final_stage.diagnostic if final_stage.status != "success" else "",
    }
    _write_summary(output_dir, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if final_stage.status != "success":
        raise SystemExit("TODO skeleton failed cjpm build after deterministic fallback")
    return 0


class _BuildResult:
    def __init__(self, returncode: int, output: str):
        self.returncode = returncode
        self.output = output


def _impacted_schema_paths(paths: list[Path], diagnostic: str) -> list[Path]:
    impacted = []
    normalized = diagnostic.replace("\\", "/")
    for path in paths:
        data = load_schema(path)
        cangjie_path = str(data.get("cangjie_skeleton_path", "")).replace("\\", "/")
        source_stem = Path(str(data.get("path", ""))).stem
        if (cangjie_path and (cangjie_path in normalized or Path(cangjie_path).name in normalized)) or (
            source_stem and f"{source_stem}.cj" in normalized
        ):
            impacted.append(path)
    return impacted or paths


def _write_summary(output_dir: Path, summary: dict) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _refresh_resolution_counts(summary: dict, service: TypeResolutionService) -> None:
    values = list(service._resolutions.values())
    summary["resolved"] = sum(item.status.startswith("resolved") for item in values)
    summary["fallback"] = sum(item.status.startswith("fallback") for item in values)


if __name__ == "__main__":
    raise SystemExit(main())
