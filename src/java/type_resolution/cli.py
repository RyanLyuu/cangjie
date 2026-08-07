from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

from .adapter import default_run_dir
from .agent import CodexRunner
from .probe import CangjieTypeProbe
from .resolver import TypeResolutionService
from .schema import load_schema, schema_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve Java type occurrences with Codex, generate a TODO skeleton, and build it"
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--model", required=True, help="Schema namespace used by create_schema")
    parser.add_argument("--temperature", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--agent-model", default="", help="Codex model override; default uses Codex config")
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument("--cjc-executable", default="cjc")
    parser.add_argument("--cjpm-executable", default="cjpm")
    parser.add_argument("--agent-timeout", type=int, default=1800)
    parser.add_argument("--compile-timeout", type=int, default=300)
    parser.add_argument("--max-attempts", type=int, default=3)
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
    skeleton_dir = Path(f"data/java/skeletons/{args.project}")
    last_build = None
    build_attempts = 0
    for build_attempt in range(1, 4):
        build_attempts = build_attempt
        _generate_skeleton(args, schema_dir)
        _write_placeholder_files(paths, args)
        last_build = _run_build(skeleton_dir, args.cjpm_executable, args.compile_timeout)
        if last_build.returncode == 0:
            _refresh_resolution_counts(summary, service)
            summary["skeleton_build"] = {
                "status": "success",
                "attempts": build_attempt,
                "fallback_pass": False,
            }
            _write_summary(output_dir, summary)
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            return 0
        impacted = _impacted_schema_paths(paths, last_build.output)
        changed = sum(service.repair_schema(path, last_build.output) for path in impacted)
        if changed == 0:
            break

    impacted = _impacted_schema_paths(paths, last_build.output if last_build else "")
    for path in impacted:
        service.fallback_schema(path)
    _generate_skeleton(args, schema_dir)
    _write_placeholder_files(paths, args)
    final_build = _run_build(skeleton_dir, args.cjpm_executable, args.compile_timeout)
    build_attempts += 1
    _refresh_resolution_counts(summary, service)
    summary["skeleton_build"] = {
        "status": "success" if final_build.returncode == 0 else "failed",
        "attempts": build_attempts,
        "fallback_pass": True,
        "diagnostic": final_build.output if final_build.returncode else "",
    }
    _write_summary(output_dir, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if final_build.returncode != 0:
        raise SystemExit("TODO skeleton failed cjpm build after deterministic fallback")
    return 0


def _generate_skeleton(args, schema_dir: Path) -> None:
    from src.java.translation.create_skeleton import main as create_skeleton

    create_skeleton(SimpleNamespace(
        project=args.project,
        model=args.model,
        temperature=args.temperature,
        suffix=args.suffix,
        translate_tests="true" if args.include_tests else "false",
        schemas_dir=str(schema_dir),
    ))


def _write_placeholder_files(paths: list[Path], args) -> None:
    names = set()
    for path in paths:
        for placeholder in load_schema(path).get("generated_type_placeholders", []):
            name = str(placeholder.get("name", "")).strip()
            if name:
                names.add(name)
    if not names:
        return
    package = args.project.replace("-", "_")
    content = f"package {package}\n\n" + "\n".join(
        f"public interface {name} {{}}" for name in sorted(names)
    ) + "\n"
    roots = [
        Path(f"data/java/skeletons/{args.project}"),
        Path(f"data/java/skeletons/translations/{args.model}/{args.temperature}/{args.project}"),
    ]
    for root in roots:
        target = root / "src" / "x2cangjie_type_placeholders.cj"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


class _BuildResult:
    def __init__(self, returncode: int, output: str):
        self.returncode = returncode
        self.output = output


def _run_build(root: Path, executable: str, timeout: int) -> _BuildResult:
    command = shutil.which(executable) or (executable if Path(executable).is_file() else "")
    if not command:
        raise SystemExit(f"Cangjie package manager not found: {executable}")
    try:
        result = subprocess.run(
            [command, "build"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=root,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _BuildResult(124, f"cjpm build timed out after {timeout}s")
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return _BuildResult(result.returncode, output)


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
