from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.java.type_resolution.agent import AgentResult, AgentRunner, CodexRunner, PersistentCodexRunner
from src.java.temp_paths import short_temporary_directory
from src.java.type_resolution.schema import load_schema
from src.java.translation.dependency_order import (
    fragment_order,
    schema_dependency_closure,
    schema_scc_batches,
)
from src.java.translation.compact_context import build_compact_translation_context
from src.java.translation.baseline_codex_environment import create_codex_environment
from src.java.translation.skeleton_service import _cangjie_environment


FILE_TRANSLATION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["status", "summary"],
}

_TODO_SKELETON = re.compile(r"throw\s+Exception\(['\"]TODO['\"]\)|//\s*TODO:")
_FRAGMENT_BATCH_SIZE = 8
# Reserve the final 20 seconds for cjpm; the agent receives 200 seconds.
_FRAGMENT_BATCH_TIMEOUT = 220


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Translate dependency-ordered Java files with a persistent Codex agent"
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--model", required=True, help="Schema namespace")
    parser.add_argument("--temperature", required=True)
    parser.add_argument("--suffix", default="")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--agent-model", default="")
    parser.add_argument("--codex-executable", default="codex")
    parser.add_argument(
        "--agent-transport", choices=("app-server", "exec"), default="app-server",
        help="Keep one Codex app-server process alive, or use one-shot exec/resume.",
    )
    parser.add_argument("--cjpm-executable", default="cjpm")
    parser.add_argument(
        "--file-timeout", type=int, default=300,
        help="Emergency watchdog for one fragment batch transaction, in seconds.",
    )
    parser.add_argument(
        "--final-build-timeout", type=int, default=20,
        help="Time reserved inside the batch limit for the system cjpm build.",
    )
    parser.add_argument(
        "--max-builds", type=int, default=3,
        help="Maximum cjpm build attempts made by the agent for one fragment batch.",
    )
    parser.add_argument("--agent-timeout", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--compile-timeout", type=int, default=300, help=argparse.SUPPRESS)
    parser.add_argument("--max-attempts", type=int, default=3, help=argparse.SUPPRESS)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--max-files", type=int, default=0,
        help="Process only the first N dependency-ordered files (0 means all).",
    )
    parser.add_argument("--output-dir", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.agent_timeout is not None:
        args.file_timeout = args.agent_timeout
    _validate_timeouts(args)
    workspace = Path.cwd().resolve()
    schema_dir = Path(
        f"data/java/schemas{args.suffix}/{args.model}/{args.temperature}/{args.project}"
    )
    translation_root = Path(
        f"data/java/skeletons/translations/{args.model}/{args.temperature}/{args.project}"
    )
    if not schema_dir.is_dir():
        raise SystemExit(f"schema directory not found: {schema_dir}")
    if not (translation_root / "cjpm.toml").is_file():
        raise SystemExit("translation skeleton is missing; run create_skeleton.sh first")

    with create_codex_environment(None, workspace) as codex_environment:
        return _run_translation(
            args,
            workspace,
            schema_dir,
            translation_root,
            codex_environment.environment,
        )


def _run_translation(
    args: argparse.Namespace,
    workspace: Path,
    schema_dir: Path,
    translation_root: Path,
    codex_environment: dict[str, str],
) -> int:

    runner = _new_translation_runner(args, codex_environment)
    batches = schema_scc_batches(
        schema_dir,
        project=args.project,
        suffix=args.suffix,
        include_tests=args.include_tests,
        workspace=workspace,
    )
    if args.max_files < 0:
        raise SystemExit("max-files must be non-negative")
    if args.max_files:
        remaining = args.max_files
        limited_batches = []
        for batch in batches:
            if remaining <= 0:
                break
            limited = batch[:remaining]
            limited_batches.append(limited)
            remaining -= len(limited)
        batches = limited_batches
    paths = [path for batch in batches for path in batch]
    if not args.resume:
        _reset_translation_skeletons(paths)
    initial_build = _build(translation_root, args.cjpm_executable, args.compile_timeout)
    if initial_build[0] != 0:
        raise SystemExit("translation TODO skeleton does not compile:\n" + initial_build[1])

    summary: dict[str, Any] = {
        "project": args.project, "files": [],
        "completed": 0, "failed": 0, "skipped": 0,
        "file_timeout_s": args.file_timeout,
        "agent_transport": args.agent_transport,
        "requested_files": args.max_files or len(paths),
    }
    summary["agent_workspace"] = "isolated-project"
    summary["project_scope"] = args.project
    summary["max_agent_builds"] = args.max_builds
    session_id = ""
    with _isolated_project_workspace(
        workspace,
        args.project,
        paths,
        schema_dir,
        translation_root,
        suffix=args.suffix,
    ) as isolated:
        build_budget = _AgentBuildBudget.create(
            isolated.root,
            args.cjpm_executable,
            args.max_builds,
            codex_executable=args.codex_executable,
        )
        runner.environment = _agent_environment(
            {**_cangjie_environment(), **codex_environment}, build_budget,
        )
        try:
            for batch_index, batch in enumerate(batches):
                for real_path in batch:
                    path = isolated.map_path(real_path)
                    result = _translate_file_transaction(
                        path,
                        isolated.map_path(schema_dir),
                        isolated.map_path(translation_root),
                        runner,
                        args,
                        isolated.root,
                        batch_index,
                        build_budget=build_budget,
                        session_id=session_id,
                    )
                    if result.get("session_id"):
                        session_id = str(result["session_id"])
                    _sync_file_transaction(isolated, path, result)
                    summary["files"].append(result)
                    summary["completed"] += result["completed"]
                    summary["failed"] += result["failed"]
                    summary["skipped"] += result["skipped"]
        finally:
            try:
                close = getattr(runner, "close", None)
                if close is not None:
                    close()
            finally:
                build_budget.cleanup()
    summary["session_id"] = session_id
    summary["incomplete_files"] = sum(
        result.get("status") not in {"success", "skipped-complete"}
        for result in summary["files"]
    )
    summary["status"] = "success" if summary["incomplete_files"] == 0 else "incomplete"

    output = Path(args.output_dir) if args.output_dir else Path(
        f"data/java/fragment_runs/{args.project}/{args.model}/{args.temperature}{args.suffix}"
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["status"] == "success" else 2


def _new_translation_runner(
    args: argparse.Namespace,
    codex_environment: dict[str, str],
) -> AgentRunner:
    runner_type = PersistentCodexRunner if args.agent_transport == "app-server" else CodexRunner
    runner_args: dict[str, Any] = {
        "executable": args.codex_executable,
        "model": args.agent_model,
        "sandbox": "workspace-write",
        "timeout": args.file_timeout - args.final_build_timeout,
        "environment": {**_cangjie_environment(), **codex_environment},
        # Keep the agent sandboxed to its isolated project workspace.
        "bypass_approvals_and_sandbox": False,
    }
    if runner_type is PersistentCodexRunner:
        # The controller owns the writable workspace and build budget. An
        # interactive approval request cannot be answered in batch execution.
        runner_args["approval_policy"] = "never"
    return runner_type(**runner_args)


def _validate_timeouts(args: argparse.Namespace) -> None:
    if args.file_timeout < 2 or args.file_timeout > 300:
        raise SystemExit("file-timeout must be between 2 and 300 seconds")
    if args.final_build_timeout < 1 or args.final_build_timeout >= args.file_timeout:
        raise SystemExit("final-build-timeout must be at least 1 and below file-timeout")
    if args.max_builds < 1 or args.max_builds > 3:
        raise SystemExit("max-builds must be between 1 and 3")


def _resolve_native_codex(executable: str | None) -> str | None:
    """Resolve npm Codex launchers to the packaged native Windows binary."""
    if not executable:
        return None

    resolved = shutil.which(executable) or executable
    launcher = Path(resolved)

    if launcher.is_file() and launcher.suffix.lower() == ".exe":
        return str(launcher.resolve())

    if not launcher.is_file():
        return None

    package_root = launcher.parent / "node_modules" / "@openai" / "codex"
    if not package_root.is_dir():
        return None

    candidates = sorted(
        package_root.glob(
            "node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe"
        )
    )
    if len(candidates) != 1:
        return None

    return str(candidates[0].resolve())


@dataclass
class _AgentBuildBudget:
    root: Path
    executable: str
    limit: int
    storage: Any = field(repr=False)
    bin_dir: Path
    count_path: Path
    exhausted_path: Path
    wrapper_path: Path
    real_command: str
    native_codex: str | None = None
    patch_wrapper_path: Path | None = None

    @classmethod
    def create(
        cls,
        root: Path,
        executable: str,
        limit: int,
        *,
        codex_executable: str | None = None,
    ) -> "_AgentBuildBudget":
        real_command = _resolve_cjpm(executable)
        if not real_command:
            raise SystemExit(f"Cangjie package manager not found: {executable}")

        native_codex = None
        if os.name == "nt" and codex_executable:
            native_codex = _resolve_native_codex(codex_executable)
            if not native_codex:
                raise SystemExit(
                    "native Codex executable not found behind Windows launcher: "
                    f"{codex_executable}"
                )

        # Windows workspace-write cannot reliably access a sibling temp
        # directory. Keep controller-provided wrappers and accounting
        # files inside the isolated workspace on Windows; non-Windows
        # retains external tempfile placement. This is execution-budget
        # accounting, not an adversarial tamper-proof security boundary.
        storage = short_temporary_directory(
            prefix="b-",
            workspace=root,
            windows_parent=root,
        )
        bin_dir = Path(storage.name) / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        budget = cls(
            root=root,
            executable=executable,
            limit=limit,
            storage=storage,
            bin_dir=bin_dir,
            count_path=bin_dir / "build-count",
            exhausted_path=bin_dir / "build-limit-exceeded",
            wrapper_path=bin_dir / ("cjpm.cmd" if os.name == "nt" else "cjpm"),
            real_command=real_command,
            native_codex=native_codex,
            patch_wrapper_path=(
                bin_dir / "apply_patch.ps1"
                if native_codex is not None
                else None
            ),
        )
        if os.name == "nt":
            helper_source = Path(__file__).with_name(
                "_agent_build_budget_helper.py"
            )
            helper_target = budget.bin_dir / "_agent_build_budget_helper.py"
            shutil.copy2(helper_source, helper_target)
            budget.wrapper_path.write_text(
                '@echo off\r\n'
                '"%X2CANGJIE_BUDGET_PYTHON%" '
                '"%~dp0_agent_build_budget_helper.py" %*\r\n'
                'exit /b %ERRORLEVEL%\r\n',
                encoding="ascii",
            )

            if budget.patch_wrapper_path is not None:
                budget.patch_wrapper_path.write_text(
                    "param(\n"
                    "    [Parameter(Mandatory=$true, Position=0)]\n"
                    "    [string]$Patch\n"
                    ")\n"
                    "if (-not $env:X2CANGJIE_NATIVE_CODEX) {\n"
                    "    Write-Error 'X2CANGJIE_NATIVE_CODEX is not set'\n"
                    "    exit 2\n"
                    "}\n"
                    "& $env:X2CANGJIE_NATIVE_CODEX "
                    "--codex-run-as-apply-patch $Patch\n"
                    "exit $LASTEXITCODE\n",
                    encoding="ascii",
                )
        else:
            budget.wrapper_path.write_text(
                "#!/usr/bin/env python3\n"
                "import fcntl\n"
                "import os\n"
                "import sys\n"
                "from pathlib import Path\n\n"
                "if len(sys.argv) > 1 and sys.argv[1] == 'build':\n"
                "    count_path = Path(os.environ['X2CANGJIE_BUILD_COUNT_FILE'])\n"
                "    exhausted_path = Path(os.environ['X2CANGJIE_BUILD_EXHAUSTED_FILE'])\n"
                "    limit = int(os.environ['X2CANGJIE_BUILD_LIMIT'])\n"
                "    with count_path.open('a+', encoding='ascii') as state:\n"
                "        fcntl.flock(state.fileno(), fcntl.LOCK_EX)\n"
                "        state.seek(0)\n"
                "        raw = state.read().strip()\n"
                "        count = int(raw or '0')\n"
                "        if count >= limit:\n"
                "            exhausted_path.write_text('1', encoding='ascii')\n"
                "            print(f'agent cjpm build budget exhausted ({limit})', file=sys.stderr)\n"
                "            raise SystemExit(125)\n"
                "        state.seek(0)\n"
                "        state.truncate()\n"
                "        state.write(str(count + 1))\n"
                "        state.flush()\n"
                "        fcntl.flock(state.fileno(), fcntl.LOCK_UN)\n"
                "os.execv(os.environ['X2CANGJIE_REAL_CJPM'], [os.environ['X2CANGJIE_REAL_CJPM'], *sys.argv[1:]])\n",
                encoding="utf-8",
            )
            budget.wrapper_path.chmod(0o755)
        budget.reset()
        return budget

    def reset(self) -> None:
        self.count_path.write_text("0", encoding="ascii")
        self.exhausted_path.unlink(missing_ok=True)

    def count(self) -> int:
        try:
            return int(self.count_path.read_text(encoding="ascii").strip() or "0")
        except (FileNotFoundError, ValueError):
            return 0

    def exceeded(self) -> bool:
        return self.exhausted_path.is_file()

    def cleanup(self) -> None:
        self.storage.cleanup()


def _agent_environment(
    environment: dict[str, str], budget: _AgentBuildBudget,
) -> dict[str, str]:
    result = dict(environment)
    result["PATH"] = os.pathsep.join(
        [str(budget.bin_dir), result.get("PATH", "")]
    )
    result["X2CANGJIE_REAL_CJPM"] = budget.real_command
    result["X2CANGJIE_BUILD_COUNT_FILE"] = str(budget.count_path)
    result["X2CANGJIE_BUILD_EXHAUSTED_FILE"] = str(budget.exhausted_path)
    result["X2CANGJIE_BUILD_LIMIT"] = str(budget.limit)
    if os.name == "nt":
        result["X2CANGJIE_BUDGET_PYTHON"] = sys.executable
        if budget.native_codex is not None:
            result["X2CANGJIE_NATIVE_CODEX"] = budget.native_codex
    return result


class _IsolatedProjectWorkspace:
    """A temporary copy containing only one Java/Cangjie project."""

    def __init__(self, root: Path, real_workspace: Path):
        self.root = root.resolve()
        self.real_workspace = real_workspace.resolve()

    def map_path(self, path: Path) -> Path:
        real_path = path.resolve()
        try:
            relative = real_path.relative_to(self.real_workspace)
        except ValueError as exc:
            raise ValueError(f"path is outside the repository workspace: {path}") from exc
        return self.root / relative

    def copy_tree(self, source: Path) -> None:
        source = source.resolve()
        destination = self.map_path(source)
        if source.is_dir():
            shutil.copytree(source, destination, symlinks=False)
        elif source.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def sync_path(self, isolated_path: Path) -> None:
        source = isolated_path.resolve()
        try:
            relative = source.relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"path is outside the isolated workspace: {isolated_path}") from exc
        destination = self.real_workspace / relative
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"isolated sync requires a regular file: {isolated_path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


@contextmanager
def _isolated_project_workspace(
    workspace: Path,
    project: str,
    schema_paths: list[Path],
    schema_dir: Path,
    translation_root: Path,
    *,
    suffix: str = "",
):
    """Expose only the selected project's inputs to the coding agent.

    The copied trees preserve repository-relative paths so schema references
    remain valid, while the temporary root contains no sibling projects or
    repository-level helper sources.
    """
    workspace = workspace.resolve()
    roots: set[Path] = {schema_dir.resolve(), translation_root.resolve()}
    dependency_root = workspace / "data" / "java" / f"dependencies{suffix}" / project
    if dependency_root.is_dir():
        roots.add(dependency_root.resolve())

    for schema_path in schema_paths:
        schema = load_schema(schema_path)
        source = _source_path_for(schema, workspace)
        if source is not None:
            source_root = _project_root_for(source, workspace, project)
            if source_root is not None:
                roots.add(source_root)
        skeleton = _schema_path(schema, "cangjie_skeleton_path", workspace)
        if skeleton is not None:
            skeleton_root = skeleton.parent.parent if skeleton.parent.name == "src" else skeleton.parent
            if skeleton_root.is_dir():
                roots.add(skeleton_root.resolve())

    with short_temporary_directory(
        prefix="p-",
        workspace=workspace,
    ) as temporary:
        isolated = _IsolatedProjectWorkspace(Path(temporary), workspace)
        for root in _minimal_roots(roots):
            isolated.copy_tree(root)
        yield isolated


def _minimal_roots(roots: set[Path]) -> list[Path]:
    """Drop nested copies when one selected project tree already contains it."""
    result: list[Path] = []
    for root in sorted(roots, key=lambda value: (len(value.parts), str(value))):
        if not any(_is_within(root, existing) for existing in result):
            result.append(root)
    return result


def _project_root_for(source: Path, workspace: Path, project: str) -> Path | None:
    for candidate in (source, *source.parents):
        if candidate.name == project and _is_within(candidate, workspace / "projects"):
            return candidate.resolve()
    return None


def _schema_path(schema: dict[str, Any], key: str, workspace: Path) -> Path | None:
    raw = str(schema.get(key, "")).strip()
    if not raw:
        return None
    candidate = Path(raw)
    candidate = candidate if candidate.is_absolute() else workspace / candidate
    return candidate.resolve() if candidate.is_file() else None


def _sync_file_transaction(
    isolated: _IsolatedProjectWorkspace, schema_path: Path, result: dict[str, Any]
) -> None:
    """Commit the isolated file state, including successful partial batches."""
    status = str(result.get("status", ""))
    if status in {"invalid_target", "skipped-complete"}:
        return
    isolated.sync_path(schema_path)
    schema = load_schema(schema_path)
    target = _schema_path(schema, "cangjie_translations_skeleton_path", isolated.root)
    if target is not None:
        isolated.sync_path(target)


def _translate_file_transaction(
    path: Path,
    schema_dir: Path,
    translation_root: Path,
    runner: AgentRunner,
    args: argparse.Namespace,
    workspace: Path,
    batch_index: int,
    *,
    build_budget: _AgentBuildBudget | None = None,
    session_id: str,
) -> dict[str, Any]:
    """Translate one file through independently committed fragment batches."""
    schema = load_schema(path)
    fragments = fragment_order(schema)
    target = Path(str(schema.get("cangjie_translations_skeleton_path", "")))
    target = target if target.is_absolute() else workspace / target
    target = target.resolve()
    source = _source_path_for(schema, workspace)
    base = _file_result(path, batch_index, fragments, session_id=session_id)
    if build_budget is not None:
        base["max_agent_builds"] = build_budget.limit
    if not target.is_file() or not _is_within(target, translation_root / "src"):
        return {
            **base,
            "status": "invalid_target",
            "failed": len(fragments),
            "diagnostic": f"translation skeleton is missing or outside translation src: {target}",
        }
    if not _has_skeleton_todo(target):
        return {**base, "status": "skipped-complete", "skipped": len(fragments)}

    semantic_dependencies = schema_dependency_closure(
        schema_dir,
        path,
        project=getattr(args, "project", ""),
        suffix=getattr(args, "suffix", ""),
        include_tests=getattr(args, "include_tests", False),
        workspace=workspace,
    )
    batches = _fragment_batches(fragments)
    batch_results = []
    file_start = time.monotonic()
    for fragment_batch_index, fragment_batch in enumerate(batches):
        result = _translate_fragment_batch_transaction(
            path=path,
            schema_dir=schema_dir,
            translation_root=translation_root,
            target=target,
            source=source,
            fragments=fragment_batch,
            fragment_batch_index=fragment_batch_index,
            fragment_batch_count=len(batches),
            runner=runner,
            args=args,
            workspace=workspace,
            semantic_dependencies=semantic_dependencies,
            build_budget=build_budget,
            session_id=session_id,
        )
        batch_results.append(result)
        session_id = result.get("session_id") or session_id

    completed = sum(item.get("completed", 0) for item in batch_results)
    failed = sum(item.get("failed", 0) for item in batch_results)
    skipped = sum(item.get("skipped", 0) for item in batch_results)
    failure_statuses = [
        str(item.get("status"))
        for item in batch_results
        if item.get("status") not in {"success", "skipped-complete"}
    ]
    status = "success" if not failure_statuses else "incomplete"
    unresolved_todos = len(_TODO_SKELETON.findall(target.read_text(encoding="utf-8")))
    if not failure_statuses and unresolved_todos:
        status = "incomplete"
        failure_statuses.append("todo_retained")
    diagnostics = [
        f"batch {item.get('batch_index')}: {item.get('diagnostic')}"
        for item in batch_results
        if item.get("diagnostic")
    ]
    diagnostic = "\n".join(diagnostics)
    if unresolved_todos and "todo_retained" in failure_statuses:
        diagnostic = (
            f"file retains {unresolved_todos} Cangjie TODO markers after batch processing"
            + (f"\n{diagnostic}" if diagnostic else "")
        )
    elapsed = time.monotonic() - file_start
    _record_file_result(
        path,
        status,
        elapsed,
        diagnostic,
        None,
        fragments,
        completed=completed,
        failed=failed,
        skipped=skipped,
        batch_results=batch_results,
    )
    return {
        **base,
        "status": status,
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "session_id": session_id,
        "elapsed_time_s": elapsed,
        "diagnostic": diagnostic,
        "failure_statuses": failure_statuses,
        "unresolved_todos": unresolved_todos,
        "fragment_batches": batch_results,
    }


def _fragment_batches(
    fragments: list[dict[str, Any]], *, max_size: int | None = None,
) -> list[list[dict[str, Any]]]:
    """Partition an already dependency-ordered fragment list contiguously."""
    if max_size is None:
        max_size = _FRAGMENT_BATCH_SIZE
    if max_size < 1:
        raise ValueError("fragment batch size must be positive")
    return [
        fragments[index:index + max_size]
        for index in range(0, len(fragments), max_size)
    ]


def _render_partial_translation(record: dict[str, Any]) -> str:
    lines = record.get("partial_translation", [])
    if not isinstance(lines, list) or not lines:
        return ""
    return "\n".join(str(line).rstrip("\n") for line in lines) + "\n"


def _fragment_skeleton_todos(
    schema: dict[str, Any], target: Path, fragments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return assigned fragments whose generated TODO block is still present."""
    target_text = target.read_text(encoding="utf-8")
    remaining = []
    for fragment in fragments:
        record = _fragment_info(schema, fragment)
        if record.get("skipped"):
            continue
        skeleton = _render_partial_translation(record)
        if skeleton and skeleton in target_text:
            remaining.append(fragment)
        elif not skeleton and _has_skeleton_todo(target):
            # Older hand-written schemas may not carry partial_translation.
            # Treat their assigned fragment as pending while any skeleton TODO
            # remains; generated schemas use the precise block check above.
            remaining.append(fragment)
    return remaining


def _batch_timeout(args: argparse.Namespace) -> tuple[int, int]:
    total = min(_FRAGMENT_BATCH_TIMEOUT, int(args.file_timeout))
    build_timeout = min(int(args.final_build_timeout), max(1, total - 1))
    agent_timeout = max(1, total - build_timeout)
    return agent_timeout, build_timeout


def _run_agent_with_watchdog(
    runner: AgentRunner,
    prompt: str,
    output_schema: dict[str, Any],
    *,
    workspace: Path,
    timeout: float,
    session_id: str = "",
) -> AgentResult:
    """Enforce a transaction deadline even when a persistent transport stalls."""
    expired = threading.Event()

    def expire() -> None:
        expired.set()
        close = getattr(runner, "close", None)
        if close is not None:
            close()

    timer = threading.Timer(timeout, expire)
    timer.daemon = True
    timer.start()
    try:
        result = runner.run(
            prompt, output_schema, workspace=workspace, session_id=session_id,
        )
    finally:
        timer.cancel()
    if expired.is_set():
        return AgentResult(
            status="timeout",
            content=None,
            session_id=session_id,
            stderr=f"translation batch watchdog expired after {timeout}s",
            returncode=124,
        )
    return result


def _translate_fragment_batch_transaction(
    *,
    path: Path,
    schema_dir: Path,
    translation_root: Path,
    target: Path,
    source: Path | None,
    fragments: list[dict[str, Any]],
    fragment_batch_index: int,
    fragment_batch_count: int,
    runner: AgentRunner,
    args: argparse.Namespace,
    workspace: Path,
    semantic_dependencies: list[Path],
    build_budget: _AgentBuildBudget | None,
    session_id: str,
) -> dict[str, Any]:
    """Translate and commit only one contiguous fragment batch."""
    schema = load_schema(path)
    batch_result = {
        "batch_index": fragment_batch_index,
        "batch_count": fragment_batch_count,
        "fragment_names": [
            f"{fragment['fragment_type']}:{fragment['fragment_name']}"
            for fragment in fragments
        ],
        "fragments": len(fragments),
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "session_id": session_id,
    }
    if not fragments:
        return {**batch_result, "status": "skipped-complete"}

    pending = _fragment_skeleton_todos(schema, target, fragments)
    if not pending:
        result = {**batch_result, "status": "skipped-complete", "skipped": len(fragments)}
        _record_batch_result(path, fragments, result, agent_content=None)
        return result

    tracked = _transaction_paths(translation_root, path.parent, source)
    snapshot = _snapshot_files(tracked)
    start = time.monotonic()
    if build_budget is not None:
        build_budget.reset()

    semantic_context = build_compact_translation_context(
        schema=schema,
        fragments=fragments,
        source=source,
        target=target,
        semantic_dependencies=semantic_dependencies,
        workspace=workspace,
    )
    agent_timeout, build_timeout = _batch_timeout(args)
    previous_timeout = getattr(runner, "timeout", None)
    if previous_timeout is not None:
        runner.timeout = agent_timeout
    prompt = _file_translation_prompt(
        path=path,
        source=source,
        target=target,
        translation_root=translation_root,
        schema_dir=schema_dir,
        workspace=workspace,
        fragments=fragments,
        semantic_dependencies=semantic_dependencies,
        semantic_context=semantic_context,
        edit_adapter=(
            build_budget.patch_wrapper_path
            if build_budget is not None
            else None
        ),
        max_builds=build_budget.limit if build_budget is not None else 3,
        timeout=agent_timeout,
        continuing=bool(session_id),
        fragment_batch_index=fragment_batch_index,
        fragment_batch_count=fragment_batch_count,
    )
    try:
        agent_result = _run_agent_with_watchdog(
            runner,
            prompt,
            FILE_TRANSLATION_SCHEMA,
            workspace=workspace,
            timeout=agent_timeout,
            session_id=session_id,
        )
    finally:
        if previous_timeout is not None:
            runner.timeout = previous_timeout

    elapsed = time.monotonic() - start
    updated_session = agent_result.session_id or session_id
    changed_paths = _changed_paths(snapshot, _snapshot_files(tracked))
    unexpected = sorted(
        str(changed.relative_to(workspace))
        for changed in changed_paths
        if changed != target and _is_within(changed, workspace)
    )

    status = "success"
    diagnostic = ""
    if build_budget is not None and build_budget.exceeded():
        status = "agent_build_limit"
        diagnostic = f"agent exceeded the {build_budget.limit}-build limit for this batch"
    elif agent_result.status != "success" or agent_result.content is None:
        status = "agent_timeout" if agent_result.status == "timeout" else "agent_failed"
        diagnostic = agent_result.stderr or "Codex did not return a structured batch result"
    elif unexpected:
        status = "out_of_scope_changes"
        diagnostic = "agent changed protected paths: " + ", ".join(unexpected)
    elif str(agent_result.content.get("status", "")).strip().lower() != "success":
        status = "agent_failed"
        diagnostic = str(agent_result.content.get("summary", "agent reported failure"))
    else:
        remaining = _fragment_skeleton_todos(load_schema(path), target, fragments)
        if remaining:
            status = "todo_retained"
            names = ", ".join(item["fragment_name"] for item in remaining)
            diagnostic = f"assigned fragments still contain TODO skeletons: {names}"
        else:
            returncode, diagnostic = _build(
                translation_root, args.cjpm_executable, build_timeout
            )
            if returncode != 0:
                status = "build_failed" if returncode != 124 else "batch_timeout"

    batch_result.update({
        "status": status,
        "completed": len(fragments) if status == "success" else 0,
        "failed": 0 if status == "success" else len(fragments),
        "session_id": updated_session,
        "agent_builds": build_budget.count() if build_budget is not None else 0,
        "elapsed_time_s": elapsed,
        "diagnostic": diagnostic,
    })
    if status != "success":
        _restore_files(snapshot, _transaction_paths(translation_root, path.parent, source))
    _record_batch_result(path, fragments, batch_result, agent_content=agent_result.content)
    return batch_result


def _file_translation_prompt(
    *,
    path: Path,
    source: Path | None,
    target: Path,
    translation_root: Path,
    schema_dir: Path,
    workspace: Path,
    fragments: list[dict[str, Any]],
    semantic_dependencies: list[Path],
    semantic_context: dict[str, Any] | None = None,
    max_builds: int,
    timeout: int,
    continuing: bool,
    edit_adapter: Path | None = None,
    fragment_batch_index: int = 0,
    fragment_batch_count: int = 1,
) -> str:
    source_name = str(source) if source else str(path)

    continuation = (
        "Continue the shared translation run. "
        "Previous files that passed are stable dependencies."
        if continuing
        else
        "This is the first file of a shared dependency-ordered translation run."
    )

    fragment_names = [
        f"{fragment['fragment_type']}:{fragment['fragment_name']}"
        for fragment in fragments
    ]

    dependency_names = [
        str(dependency)
        for dependency in semantic_dependencies
    ]

    dependency_scope = (
        json.dumps(
            dependency_names,
            ensure_ascii=False,
        )
        if dependency_names
        else "NONE"
    )

    if semantic_context is None:
        semantic_context = {
            "java_source": "",
            "current_cangjie_target": "",
            "schema_metadata": {},
            "class_contexts": [],
            "fragment_records": [],
            "semantic_dependencies": [
                {
                    "schema": str(dependency),
                    "java_source": "",
                    "cangjie_target": "",
                }
                for dependency in semantic_dependencies
            ],
        }

    compact_schema = {
        "schema_metadata": semantic_context.get(
            "schema_metadata",
            {},
        ),
        "class_contexts": semantic_context.get(
            "class_contexts",
            [],
        ),
        "fragment_records": semantic_context.get(
            "fragment_records",
            [],
        ),
    }

    compact_schema_json = json.dumps(
        compact_schema,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    dependency_json = json.dumps(
        semantic_context.get(
            "semantic_dependencies",
            [],
        ),
        ensure_ascii=False,
        separators=(",", ":"),
    )

    translation_rules = semantic_context.get("translation_rules", {})
    rules_section = ""
    if translation_rules:
        rules_section = f"""
===== TRANSLATION TYPE RULES =====
These rules were selected from the current file Schema. Apply them as
file-level translation constraints. Do not invent additional type mappings
and do not ignore a rule that applies to a source occurrence.

<BEGIN_TRANSLATION_TYPE_RULES>
{json.dumps(translation_rules, ensure_ascii=False, separators=(",", ":"))}
<END_TRANSLATION_TYPE_RULES>
"""

    java_source = str(
        semantic_context.get(
            "java_source",
            "",
        )
    )

    target_source = str(
        semantic_context.get(
            "current_cangjie_target",
            "",
        )
    )

    edit_policy = ""

    if edit_adapter is not None:
        edit_policy = f"""
Windows edit adapter (controller-provided, execute-only): {edit_adapter}
- Use this adapter for edits to the target Cangjie file.
- Pass the complete patch text as its single argument.
- Do not call bare apply_patch.
- Execute the adapter only; do not inspect or modify it.
"""

    retrieval_policy = (
        "- Do not read or follow any SKILL.md, AGENTS.md, .codex rules, plugin, MCP, or\n"
        "  repository research instruction file. This baseline does not use\n"
        "  repository-hosted skills or alternate translation workflows."
    )

    return f"""{continuation}

Translate only the assigned fragment batch of one Java source file into its
existing Cangjie TODO skeleton. You own the edit, compile, diagnose, and repair
loop for this batch.

Hard project boundary: {workspace}
Current Java path: {source_name}
Current schema path: {path}
Target Cangjie file ? the only source file you may edit: {target}
Cangjie package root: {translation_root}
Schema directory: {schema_dir}
Fragments represented by this batch: {json.dumps(fragment_names, ensure_ascii=False)}
Fragment batch: {fragment_batch_index + 1} of {fragment_batch_count}
Project semantic dependency schemas: {dependency_scope}

{edit_policy}

===== INLINE JAVA SOURCE =====
<BEGIN_JAVA_SOURCE>
{java_source}
<END_JAVA_SOURCE>

===== INLINE CURRENT CANGJIE TARGET =====
<BEGIN_CANGJIE_TARGET>
{target_source}
<END_CANGJIE_TARGET>

===== COMPACT MATERIALIZED SCHEMA CONTEXT =====
This JSON contains the exact schema record for every requested field,
static initializer, constructor, and method, plus materialized type facts.
Historical Agent feedback, probes, prompts, timestamps, and reasoning have
intentionally been removed.

<BEGIN_COMPACT_SCHEMA_JSON>
{compact_schema_json}
<END_COMPACT_SCHEMA_JSON>

{rules_section}

===== DEPENDENCY RETRIEVAL MANIFEST =====
{dependency_json}

Semantic retrieval policy:
- For project-specific semantic context, inspect only files represented by the
  dependency schemas listed above or the exact dependency Java/Cangjie paths
  supplied by the manifest.
{retrieval_policy}
- If the dependency list is NONE, do not inspect sibling project files for
  semantic understanding.
- The inline Java source, inline current Cangjie target, and compact schema
  context above are the primary semantic evidence.
- Do not reread the current Java source, current schema, or current target
  before the first edit merely to rediscover information already supplied.
- If project-specific dependency context is necessary, inspect only the exact
  dependency Java or Cangjie paths in the manifest.
- Dependency schema paths are identifiers, not an invitation to dump the full
  schema files.
- If the dependency manifest is empty, do not inspect sibling project files.
- Do not enumerate the package or repository to discover siblings.
- Do not run Get-ChildItem -Recurse, repository-wide rg, or equivalent broad
  discovery.
- Compiler diagnostics may justify one narrowly targeted dependency lookup.
- If syntax remains unclear, one small targeted syntax lookup is allowed only when the target and
  compiler diagnostics do not answer the syntax question.

Requirements:
1. Edit only the target Cangjie file.
2. Do not edit schemas, Java files, cjpm.toml, dependencies, or any other
   Cangjie source file. Do not add files.
3. Replace TODO markers only in the assigned fragments with faithful
   implementations preserving the materialized types supplied above. Leave
   unassigned fragments unchanged; their TODO markers are expected.
4. Run cjpm build from the package root only after making a real target edit.
5. Use no more than {max_builds} build attempts for this batch.
6. Do not spend a build attempt on an unchanged target.
7. The {timeout}-second time limit is only an emergency watchdog.
8. If the assigned batch cannot pass within the build budget, report failure instead of
   exploring unrelated files.
9. Return only:
   {{"status":"success"|"failed","summary":"short factual result"}}
"""


def _source_path_for(schema: dict[str, Any], workspace: Path) -> Path | None:
    raw = str(schema.get("path", "")).strip()
    if not raw:
        return None
    candidate = Path(raw)
    candidate = candidate if candidate.is_absolute() else workspace / candidate
    if candidate.is_file():
        return candidate.resolve()
    return None


def _has_skeleton_todo(path: Path) -> bool:
    return bool(_TODO_SKELETON.search(path.read_text(encoding="utf-8")))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _transaction_paths(translation_root: Path, schema_dir: Path, source: Path | None) -> set[Path]:
    paths = set((translation_root / "src").glob("**/*.cj"))
    paths.update({translation_root / "cjpm.toml", translation_root / "cjpm.lock"})
    paths.update(schema_dir.glob("*.json"))
    if source is not None:
        paths.add(source)
    return {path.resolve() for path in paths if path.is_file()}


def _snapshot_files(paths: set[Path]) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in paths}


def _changed_paths(before: dict[Path, bytes], after: dict[Path, bytes]) -> set[Path]:
    return {
        path for path in before.keys() | after.keys()
        if before.get(path) != after.get(path)
    }


def _restore_files(before: dict[Path, bytes], current_paths: set[Path]) -> None:
    for path in current_paths - before.keys():
        path.unlink()
    for path, content in before.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _record_file_result(
    schema_path: Path,
    status: str,
    elapsed: float,
    diagnostic: str,
    agent_content: dict[str, Any] | None,
    fragments: list[dict[str, Any]],
    *,
    completed: int = 0,
    failed: int = 0,
    skipped: int = 0,
    batch_results: list[dict[str, Any]] | None = None,
) -> None:
    """Record the aggregate file result after all fragment batches finish."""
    schema = load_schema(schema_path)
    schema["file_translation"] = {
        "status": status,
        "elapsed_time_s": round(elapsed, 3),
        "diagnostic": diagnostic[-8000:],
        "agent_summary": str((agent_content or {}).get("summary", "")),
        "fragment_count": len(fragments),
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "batch_count": len(batch_results or []),
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if status == "success":
        for fragment in fragments:
            fragment_info = _fragment_info(schema, fragment)
            fragment_info["translation_status"] = "completed"
            fragment_info["cangjie_compilation"] = {
                "outcome": "success", "mode": "fragment_batch",
            }
            fragment_info["elapsed_time"] = elapsed
            fragment_info["generation_timestamp"] = datetime.now(timezone.utc).isoformat()
    schema_path.write_text(json.dumps(schema, indent=4, ensure_ascii=False), encoding="utf-8")


def _record_batch_result(
    schema_path: Path,
    fragments: list[dict[str, Any]],
    result: dict[str, Any],
    *,
    agent_content: dict[str, Any] | None,
) -> None:
    """Persist one batch receipt and update only its fragment records."""
    schema = load_schema(schema_path)
    batch_index = int(result.get("batch_index", 0))
    batch_id = f"{batch_index}:" + ",".join(
        f"{item['fragment_type']}:{item['fragment_name']}"
        for item in fragments
    )
    entry = {
        "batch_id": batch_id,
        "batch_index": batch_index,
        "batch_count": int(result.get("batch_count", 1)),
        "fragment_names": list(result.get("fragment_names", [])),
        "fragments": len(fragments),
        "status": str(result.get("status", "")),
        "completed": int(result.get("completed", 0)),
        "failed": int(result.get("failed", 0)),
        "skipped": int(result.get("skipped", 0)),
        "agent_builds": int(result.get("agent_builds", 0)),
        "elapsed_time_s": round(float(result.get("elapsed_time_s", 0.0)), 3),
        "diagnostic": str(result.get("diagnostic", ""))[-8000:],
        "agent_summary": str((agent_content or {}).get("summary", "")),
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    previous = schema.get("translation_batches", [])
    if not isinstance(previous, list):
        previous = []
    schema["translation_batches"] = [
        item for item in previous
        if isinstance(item, dict) and item.get("batch_id") != batch_id
    ] + [entry]

    status = entry["status"]
    for fragment in fragments:
        fragment_info = _fragment_info(schema, fragment)
        if status == "success":
            fragment_info["translation_status"] = "completed"
            fragment_info["cangjie_compilation"] = {
                "outcome": "success",
                "mode": "fragment_batch",
            }
        elif status not in {"skipped-complete", "invalid_target"}:
            fragment_info["translation_status"] = "failed"
            fragment_info["cangjie_compilation"] = {
                "outcome": "failed",
                "mode": "fragment_batch",
                "status": status,
                "diagnostic": entry["diagnostic"],
            }
        fragment_info["translation_batch"] = batch_id
        fragment_info["generation_timestamp"] = datetime.now(timezone.utc).isoformat()

    schema_path.write_text(json.dumps(schema, indent=4, ensure_ascii=False), encoding="utf-8")


def _file_result(
    path: Path, batch_index: int, fragments: list[dict[str, Any]], *, session_id: str,
) -> dict[str, Any]:
    return {
        "schema_file": path.name,
        "scc_batch": batch_index,
        "fragments": len(fragments),
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "session_id": session_id,
    }


def _fragment_info(schema: dict[str, Any], fragment: dict[str, Any]) -> dict[str, Any]:
    class_info = schema["classes"][fragment["class_key"]]
    kind = fragment["fragment_type"]
    if kind == "field":
        return class_info["fields"][fragment["fragment_name"]]
    if kind == "static_initializer":
        return class_info["static_initializers"][fragment["fragment_name"]]
    return class_info["methods"][fragment["fragment_name"]]


def _resolve_cjpm(executable: str) -> str:
    environment = _cangjie_environment()
    command = shutil.which(executable, path=environment.get("PATH")) or (
        executable if Path(executable).is_file() else ""
    )
    if not command and executable == "cjpm":
        candidate = Path(environment.get("CANGJIE_HOME", "")) / "tools" / "bin" / "cjpm"
        command = str(candidate) if candidate.is_file() else ""
    return command


def _build(root: Path, executable: str, timeout: int) -> tuple[int, str]:
    environment = _cangjie_environment()
    command = _resolve_cjpm(executable)
    if not command:
        return 127, f"Cangjie package manager not found: {executable}"
    try:
        result = subprocess.run(
            [command, "build"], capture_output=True, text=True, timeout=timeout,
            cwd=root, env=environment, check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"cjpm build timed out after {timeout}s"
    output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    return result.returncode, output


def _reset_translation_skeletons(paths):
    for path in paths:
        schema = load_schema(path)
        source = Path(str(schema.get("cangjie_skeleton_path", "")))
        target = Path(str(schema.get("cangjie_translations_skeleton_path", "")))
        if not source.is_file() or not target.parent.exists():
            raise SystemExit(f"skeleton paths are incomplete in {path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


if __name__ == "__main__":
    raise SystemExit(main())
