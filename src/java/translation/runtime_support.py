"""Install the minimal Cangjie runtime source required by skeleton generation."""

from __future__ import annotations

import re
from pathlib import Path


_ANY_HASHABLE_SOURCE = Path(__file__).resolve().parent / "AnyHashable.cj"
_RUNTIME_DIRECTORY = "runtime"
_ANY_HASHABLE_FILENAME = "AnyHashable.cj"


def any_hashable_package(package_name: str) -> str:
    return f"{package_name}.{_RUNTIME_DIRECTORY}"


def any_hashable_import(package_name: str) -> str:
    return f"import {any_hashable_package(package_name)}.AnyHashable"


def inject_any_hashable(target_src_dir: Path, package_name: str) -> list[Path]:
    if not _ANY_HASHABLE_SOURCE.is_file():
        raise FileNotFoundError(f"runtime source not found: {_ANY_HASHABLE_SOURCE}")
    target_dir = target_src_dir / _RUNTIME_DIRECTORY
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / _ANY_HASHABLE_FILENAME
    content = _ANY_HASHABLE_SOURCE.read_text(encoding="utf-8")
    content = re.sub(
        r"^\s*package\s+\S+",
        f"package {any_hashable_package(package_name)}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    target.write_text(content, encoding="utf-8")
    return [target]
