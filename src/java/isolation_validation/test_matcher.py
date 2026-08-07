"""按 fragment 的 class/method 在 staging 中匹配 focal-call 测试。

`script.py` 生成的每个 `_test.cj` 头部都有形如
    // focal call: <pkg>.<Class>.<method>
的注释。本模块只按这个 focal 字段匹配，不放过 callgraph 间接命中。

匹配时会做必要的命名归一化：
- schema 位置前缀：`181-183:setEnabled` -> `setEnabled`
- Java 构造器：`<init>` -> class constructor fragment
- Java 内部类：`Ansi$NoAnsi` 可匹配 `NoAnsi` 或 `Ansi_NoAnsi`
- overload/decomposed 后缀：`render3` 可回退匹配 `render`
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

_FOCAL_RE = re.compile(r"//\s*focal call:\s*(\S+)")
_FOCAL_ARGC_RE = re.compile(r"//\s*focal argc:\s*(\d+)")
_FOCAL_ARG_TYPES_RE = re.compile(r"//[ \t]*focal arg types:[ \t]*([^\r\n]*)")
_TRAILING_DIGITS_RE = re.compile(r"^(.*?)(\d+)$")

_BOXED_TO_PRIMITIVE = {
    "Boolean": "boolean",
    "java.lang.Boolean": "boolean",
    "Byte": "byte",
    "java.lang.Byte": "byte",
    "Character": "char",
    "java.lang.Character": "char",
    "Double": "double",
    "java.lang.Double": "double",
    "Float": "float",
    "java.lang.Float": "float",
    "Integer": "int",
    "java.lang.Integer": "int",
    "Long": "long",
    "java.lang.Long": "long",
    "Short": "short",
    "java.lang.Short": "short",
    "String": "String",
    "java.lang.String": "String",
}


def _strip_position_prefix(name: str) -> str:
    """schema 内 fragment_name / class_name 形如 '14-17:Calculator'，剥掉位置前缀。"""
    if not name:
        return ""
    if ":" in name:
        return name.rsplit(":", 1)[-1]
    return name


def _dedupe(values: Iterable[str]) -> set[str]:
    return {value for value in values if value}


def _class_candidates(name: str) -> set[str]:
    """Return class-name forms that should be considered equivalent."""
    simple = _strip_position_prefix(name).replace("$", "_").replace(".", "_")
    if not simple:
        return set()

    parts = [part for part in simple.split("_") if part]
    candidates = {simple}
    if parts:
        candidates.add(parts[-1])
        if len(parts) >= 2:
            candidates.add("_".join(parts[-2:]))
    return candidates


def _method_candidates(name: str, *, class_candidates: set[str], is_constructor: bool) -> set[str]:
    """Return method-name forms that should be considered equivalent.

    We deliberately do not strip leading underscores. In jansi, `_appendEscapeSequence`
    and `appendEscapeSequence` are distinct Java methods, so collapsing them would
    over-match tests.
    """
    method = _strip_position_prefix(name)
    candidates = {method}

    if method in {"<init>", "init"} or is_constructor:
        candidates.update({"<init>", "init"})
        candidates.update(class_candidates)

    m = _TRAILING_DIGITS_RE.match(method)
    if m and m.group(1):
        candidates.add(m.group(1))

    return _dedupe(candidates)


def _normalize_type_name(type_name: str) -> str:
    name = _strip_position_prefix(type_name).strip()
    if not name:
        return ""
    name = re.sub(r"<.*>$", "", name).strip()
    array_suffix = ""
    while name.endswith("[]"):
        array_suffix += "[]"
        name = name[:-2].strip()
    if name in _BOXED_TO_PRIMITIVE:
        name = _BOXED_TO_PRIMITIVE[name]
    elif name.startswith("src.main.") or name.startswith("src.test.") or name.startswith("src."):
        name = name.replace("$", ".").rsplit(".", 1)[-1]
    elif "." in name:
        name = name.replace("$", ".").rsplit(".", 1)[-1]
    else:
        name = name.replace("$", "_")
    return f"{name}{array_suffix}"


def _type_compatible(expected: str, actual: str) -> bool:
    expected = _normalize_type_name(expected)
    actual = _normalize_type_name(actual)
    if not expected or not actual:
        return True
    if expected == actual:
        return True
    return False


def _parse_focal_from_head(head: str) -> Optional[tuple[set[str], set[str], Optional[int], Optional[list[str]]]]:
    m = _FOCAL_RE.search(head)
    if not m:
        return None

    focal = m.group(1).strip()
    owner, sep, method = focal.rpartition(".")
    if not sep or not owner or not method:
        return None

    owner_parts = owner.split(".")
    class_path = owner_parts[-1]
    if "$" in class_path:
        class_candidates = _class_candidates(class_path)
    else:
        class_candidates = _class_candidates(class_path)

    method_candidates = _method_candidates(
        method,
        class_candidates=class_candidates,
        is_constructor=method == "<init>",
    )
    argc_match = _FOCAL_ARGC_RE.search(head)
    focal_argc = int(argc_match.group(1)) if argc_match else None
    arg_types_match = _FOCAL_ARG_TYPES_RE.search(head)
    focal_arg_types: Optional[list[str]] = None
    if arg_types_match:
        raw = arg_types_match.group(1).strip()
        focal_arg_types = [] if not raw else [_normalize_type_name(part) for part in raw.split(",")]
    return class_candidates, method_candidates, focal_argc, focal_arg_types


def _fragment_argc(fragment: dict) -> Optional[int]:
    params = fragment.get("parameters")
    if isinstance(params, list):
        return len(params)

    signature = fragment.get("signature")
    if not isinstance(signature, str) or "(" not in signature or ")" not in signature:
        return None
    inside = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
    if not inside:
        return 0
    return len([part for part in inside.split(",") if part.strip()])


def _fragment_arg_types(fragment: dict) -> Optional[list[str]]:
    params = fragment.get("parameters")
    if isinstance(params, list):
        types: list[str] = []
        for param in params:
            if not isinstance(param, dict) or "type" not in param:
                return None
            types.append(_normalize_type_name(str(param["type"])))
        return types
    return None


def focal_matches_fragment(fragment: dict, test_cj: Path) -> bool:
    """Return whether one generated mock test's focal call matches a fragment."""
    target_classes = _class_candidates(fragment.get("class_name", ""))
    target_methods = _method_candidates(
        fragment.get("fragment_name", ""),
        class_candidates=target_classes,
        is_constructor=bool(fragment.get("is_constructor", False)),
    )
    if not target_classes or not target_methods:
        return False
    target_argc = _fragment_argc(fragment)
    target_arg_types = _fragment_arg_types(fragment)

    try:
        with test_cj.open("r", encoding="utf-8") as f:
            head = "".join([f.readline() for _ in range(96)])
    except OSError:
        return False

    parsed = _parse_focal_from_head(head)
    if not parsed:
        return False
    focal_classes, focal_methods, focal_argc, focal_arg_types = parsed

    if not (target_classes & focal_classes) or not (target_methods & focal_methods):
        return False
    if target_argc is not None and focal_argc is not None and target_argc != focal_argc:
        return False
    if target_arg_types is not None and focal_arg_types is not None:
        if len(target_arg_types) != len(focal_arg_types):
            return False
        if not all(_type_compatible(expected, actual) for expected, actual in zip(target_arg_types, focal_arg_types)):
            return False
    return True


def find_focal_tests(fragment: dict, staging_dir: Path) -> list[tuple[Path, Path | None]]:
    """返回 [(test_cj, workflow_json|None)]；只保留 focal 匹配本 fragment 的测试。"""
    if not staging_dir.is_dir():
        return []

    matched: list[tuple[Path, Path | None]] = []
    for test_cj in sorted(staging_dir.glob("*_test.cj")):
        if not focal_matches_fragment(fragment, test_cj):
            continue
        stem = test_cj.name[:-len("_test.cj")]
        wf = staging_dir / f"{stem}.workflow.json"
        matched.append((test_cj, wf if wf.exists() else None))
    return matched
