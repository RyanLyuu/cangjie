from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.java.type_resolution.agent import AgentRunner, CodexRunner, PersistentCodexRunner
from src.java.type_resolution.schema import load_schema
from src.java.translation.dependency_order import fragment_order, schema_scc_batches
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
        help="Emergency watchdog for one file transaction, in seconds.",
    )
    parser.add_argument(
        "--final-build-timeout", type=int, default=20,
        help="Time reserved inside the file limit for the system final cjpm build.",
    )
    parser.add_argument(
        "--max-builds", type=int, default=3,
        help="Maximum cjpm build attempts made by the agent for one file.",
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

    runner_type = PersistentCodexRunner if args.agent_transport == "app-server" else CodexRunner
    runner = runner_type(
        executable=args.codex_executable,
        model=args.agent_model,
        sandbox="workspace-write",
        timeout=args.file_timeout - args.final_build_timeout,
        environment=_cangjie_environment(),
        # The project workspace below is the only writable scope. Keep Codex's
        # sandbox enabled so the process cannot escape that temporary copy.
        bypass_approvals_and_sandbox=False,
    )
    batches = schema_scc_batches(
        schema_dir,
        project=args.project,
        suffix=args.suffix,
        include_tests=args.include_tests,
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
            isolated.root, args.cjpm_executable, args.max_builds,
        )
        runner.environment = _agent_environment(
            _cangjie_environment(), build_budget,
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

    output = Path(args.output_dir) if args.output_dir else Path(
        f"data/java/fragment_runs/{args.project}/{args.model}/{args.temperature}{args.suffix}"
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


def _validate_timeouts(args: argparse.Namespace) -> None:
    if args.file_timeout < 2 or args.file_timeout > 300:
        raise SystemExit("file-timeout must be between 2 and 300 seconds")
    if args.final_build_timeout < 1 or args.final_build_timeout >= args.file_timeout:
        raise SystemExit("final-build-timeout must be at least 1 and below file-timeout")
    if args.max_builds < 1 or args.max_builds > 3:
        raise SystemExit("max-builds must be between 1 and 3")


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

    @classmethod
    def create(cls, root: Path, executable: str, limit: int) -> "_AgentBuildBudget":
        real_command = _resolve_cjpm(executable)
        if not real_command:
            raise SystemExit(f"Cangjie package manager not found: {executable}")
        # Keep the enforcement state outside the agent's writable project.
        # The agent can edit only the isolated project, never this directory.
        storage = tempfile.TemporaryDirectory(prefix="x2cangjie-build-budget-")
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
            wrapper_path=bin_dir / "cjpm",
            real_command=real_command,
        )
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

    with tempfile.TemporaryDirectory(prefix="x2cangjie-agent-project-") as temporary:
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
    """Commit only the isolated transaction's target and schema receipt."""
    status = str(result.get("status", ""))
    if status in {"invalid_target", "skipped-complete"}:
        return
    isolated.sync_path(schema_path)
    if status != "success":
        return
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
    """Give one dependency-ordered Java file to the persistent coding agent.

    The agent owns the edit/compile/fix loop.  The controller intentionally
    intervenes only at the transaction boundary: it verifies the final build
    and restores the original skeleton if the file does not finish cleanly.
    """
    schema = load_schema(path)
    fragments = fragment_order(schema)
    target = Path(str(schema.get("cangjie_translations_skeleton_path", "")))
    target = target if target.is_absolute() else workspace / target
    target = target.resolve()
    source = _source_path_for(schema, workspace)
    base = _file_result(path, batch_index, fragments, session_id=session_id)
    if build_budget is not None:
        build_budget.reset()
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

    tracked = _transaction_paths(translation_root, path.parent, source)
    snapshot = _snapshot_files(tracked)
    start = time.monotonic()
    prompt = _file_translation_prompt(
        path=path,
        source=source,
        target=target,
        translation_root=translation_root,
        schema_dir=schema_dir,
        workspace=workspace,
        fragments=fragments,
        max_builds=build_budget.limit if build_budget is not None else 3,
        timeout=args.file_timeout - args.final_build_timeout,
        continuing=bool(session_id),
    )
    agent_result = runner.run(
        prompt, FILE_TRANSLATION_SCHEMA, workspace=workspace, session_id=session_id
    )
    elapsed = time.monotonic() - start
    updated_session = agent_result.session_id or session_id
    if build_budget is not None:
        base["agent_builds"] = build_budget.count()
    current_paths = _transaction_paths(translation_root, path.parent, source)
    changed_paths = _changed_paths(snapshot, _snapshot_files(current_paths))
    unexpected = sorted(
        str(changed.relative_to(workspace))
        for changed in changed_paths
        if changed != target and _is_within(changed, workspace)
    )

    status = "success"
    diagnostic = ""
    if build_budget is not None and build_budget.exceeded():
        status = "agent_build_limit"
        diagnostic = (
            f"agent exceeded the {build_budget.limit}-build limit for this file"
        )
    elif agent_result.status != "success" or agent_result.content is None:
        status = "agent_timeout" if agent_result.status == "timeout" else "agent_failed"
        diagnostic = agent_result.stderr or "Codex did not return a structured file result"
    elif unexpected:
        status = "out_of_scope_changes"
        diagnostic = "agent changed protected paths: " + ", ".join(unexpected)
    elif str(agent_result.content.get("status", "")).strip().lower() != "success":
        status = "agent_failed"
        diagnostic = str(agent_result.content.get("summary", "agent reported failure"))
    elif _has_skeleton_todo(target):
        status = "todo_retained"
        diagnostic = "agent returned before removing every Cangjie TODO marker"
    else:
        remaining = args.file_timeout - elapsed
        if remaining < 1:
            status = "file_timeout"
            diagnostic = f"file transaction exceeded {args.file_timeout}s before final build"
        else:
            build_timeout = min(args.final_build_timeout, max(1, math.floor(remaining)))
            returncode, diagnostic = _build(
                translation_root, args.cjpm_executable, build_timeout
            )
            if returncode != 0:
                status = "build_failed" if returncode != 124 else "file_timeout"

    elapsed = time.monotonic() - start
    if status != "success":
        _restore_files(snapshot, _transaction_paths(translation_root, path.parent, source))
        _record_file_result(
            path, status, elapsed, diagnostic, agent_result.content, fragments,
        )
        return {
            **base,
            "status": status,
            "failed": len(fragments),
            "session_id": updated_session,
            "elapsed_time_s": elapsed,
            "diagnostic": diagnostic,
        }

    _record_file_result(
        path, "success", elapsed, diagnostic, agent_result.content, fragments,
    )
    return {
        **base,
        "status": "success",
        "completed": len(fragments),
        "session_id": updated_session,
        "elapsed_time_s": elapsed,
        "diagnostic": diagnostic,
    }


def _file_translation_prompt(
    *, path: Path, source: Path | None, target: Path, translation_root: Path,
    schema_dir: Path, workspace: Path, fragments: list[dict[str, Any]],
    max_builds: int, timeout: int,
    continuing: bool,
) -> str:
    source_name = str(source) if source else str(path)
    continuation = (
        "Continue the shared translation run. Previous files that passed are stable dependencies."
        if continuing else
        "This is the first file of a shared dependency-ordered translation run."
    )
    fragment_names = [
        f"{fragment['fragment_type']}:{fragment['fragment_name']}"
        for fragment in fragments
    ]
    return f"""{continuation}

Translate exactly one Java source file to its existing Cangjie TODO skeleton.
You own the complete edit, compile, diagnose, and repair loop for this file.

Hard project boundary: the isolated project workspace is {workspace}.
Only inspect and execute paths under this directory. It contains this Java
project, its schemas, and its Cangjie translation package; do not access parent
directories, sibling projects, repository-wide helpers, or external source
trees. The package root below is the only build directory.

Java source (read-only): {source_name}
Schema (read-only): {path}
Target Cangjie file (the only source file you may edit): {target}
Cangjie package root: {translation_root}
Schema directory: {schema_dir}
Fragments represented by this file: {json.dumps(fragment_names, ensure_ascii=False)}

Requirements:
1. Read the Java source, schema, and current target skeleton before editing.
2. Edit only the target Cangjie file. Do not edit schemas, Java files, cjpm.toml,
   dependencies, or any other Cangjie source file. Do not add files.
3. Replace every TODO marker in the target file, including TODO throws and
   TODO comments, with a faithful Cangjie implementation that preserves the
   skeleton's materialized types.
4. Run `cjpm build` from the Cangjie package root to validate repairs, but use
   no more than {max_builds} build attempts for this file. Do not spend a build
   attempt on an unchanged target.
5. Keep all searches scoped to this project workspace; do not use absolute
   paths outside it, and do not search the repository root.
6. The time limit is only an emergency watchdog for a stuck turn; the normal
   stopping condition is the build-attempt limit above. If the file cannot pass
   within the build budget, report failure; the controller will restore it.
7. Return only this JSON object after the work is done:
   {{"status":"success"|"failed", "summary":"short factual result"}}
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
) -> None:
    """Record the transaction at the file boundary without parsing agent edits."""
    schema = load_schema(schema_path)
    schema["file_translation"] = {
        "status": status,
        "elapsed_time_s": round(elapsed, 3),
        "diagnostic": diagnostic[-8000:],
        "agent_summary": str((agent_content or {}).get("summary", "")),
        "fragment_count": len(fragments),
        "generation_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if status == "success":
        for fragment in fragments:
            fragment_info = _fragment_info(schema, fragment)
            fragment_info["translation_status"] = "completed"
            fragment_info["cangjie_compilation"] = {
                "outcome": "success", "mode": "file_agent",
            }
            fragment_info["elapsed_time"] = elapsed
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
