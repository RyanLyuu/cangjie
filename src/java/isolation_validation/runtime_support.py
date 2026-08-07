"""注入/清理工程内的 mock 运行时支持文件（helper.cj、simple_ioc.cj）。

inject 模式：把 helper.cj 和 simple_ioc.cj 按 runtime 包名渲染后写入指定 src/runtime 目录。
clean  模式：从指定 src/runtime 目录删除这两个文件。

模板/源来源：
  - helper.cj      ← isolation_validation/helper.cj（替换 package 行）
  - simple_ioc.cj  ← isolation_validation/simple_ioc.cj（替换 package 行）
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_HELPER_TEMPLATE = _THIS_DIR / "helper.cj"
_SIMPLE_IOC_SRC = _THIS_DIR / "simple_ioc.cj"
_ANY_HASHABLE_SRC = _THIS_DIR.parent / "translation" / "AnyHashable.cj"

HELPER_FILENAME = "helper.cj"
SIMPLE_IOC_FILENAME = "simple_ioc.cj"
ANY_HASHABLE_FILENAME = "AnyHashable.cj"
RUNTIME_DIRNAME = "runtime"


def _render_with_package(source: Path, package_name: str) -> str:
    content = source.read_text(encoding="utf-8")
    if "__PACKAGE__" in content:
        return content.replace("__PACKAGE__", package_name)
    return re.sub(r"^\s*package\s+\S+", f"package {package_name}", content, count=1, flags=re.MULTILINE)


def runtime_package(package_name: str) -> str:
    return f"{package_name}.{RUNTIME_DIRNAME}"


def runtime_dir(target_src_dir: Path) -> Path:
    return target_src_dir / RUNTIME_DIRNAME


def inject(target_src_dir: Path, package_name: str) -> list[Path]:
    target_dir = runtime_dir(target_src_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    runtime_pkg = runtime_package(package_name)
    written: list[Path] = []
    for source, name in [
        (_HELPER_TEMPLATE, HELPER_FILENAME),
        (_SIMPLE_IOC_SRC, SIMPLE_IOC_FILENAME),
    ]:
        if not source.exists():
            print(f"[runtime_support] skip {name}: source missing at {source}")
            continue
        target = target_dir / name
        target.write_text(_render_with_package(source, runtime_pkg), encoding="utf-8")
        written.append(target)
    return written


def any_hashable_package(package_name: str) -> str:
    return runtime_package(package_name)


def any_hashable_import(package_name: str) -> str:
    return f"import {any_hashable_package(package_name)}.AnyHashable"


def inject_any_hashable(target_src_dir: Path, package_name: str) -> list[Path]:
    target_dir = runtime_dir(target_src_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    if not _ANY_HASHABLE_SRC.exists():
        print(f"[runtime_support] skip {ANY_HASHABLE_FILENAME}: source missing at {_ANY_HASHABLE_SRC}")
        return written

    target = target_dir / ANY_HASHABLE_FILENAME
    target.write_text(
        _render_with_package(_ANY_HASHABLE_SRC, any_hashable_package(package_name)),
        encoding="utf-8",
    )
    written.append(target)
    return written


def clean(target_src_dir: Path) -> list[Path]:
    removed: list[Path] = []
    target_dir = runtime_dir(target_src_dir)
    for name in (HELPER_FILENAME, SIMPLE_IOC_FILENAME):
        target = target_dir / name
        if target.exists():
            target.unlink()
            removed.append(target)
    return removed


def main() -> None:
    parser = argparse.ArgumentParser(description="注入/清理 mock 运行时支持文件")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_inject = sub.add_parser("inject", help="写入 helper.cj 与 simple_ioc.cj 到 src/runtime")
    p_inject.add_argument("target", help="目标 src 目录")
    p_inject.add_argument("package", help="目标包名")

    p_clean = sub.add_parser("clean", help="从 src/runtime 删除 helper.cj 与 simple_ioc.cj")
    p_clean.add_argument("target", help="目标 src 目录")

    args = parser.parse_args()
    target = Path(args.target)

    if args.cmd == "inject":
        for path in inject(target, args.package):
            print(f"[runtime_support] injected: {path}")
    elif args.cmd == "clean":
        for path in clean(target):
            print(f"[runtime_support] removed: {path}")


if __name__ == "__main__":
    main()
