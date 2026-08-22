from __future__ import annotations

from pathlib import Path
from typing import Any

from src.java.type_resolution.schema import load_schema


_TYPE_FACT_KEYS = (
    "identifier",
    "legacy_identifier",
    "translated",
    "attempted",
    "type_variation",
    "source_type",
    "generation",
    "imports",
    "translated_target_type",
    "status",
)


_FRAGMENT_KEYS = (
    "start",
    "end",
    "body",
    "is_constructor",
    "annotations",
    "modifiers",
    "return_types",
    "type_parameters",
    "body_types",
    "signature",
    "parameters",
    "calls",
    "types",
    "enum_constant",
    "is_overload",
    "is_override",
    "needs_open",
)


_CLASS_KEYS = (
    "start",
    "end",
    "is_abstract",
    "is_interface",
    "is_enum",
    "modifiers",
    "type_parameters",
    "nested_inside",
    "nests",
    "implements",
    "extends",
    "cangjie_class_declaration",
)


def _compact_type_translations(value: Any) -> Any:
    """Keep materialized type facts and discard historical Agent noise."""

    if isinstance(value, dict):
        if any(key in value for key in _TYPE_FACT_KEYS):
            return {
                key: value[key]
                for key in _TYPE_FACT_KEYS
                if key in value
            }

        result: dict[str, Any] = {}

        for key, child in value.items():
            compact = _compact_type_translations(child)

            if compact in ({}, [], "", None):
                continue

            result[str(key)] = compact

        return result

    if isinstance(value, list):
        result = [
            _compact_type_translations(child)
            for child in value
        ]

        return [
            child
            for child in result
            if child not in ({}, [], "", None)
        ]

    return value


def _fragment_record(
    schema: dict[str, Any],
    fragment: dict[str, Any],
) -> dict[str, Any]:
    class_key = str(fragment.get("class_key", ""))
    fragment_name = str(fragment.get("fragment_name", ""))
    fragment_type = str(fragment.get("fragment_type", ""))

    class_info = schema.get("classes", {}).get(class_key)

    if not isinstance(class_info, dict):
        raise ValueError(
            "fragment class is missing from schema: "
            f"{class_key} / {fragment_name}"
        )

    collection_name = {
        "field": "fields",
        "method": "methods",
        "static_initializer": "static_initializers",
    }.get(fragment_type)

    if collection_name is None:
        raise ValueError(
            "unsupported fragment type: "
            f"{fragment_type} / {fragment_name}"
        )

    collection = class_info.get(collection_name, {})

    if not isinstance(collection, dict):
        raise ValueError(
            f"schema collection {collection_name!r} "
            f"is invalid for {class_key}"
        )

    record = collection.get(fragment_name)

    if not isinstance(record, dict):
        raise ValueError(
            "exact schema record missing: "
            f"{class_key} / {fragment_type} / {fragment_name}"
        )

    return record


def _compact_fragment(
    schema: dict[str, Any],
    fragment: dict[str, Any],
) -> dict[str, Any]:
    record = _fragment_record(schema, fragment)

    semantic = {
        key: record[key]
        for key in _FRAGMENT_KEYS
        if key in record
    }

    if "type_translations" in record:
        semantic["type_translations"] = _compact_type_translations(
            record.get("type_translations", {})
        )

    return {
        "descriptor": dict(fragment),
        "schema_record": semantic,
    }


def _compact_class(
    schema: dict[str, Any],
    class_key: str,
) -> dict[str, Any]:
    info = schema.get("classes", {}).get(class_key)

    if not isinstance(info, dict):
        raise ValueError(f"class metadata missing: {class_key}")

    result: dict[str, Any] = {
        "class_key": class_key,
        "class_name": class_key.split(":", 1)[-1],
    }

    for key in _CLASS_KEYS:
        if key in info:
            result[key] = info[key]

    result["type_translations"] = _compact_type_translations(
        info.get("type_translations", {})
    )

    return result


def _resolve_path(
    schema: dict[str, Any],
    key: str,
    workspace: Path,
) -> Path | None:
    raw = str(schema.get(key, "")).strip()

    if not raw:
        return None

    candidate = Path(raw)

    if not candidate.is_absolute():
        candidate = workspace / candidate

    return candidate.resolve() if candidate.is_file() else None


def _dependency_manifest(
    dependencies: list[Path],
    workspace: Path,
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []

    for dependency in dependencies:
        dependency = Path(dependency).resolve()
        data = load_schema(dependency)

        java_source = _resolve_path(data, "path", workspace)
        cangjie_target = _resolve_path(
            data,
            "cangjie_translations_skeleton_path",
            workspace,
        )

        result.append(
            {
                "schema": str(dependency),
                "java_source": str(java_source) if java_source is not None else "",
                "cangjie_target": (
                    str(cangjie_target)
                    if cangjie_target is not None
                    else ""
                ),
            }
        )

    return result


def build_compact_translation_context(
    *,
    schema: dict[str, Any],
    fragments: list[dict[str, Any]],
    source: Path | None,
    target: Path,
    semantic_dependencies: list[Path],
    workspace: Path,
) -> dict[str, Any]:
    """Build the complete semantic payload for one Stage3 Agent turn."""

    java_source = ""

    if source is not None:
        java_source = source.read_text(
            encoding="utf-8",
            errors="replace",
        )

    target_source = target.read_text(encoding="utf-8")

    class_keys: list[str] = []

    for fragment in fragments:
        class_key = str(fragment.get("class_key", ""))

        if class_key and class_key not in class_keys:
            class_keys.append(class_key)

    metadata: dict[str, Any] = {}

    for key in (
        "path",
        "imports",
        "import_map",
        "generated_type_placeholders",
    ):
        if key in schema:
            metadata[key] = schema[key]

    return {
        "java_source": java_source,
        "current_cangjie_target": target_source,
        "schema_metadata": metadata,
        "class_contexts": [
            _compact_class(schema, class_key)
            for class_key in class_keys
        ],
        "fragment_records": [
            _compact_fragment(schema, fragment)
            for fragment in fragments
        ],
        "semantic_dependencies": _dependency_manifest(
            semantic_dependencies,
            workspace,
        ),
    }
