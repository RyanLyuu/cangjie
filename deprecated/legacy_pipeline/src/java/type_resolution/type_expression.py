"""Deterministic Java type-expression translation helpers.

This module handles type names and parameterized type expressions that can be
translated without model reasoning. Higher-level Java generic language
features such as wildcard capture, bounds, and generic construction remain in
the generics rule prompt path.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


ERASED_GENERIC_TYPES = frozenset({"Any", "Nothing", "TypeInfo"})
JAVA_GENERIC_TYPE_MAP_PATH = "data/java/type_resolution/java_generic_type_map.json"

PRIMITIVE_TYPE_MAP = {
    "byte": "Int8",
    "short": "Int16",
    "int": "Int32",
    "long": "Int64",
    "float": "Float32",
    "double": "Float64",
    "boolean": "Bool",
    "char": "Rune",
    "void": "Unit",
    "Byte": "Int8",
    "Short": "Int16",
    "Integer": "Int32",
    "Long": "Int64",
    "Float": "Float32",
    "Double": "Float64",
    "Boolean": "Bool",
    "Character": "Rune",
    "Void": "Unit",
    "java.lang.Byte": "Int8",
    "java.lang.Short": "Int16",
    "java.lang.Integer": "Int32",
    "java.lang.Long": "Int64",
    "java.lang.Float": "Float32",
    "java.lang.Double": "Float64",
    "java.lang.Boolean": "Bool",
    "java.lang.Character": "Rune",
    "java.lang.Void": "Unit",
    "String": "String",
    "java.lang.String": "String",
    "Object": "Any",
    "java.lang.Object": "Any",
}

FUNCTIONAL_INTERFACE_MAP = {
    "Runnable": {"template": "() -> Unit", "params": []},
    "java.lang.Runnable": {"template": "() -> Unit", "params": []},
    "Callable": {"template": "() -> V", "params": ["V"]},
    "java.util.concurrent.Callable": {"template": "() -> V", "params": ["V"]},
    "Function": {"template": "(T) -> R", "params": ["T", "R"]},
    "java.util.function.Function": {"template": "(T) -> R", "params": ["T", "R"]},
    "Consumer": {"template": "(T) -> Unit", "params": ["T"]},
    "java.util.function.Consumer": {"template": "(T) -> Unit", "params": ["T"]},
    "Supplier": {"template": "() -> T", "params": ["T"]},
    "java.util.function.Supplier": {"template": "() -> T", "params": ["T"]},
    "Predicate": {"template": "(T) -> Bool", "params": ["T"]},
    "java.util.function.Predicate": {"template": "(T) -> Bool", "params": ["T"]},
    "BiFunction": {"template": "(T, U) -> R", "params": ["T", "U", "R"]},
    "java.util.function.BiFunction": {"template": "(T, U) -> R", "params": ["T", "U", "R"]},
    "BiConsumer": {"template": "(T, U) -> Unit", "params": ["T", "U"]},
    "java.util.function.BiConsumer": {"template": "(T, U) -> Unit", "params": ["T", "U"]},
    "BiPredicate": {"template": "(T, U) -> Bool", "params": ["T", "U"]},
    "java.util.function.BiPredicate": {"template": "(T, U) -> Bool", "params": ["T", "U"]},
    "UnaryOperator": {"template": "(T) -> T", "params": ["T"]},
    "java.util.function.UnaryOperator": {"template": "(T) -> T", "params": ["T"]},
    "BinaryOperator": {"template": "(T, T) -> T", "params": ["T"]},
    "java.util.function.BinaryOperator": {"template": "(T, T) -> T", "params": ["T"]},
    "Comparator": {"template": "(T, T) -> Int64", "params": ["T"]},
    "java.util.Comparator": {"template": "(T, T) -> Int64", "params": ["T"]},
    "BooleanSupplier": {"template": "() -> Bool", "params": []},
    "java.util.function.BooleanSupplier": {"template": "() -> Bool", "params": []},
    "IntFunction": {"template": "(Int32) -> R", "params": ["R"]},
    "java.util.function.IntFunction": {"template": "(Int32) -> R", "params": ["R"]},
    "IntConsumer": {"template": "(Int32) -> Unit", "params": []},
    "java.util.function.IntConsumer": {"template": "(Int32) -> Unit", "params": []},
    "IntSupplier": {"template": "() -> Int32", "params": []},
    "java.util.function.IntSupplier": {"template": "() -> Int32", "params": []},
    "IntPredicate": {"template": "(Int32) -> Bool", "params": []},
    "java.util.function.IntPredicate": {"template": "(Int32) -> Bool", "params": []},
    "IntUnaryOperator": {"template": "(Int32) -> Int32", "params": []},
    "java.util.function.IntUnaryOperator": {"template": "(Int32) -> Int32", "params": []},
    "IntBinaryOperator": {"template": "(Int32, Int32) -> Int32", "params": []},
    "java.util.function.IntBinaryOperator": {"template": "(Int32, Int32) -> Int32", "params": []},
    "IntToDoubleFunction": {"template": "(Int32) -> Float64", "params": []},
    "java.util.function.IntToDoubleFunction": {"template": "(Int32) -> Float64", "params": []},
    "IntToLongFunction": {"template": "(Int32) -> Int64", "params": []},
    "java.util.function.IntToLongFunction": {"template": "(Int32) -> Int64", "params": []},
    "LongFunction": {"template": "(Int64) -> R", "params": ["R"]},
    "java.util.function.LongFunction": {"template": "(Int64) -> R", "params": ["R"]},
    "LongConsumer": {"template": "(Int64) -> Unit", "params": []},
    "java.util.function.LongConsumer": {"template": "(Int64) -> Unit", "params": []},
    "LongSupplier": {"template": "() -> Int64", "params": []},
    "java.util.function.LongSupplier": {"template": "() -> Int64", "params": []},
    "LongPredicate": {"template": "(Int64) -> Bool", "params": []},
    "java.util.function.LongPredicate": {"template": "(Int64) -> Bool", "params": []},
    "LongUnaryOperator": {"template": "(Int64) -> Int64", "params": []},
    "java.util.function.LongUnaryOperator": {"template": "(Int64) -> Int64", "params": []},
    "LongBinaryOperator": {"template": "(Int64, Int64) -> Int64", "params": []},
    "java.util.function.LongBinaryOperator": {"template": "(Int64, Int64) -> Int64", "params": []},
    "LongToDoubleFunction": {"template": "(Int64) -> Float64", "params": []},
    "java.util.function.LongToDoubleFunction": {"template": "(Int64) -> Float64", "params": []},
    "LongToIntFunction": {"template": "(Int64) -> Int32", "params": []},
    "java.util.function.LongToIntFunction": {"template": "(Int64) -> Int32", "params": []},
    "DoubleFunction": {"template": "(Float64) -> R", "params": ["R"]},
    "java.util.function.DoubleFunction": {"template": "(Float64) -> R", "params": ["R"]},
    "DoubleConsumer": {"template": "(Float64) -> Unit", "params": []},
    "java.util.function.DoubleConsumer": {"template": "(Float64) -> Unit", "params": []},
    "DoubleSupplier": {"template": "() -> Float64", "params": []},
    "java.util.function.DoubleSupplier": {"template": "() -> Float64", "params": []},
    "DoublePredicate": {"template": "(Float64) -> Bool", "params": []},
    "java.util.function.DoublePredicate": {"template": "(Float64) -> Bool", "params": []},
    "DoubleUnaryOperator": {"template": "(Float64) -> Float64", "params": []},
    "java.util.function.DoubleUnaryOperator": {"template": "(Float64) -> Float64", "params": []},
    "DoubleBinaryOperator": {"template": "(Float64, Float64) -> Float64", "params": []},
    "java.util.function.DoubleBinaryOperator": {"template": "(Float64, Float64) -> Float64", "params": []},
    "DoubleToIntFunction": {"template": "(Float64) -> Int32", "params": []},
    "java.util.function.DoubleToIntFunction": {"template": "(Float64) -> Int32", "params": []},
    "DoubleToLongFunction": {"template": "(Float64) -> Int64", "params": []},
    "java.util.function.DoubleToLongFunction": {"template": "(Float64) -> Int64", "params": []},
    "ToDoubleFunction": {"template": "(T) -> Float64", "params": ["T"]},
    "java.util.function.ToDoubleFunction": {"template": "(T) -> Float64", "params": ["T"]},
    "ToDoubleBiFunction": {"template": "(T, U) -> Float64", "params": ["T", "U"]},
    "java.util.function.ToDoubleBiFunction": {"template": "(T, U) -> Float64", "params": ["T", "U"]},
    "ToIntFunction": {"template": "(T) -> Int32", "params": ["T"]},
    "java.util.function.ToIntFunction": {"template": "(T) -> Int32", "params": ["T"]},
    "ToIntBiFunction": {"template": "(T, U) -> Int32", "params": ["T", "U"]},
    "java.util.function.ToIntBiFunction": {"template": "(T, U) -> Int32", "params": ["T", "U"]},
    "ToLongFunction": {"template": "(T) -> Int64", "params": ["T"]},
    "java.util.function.ToLongFunction": {"template": "(T) -> Int64", "params": ["T"]},
    "ToLongBiFunction": {"template": "(T, U) -> Int64", "params": ["T", "U"]},
    "java.util.function.ToLongBiFunction": {"template": "(T, U) -> Int64", "params": ["T", "U"]},
    "ObjDoubleConsumer": {"template": "(T, Float64) -> Unit", "params": ["T"]},
    "java.util.function.ObjDoubleConsumer": {"template": "(T, Float64) -> Unit", "params": ["T"]},
    "ObjIntConsumer": {"template": "(T, Int32) -> Unit", "params": ["T"]},
    "java.util.function.ObjIntConsumer": {"template": "(T, Int32) -> Unit", "params": ["T"]},
    "ObjLongConsumer": {"template": "(T, Int64) -> Unit", "params": ["T"]},
    "java.util.function.ObjLongConsumer": {"template": "(T, Int64) -> Unit", "params": ["T"]},
}


def normalize_type_map_value(value: Any) -> str:
    """Return a concrete type string from plain or structured map values."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        mapped = value.get("mapping") or value.get("cangjie") or ""
        return mapped if isinstance(mapped, str) else ""
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return str(first.get("translated_type") or first.get("mapping") or "")
        if isinstance(first, str):
            return first
    return ""


