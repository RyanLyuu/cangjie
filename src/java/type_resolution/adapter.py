"""Compatibility surface for skeleton and fragment validation code."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def merge_shim_type_map(type_map: dict[str, Any], project: str) -> dict[str, Any]:
    return type_map


def render_shim_file(project: str, cjpm_name: str, output_roots: list[str]) -> bool:
    return False


def build_default_type_map() -> dict[str, str]:
    return {}


def get_cangjie_type(java_type: str, type_map: dict[str, Any] | None = None) -> str:
    value = (type_map or {}).get(java_type, "")
    if isinstance(value, dict):
        value = value.get("mapping") or value.get("cangjie") or ""
    if value:
        return str(value)
    raise ValueError(f"type has no materialized occurrence translation: {java_type}")


def default_run_dir(project: str, model: str, temperature: str, suffix: str = "") -> Path:
    namespace = f"{model}/{temperature}{suffix}"
    return Path("data/java/type_resolution_runs") / project / namespace
