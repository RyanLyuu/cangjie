"""Generate and validate Cangjie TODO skeletons from finalized schemas.

This module is deliberately independent of an agent transport.  The MCP server
uses it to perform the write operation, while the workflow controller verifies
the receipt it leaves behind.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import platform
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from src.java.type_resolution.schema import (
    get_materialized_type,
    load_occurrences,
    schema_paths,
)


_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class SkeletonRequest:
    project: str
    model: str
    temperature: str
    suffix: str = ""
    include_tests: bool = False
    compile_timeout: int = 300
    request_id: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkeletonRequest":
        include_tests = data.get("include_tests", False)
        if not isinstance(include_tests, bool):
            raise ValueError("include_tests must be a boolean")
        compile_timeout = data.get("compile_timeout", 300)
        if isinstance(compile_timeout, bool) or not isinstance(compile_timeout, int):
            raise ValueError("compile_timeout must be an integer")
        request = cls(
            project=str(data.get("project", "")).strip(),
            model=str(data.get("model", "")).strip(),
            temperature=str(data.get("temperature", "")).strip(),
            suffix=str(data.get("suffix", "")),
            include_tests=include_tests,
            compile_timeout=compile_timeout,
            request_id=str(data.get("request_id", "")).strip(),
        )
        request.validate()
        return request

    def validate(self) -> None:
        for name, value in (
            ("project", self.project),
            ("model", self.model),
            ("temperature", self.temperature),
        ):
            if value in {".", ".."} or not _SAFE_COMPONENT.fullmatch(value):
                raise ValueError(f"{name} must be a non-empty path-safe identifier")
        if self.suffix and (
            self.suffix in {".", ".."} or not _SAFE_COMPONENT.fullmatch(self.suffix)
        ):
            raise ValueError("suffix must be path-safe")
        if self.compile_timeout < 1 or self.compile_timeout > 3600:
            raise ValueError("compile_timeout must be between 1 and 3600 seconds")
        try:
            uuid.UUID(self.request_id)
        except ValueError as exc:
            raise ValueError("request_id must be a UUID") from exc

    @property
    def namespace(self) -> str:
        return f"{self.model}/{self.temperature}{self.suffix}"


def schema_dir_for(request: SkeletonRequest, workspace: Path) -> Path:
    return workspace / "data" / "java" / f"schemas{request.suffix}" / request.model / request.temperature / request.project


def skeleton_dir_for(request: SkeletonRequest, workspace: Path) -> Path:
    return workspace / "data" / "java" / "skeletons" / request.project


def translation_skeleton_dir_for(request: SkeletonRequest, workspace: Path) -> Path:
    return (
        workspace / "data" / "java" / "skeletons" / "translations"
        / request.model / request.temperature / request.project
    )


def receipt_path_for(request: SkeletonRequest, workspace: Path) -> Path:
    return (
        workspace / "data" / "java" / "skeleton_generation_runs" / request.project
        / request.model / f"{request.temperature}{request.suffix}" / f"{request.request_id}.json"
    )


def _fragment_for_occurrence(schema: dict[str, Any], occurrence: Any) -> dict[str, Any]:
    class_info = schema["classes"][occurrence.class_key]
    if occurrence.fragment_kind == "class":
        return class_info
    if occurrence.fragment_kind == "field":
        return class_info["fields"][occurrence.fragment_key]
    if occurrence.fragment_kind == "static_initializer":
        return class_info["static_initializers"][occurrence.fragment_key]
    return class_info["methods"][occurrence.fragment_key]


def unresolved_type_occurrences(schema_dir: Path, *, include_tests: bool) -> list[dict[str, str]]:
    """Return all source occurrences that do not have a materialized target."""
    missing = []
    for path in schema_paths(schema_dir, include_tests=include_tests):
        schema, occurrences = load_occurrences(path)
        for occurrence in occurrences:
            fragment = _fragment_for_occurrence(schema, occurrence)
            target = get_materialized_type(
                fragment, occurrence.variation, occurrence.identifier
            )
            if not target:
                missing.append({
                    "schema_file": path.name,
                    "occurrence_id": occurrence.occurrence_id,
                    "source_type": occurrence.source_type,
                    "role": occurrence.role,
                })
    return missing


def _write_placeholder_files(paths: list[Path], request: SkeletonRequest, workspace: Path) -> None:
    names = set()
    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for placeholder in data.get("generated_type_placeholders", []):
            name = str(placeholder.get("name", "")).strip()
            if name:
                names.add(name)
    if not names:
        return
    package = request.project.replace("-", "_")
    content = f"package {package}\n\n" + "\n".join(
        f"public interface {name} {{}}" for name in sorted(names)
    ) + "\n"
    for root in (
        skeleton_dir_for(request, workspace),
        translation_skeleton_dir_for(request, workspace),
    ):
        target = root / "src" / "x2cangjie_type_placeholders.cj"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def _prepend_path(value: str, entries: list[Path]) -> str:
    """Prepend existing SDK directories without duplicating PATH entries."""
    parts = [str(path) for path in entries if path.is_dir()]
    parts.extend(part for part in value.split(os.pathsep) if part)
    return os.pathsep.join(dict.fromkeys(parts))


def _cangjie_environment() -> dict[str, str]:
    """Make the Cangjie runtime discoverable by native ``cjpm`` subprocesses."""
    env = os.environ.copy()
    candidates: list[Path] = []
    for variable in ("CANGJIE_HOME", "CANGJIE_SDK_HOME"):
        value = env.get(variable, "").strip()
        if value:
            candidates.append(Path(value).expanduser())

    for executable in ("cjpm", "cjc"):
        resolved = shutil.which(executable, path=env.get("PATH"))
        if not resolved:
            continue
        path = Path(resolved).resolve()
        # cjpm is in <sdk>/tools/bin and cjc is in <sdk>/bin.
        candidates.extend((path.parents[2], path.parents[1]))

    sdk_home = next(
        (candidate.resolve() for candidate in candidates
         if (candidate / "runtime" / "lib").is_dir()),
        None,
    )
    if sdk_home is None:
        return env

    arch = platform.machine().lower()
    arch = {"amd64": "x86_64", "x86-64": "x86_64", "aarch64": "aarch64"}.get(arch, arch)
    runtime_root = sdk_home / "runtime" / "lib"
    runtime_dir = runtime_root / f"linux_{arch}_cjnative"
    if not runtime_dir.is_dir():
        runtime_dirs = sorted(runtime_root.glob("linux_*_cjnative"))
        if runtime_dirs:
            runtime_dir = runtime_dirs[0]

    env["CANGJIE_HOME"] = str(sdk_home)
    env["CANGJIE_SDK_HOME"] = str(sdk_home)
    env["PATH"] = _prepend_path(
        env.get("PATH", ""), [sdk_home / "bin", sdk_home / "tools" / "bin"]
    )
    env["LD_LIBRARY_PATH"] = _prepend_path(
        env.get("LD_LIBRARY_PATH", ""), [runtime_dir, sdk_home / "tools" / "lib"]
    )
    return env


def _run_build(root: Path, timeout: int) -> tuple[int, str]:
    env = _cangjie_environment()
    command = shutil.which("cjpm", path=env.get("PATH"))
    if not command:
        candidate = Path(env.get("CANGJIE_HOME", "")) / "tools" / "bin" / "cjpm"
        command = str(candidate) if candidate.is_file() else ""
    if not command:
        return 127, "Cangjie package manager not found: cjpm"
    try:
        result = subprocess.run(
            [command, "build"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=root,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, f"cjpm build timed out after {timeout}s"
    diagnostic = "\n".join(
        part.strip() for part in (result.stdout, result.stderr) if part.strip()
    )
    return result.returncode, diagnostic


def _result(request: SkeletonRequest, workspace: Path, status: str, **extra: Any) -> dict[str, Any]:
    return {
        "request_id": request.request_id,
        "status": status,
        "project": request.project,
        "schema_dir": str(schema_dir_for(request, workspace)),
        "skeleton_dir": str(skeleton_dir_for(request, workspace)),
        "translation_skeleton_dir": str(translation_skeleton_dir_for(request, workspace)),
        **extra,
    }


def _write_receipt(request: SkeletonRequest, workspace: Path, result: dict[str, Any]) -> None:
    path = receipt_path_for(request, workspace)
    path.parent.mkdir(parents=True, exist_ok=True)
    calls = 0
    if path.is_file():
        try:
            prior = json.loads(path.read_text(encoding="utf-8"))
            calls = int(prior.get("tool_call_count", 0))
        except (OSError, ValueError, json.JSONDecodeError):
            calls = 0
    result["tool_name"] = "generate_cangjie_skeleton"
    result["tool_call_count"] = calls + 1
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_skeleton(request: SkeletonRequest, workspace: str | Path = ".") -> dict[str, Any]:
    """Generate both skeleton trees and validate the source TODO tree with cjpm."""
    workspace = Path(workspace).resolve()
    schema_dir = schema_dir_for(request, workspace)
    if not schema_dir.is_dir():
        result = _result(
            request, workspace, "invalid_request",
            diagnostic=f"schema directory not found: {schema_dir}",
        )
        _write_receipt(request, workspace, result)
        return result

    missing = unresolved_type_occurrences(
        schema_dir, include_tests=request.include_tests
    )
    if missing:
        result = _result(
            request, workspace, "unresolved_types", unresolved_occurrences=missing,
            diagnostic="Skeleton generation requires every included type occurrence to be resolved.",
        )
        _write_receipt(request, workspace, result)
        return result

    from src.java.translation.create_skeleton import main as create_skeleton

    generation_log = io.StringIO()
    try:
        # create_skeleton.py uses repository-relative paths. Run it from the
        # MCP request workspace so direct service calls and MCP calls have the
        # same output root.
        with contextlib.chdir(workspace), contextlib.redirect_stdout(generation_log):
            create_skeleton(SimpleNamespace(
                project=request.project,
                model=request.model,
                temperature=request.temperature,
                suffix=request.suffix,
                translate_tests="true" if request.include_tests else "false",
                schemas_dir=str(schema_dir),
            ))
        paths = schema_paths(schema_dir, include_tests=request.include_tests)
        _write_placeholder_files(paths, request, workspace)
        returncode, diagnostic = _run_build(
            skeleton_dir_for(request, workspace), request.compile_timeout,
        )
        status = "success" if returncode == 0 else "build_failed"
        result = _result(
            request, workspace, status,
            build={"returncode": returncode, "diagnostic": diagnostic},
            generated_files=len(list(skeleton_dir_for(request, workspace).glob("src/**/*.cj"))),
            generation_log=generation_log.getvalue()[-8000:],
        )
    except Exception as exc:
        result = _result(
            request, workspace, "generation_failed",
            diagnostic=f"{type(exc).__name__}: {exc}",
            generation_log=generation_log.getvalue()[-8000:],
        )
    _write_receipt(request, workspace, result)
    return result