def load_json_map(path: str | os.PathLike[str]) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_java_generic_type_map(
    path: str | os.PathLike[str] = JAVA_GENERIC_TYPE_MAP_PATH,
) -> dict[str, dict[str, Any]]:
    """Load Java generic raw-type fallback metadata."""
    raw_map = load_json_map(path)
    return {key: value for key, value in raw_map.items() if isinstance(value, dict)}


def merge_java_base_type_map(type_map: dict[str, str], path: str | os.PathLike[str]) -> None:
    """Merge java.base mappings and add unambiguous simple-name aliases.

    The source table is keyed by fully-qualified Java API names. Schemas often
    contain simple names such as ``List`` or ``Optional``, so we add aliases
    only when every mapped fully-qualified type with that simple name points to
    the same Cangjie type. Ambiguous names such as ``Entry`` are left unmapped.
    """
    raw_map = load_json_map(path)
    simple_aliases: dict[str, set[str]] = {}

    for key, value in raw_map.items():
        mapped = normalize_type_map_value(value)
        if not mapped:
            continue
        type_map[key] = mapped
        if "." in key:
            simple_aliases.setdefault(simple_name(key), set()).add(mapped)

    for alias, mappings in simple_aliases.items():
        if len(mappings) == 1 and alias not in type_map:
            type_map[alias] = next(iter(mappings))


