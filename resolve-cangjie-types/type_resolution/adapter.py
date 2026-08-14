"""Compatibility adapter used by the restored skeleton and validation stages."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def merge_shim_type_map(type_map: dict[str, Any], project: str) -> dict[str, Any]:
    """Keep the legacy call surface; the new pipeline does not generate shims."""
    return type_map


def render_shim_file(project: str, cjpm_name: str, output_roots: list[str]) -> bool:
    """Return false because direct annotation does not synthesize compatibility types."""
    return False


def build_default_type_map() -> dict[str, str]:
    """The v2 skeleton does not consume a process-global type map."""
    return {}


def get_cangjie_type(java_type: str, type_map: dict[str, Any] | None = None) -> str:
    raise RuntimeError(
        "global Java-to-Cangjie mapping is disabled; consume a resolved occurrence target.type"
    )


def default_run_dir(project: str, model: str, temperature: str, suffix: str = "") -> Path:
    namespace = f"{model}/{temperature}{suffix}"
    return Path("data/java/type_resolution_runs") / project / namespace