def simple_name(type_name: str) -> str:
    return type_name.split(".")[-1] if "." in type_name else type_name


def is_type_parameter(type_name: str) -> bool:
    if not type_name:
        return False
    stripped = type_name.strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", stripped):
        return False
    # Exclude known JDK type acronyms that would otherwise be misclassified
    # as generic type parameters by the "short + uppercase" heuristic below.
    # These are real Java types (java.net.URL, java.net.URI, ...) that must
    # be looked up in the type map, not returned as-is.
    _JDK_ACRONYM_TYPES = frozenset({"URL", "URI", "UUID", "URI"})
    if stripped in _JDK_ACRONYM_TYPES:
        return False
    if len(stripped) == 1 and stripped.isalpha() and stripped.isupper():
        return True
    if stripped.isupper() and len(stripped) <= 3:
        return True
    return False


def strip_generic_params(type_str: str) -> str:
    if "<" in type_str:
        return type_str.split("<", 1)[0].strip()
    if "[" in type_str:
        return type_str.split("[", 1)[0].strip()
    return type_str.strip()


def strip_wildcard_bound(type_str: str) -> str:
    """Reduce an unbounded Java wildcard to the nearest usable type argument."""
    stripped = type_str.strip()
    if stripped == "?":
        return "Any"
    return stripped


def has_wildcard_bound(type_str: str) -> bool:
    stripped = type_str.strip()
    return stripped.startswith("? extends ") or stripped.startswith("? super ")


def split_generic_args(inner: str) -> list[str]:
    parts = []
    depth = 0
    current = ""
    for char in inner:
        if char == "<":
            depth += 1
            current += char
        elif char == ">":
            depth -= 1
            current += char
        elif char == "," and depth == 0:
            if current.strip():
                parts.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        parts.append(current.strip())
    return parts


def _lookup_type(type_name: str, type_map: dict[str, Any]) -> str:
    mapped = normalize_type_map_value(type_map.get(type_name))
    if mapped:
        return mapped
    short = simple_name(type_name)
    if short != type_name:
        mapped = normalize_type_map_value(type_map.get(short))
        if mapped:
            return mapped
    return PRIMITIVE_TYPE_MAP.get(type_name) or PRIMITIVE_TYPE_MAP.get(short, "")


def _generic_entry(base_type: str, type_map: dict[str, Any]) -> dict[str, Any] | None:
    entry = type_map.get(base_type)
    if isinstance(entry, dict) and "cangjie" in entry:
        return entry
    short = simple_name(base_type)
    if short != base_type:
        entry = type_map.get(short)
        if isinstance(entry, dict) and "cangjie" in entry:
            return entry
    return None


def _apply_hash_key_constraints(entry: dict[str, Any], resolved_args: list[str]) -> list[str]:
    adjusted = list(resolved_args)
    for index in entry.get("hash_key_indices", []):
        if isinstance(index, int) and 0 <= index < len(adjusted) and adjusted[index] == "Any":
            adjusted[index] = "AnyHashable"
    return adjusted


def _format_generic_type(base_cangjie: str, args: list[str]) -> str:
    if not args:
        return base_cangjie
    return f"{base_cangjie}<{', '.join(args)}>"


def _translate_raw_generic(entry: dict[str, Any]) -> str:
    base_cangjie = str(entry.get("cangjie") or "Any")
    if entry.get("erase_args"):
        return base_cangjie
    raw_args = [str(arg) for arg in entry.get("raw_args", [])]
    return _format_generic_type(base_cangjie, raw_args)


def _translate_parameterized_generic(
    entry: dict[str, Any],
    generic_parts: list[str],
    type_map: dict[str, Any],
) -> str:
    base_cangjie = str(entry.get("cangjie") or "Any")
    if entry.get("erase_args"):
        return base_cangjie
    resolved_parts = [get_cangjie_type(part, type_map) for part in generic_parts]
    resolved_parts = _apply_hash_key_constraints(entry, resolved_parts)
    return _format_generic_type(base_cangjie, resolved_parts)


def _functional_entry(base_type: str) -> dict | None:
    return FUNCTIONAL_INTERFACE_MAP.get(base_type) or FUNCTIONAL_INTERFACE_MAP.get(simple_name(base_type))


def _replace_type_variables(template: str, type_vars: list[str], resolved_args: list[str]) -> str:
    result = template
    for var, value in sorted(zip(type_vars, resolved_args), key=lambda item: -len(item[0])):
        result = re.sub(rf"\b{re.escape(var)}\b", value, result)
    return result


def _translate_functional(base_type: str, resolved_args: list[str]) -> str:
    entry = _functional_entry(base_type)
    if not entry:
        return ""
    params = entry["params"]
    if not resolved_args:
        resolved_args = ["Any"] * len(params)
    if len(resolved_args) < len(params):
        resolved_args = resolved_args + ["Any"] * (len(params) - len(resolved_args))
    return _replace_type_variables(entry["template"], params, resolved_args)


def is_known_type_expression(java_type: str, type_map: dict[str, Any]) -> bool:
    """Return whether ``java_type`` can be resolved without model reasoning.

    This is intentionally stricter than ``get_cangjie_type``. Skeleton
    generation may keep unknown generic base types as their simple names, but
    type-resolution should only skip the LLM when the expression is grounded in
    known maps, type parameters, arrays of known types, or known functional
    interfaces.
    """
    if not java_type:
        return False

    java_type = java_type.strip()
    if not java_type:
        return False
    if has_wildcard_bound(java_type):
        return False
    java_type = strip_wildcard_bound(java_type)
    if java_type == "Any":
        return True
    if is_type_parameter(java_type):
        return True
    if java_type.endswith("[]"):
        return is_known_type_expression(java_type[:-2], type_map)
    if _generic_entry(java_type, type_map):
        return True
    if _lookup_type(java_type, type_map):
        return True

    if "<" in java_type and java_type.endswith(">"):
        base_type = java_type[: java_type.index("<")].strip()
        generic_part = java_type[java_type.index("<") + 1 : java_type.rindex(">")]
        generic_parts = split_generic_args(generic_part)
        if not generic_parts:
            return False
        generic = _generic_entry(base_type, type_map)
        if not (generic or _lookup_type(base_type, type_map) or _functional_entry(base_type)):
            return False
        return all(is_known_type_expression(part, type_map) for part in generic_parts)

    return False


def get_cangjie_type(java_type: str, type_map: dict[str, Any]) -> str:
    """Translate a Java type expression deterministically when possible."""
    if not java_type:
        return "Any"

    java_type = java_type.strip()
    if not java_type:
        return "Any"
    java_type = strip_wildcard_bound(java_type)
    if java_type == "Any":
        return "Any"

    if is_type_parameter(java_type):
        return java_type

    if java_type.endswith("[]"):
        element_type = java_type[:-2]
        return f"Array<{get_cangjie_type(element_type, type_map)}>"

    generic = _generic_entry(java_type, type_map)
    if generic:
        return _translate_raw_generic(generic)

    direct = _lookup_type(java_type, type_map)
    if direct:
        return direct

    if "<" in java_type and java_type.endswith(">"):
        base_type = java_type[: java_type.index("<")].strip()
        generic_part = java_type[java_type.index("<") + 1 : java_type.rindex(">")]
        generic_parts = split_generic_args(generic_part)

        generic = _generic_entry(base_type, type_map)
        if generic:
            return _translate_parameterized_generic(generic, generic_parts, type_map)

        resolved_parts = [get_cangjie_type(part, type_map) for part in generic_parts]

        functional = _translate_functional(base_type, resolved_parts)
        if functional:
            return functional

        base_cangjie = _lookup_type(base_type, type_map)
        if not base_cangjie:
            base_cangjie = simple_name(base_type)
        if base_cangjie in ERASED_GENERIC_TYPES:
            return base_cangjie
        if "<" in base_cangjie:
            base_cangjie = base_cangjie.split("<", 1)[0].strip()
        if not base_cangjie:
            return "Any"

        return f"{base_cangjie}<{', '.join(resolved_parts)}>"

    functional = _translate_functional(java_type, [])
    if functional:
        return functional

    return "Any"


def build_default_type_map() -> dict[str, str]:
    """Build the canonical deterministic type map used by translation stages."""
    type_map: dict[str, str] = {}
    for key, value in PRIMITIVE_TYPE_MAP.items():
        type_map[key] = value
    merge_java_base_type_map(type_map, "data/java/type_resolution/java_base_type_map.json")
    type_map.update(load_java_generic_type_map())
    return type_map


def load_java_base_mapping(path: str | Path = "data/java/type_resolution/java_base_type_map.json") -> dict[str, str]:
    result: dict[str, str] = {}
    merge_java_base_type_map(result, path)
    return result
