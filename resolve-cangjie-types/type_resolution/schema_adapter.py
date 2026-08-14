from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from .models import TypeOccurrence, TypeResolutionRecord


def is_test_schema(schema_file: str) -> bool:
    return (
        ".src.test." in schema_file
        or schema_file.endswith(".src.test.json")
        or ".evosuite-tests." in schema_file
    )


def occurrence_id(
    schema_file: str,
    class_key: str,
    fragment_kind: str,
    fragment_key: str,
    variation: str,
    identifier: str,
) -> str:
    raw = "|".join((schema_file, class_key, fragment_kind, fragment_key, variation, identifier))
    return "occ-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def collect_project_types(schema_dir: str | Path, include_tests: bool = False) -> set[str]:
    result: set[str] = set()
    for path in sorted(Path(schema_dir).glob("*.json")):
        if is_test_schema(path.name) and not include_tests:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        source_path = str(data.get("path", "")).replace("\\", "/")
        package = ""
        if "/java/" in source_path:
            relative = source_path.rsplit("/java/", 1)[1]
            package = ".".join(relative.split("/")[:-1])
        for class_key, class_info in data.get("classes", {}).items():
            name = class_key.split(":", 1)[-1]
            result.add(name)
            if package:
                result.add(f"{package}.{name}")
            nested = class_info.get("nested_inside", "")
            if nested:
                nested_name = f"{str(nested).split(':', 1)[-1]}.{name}"
                result.add(nested_name)
                if package:
                    result.add(f"{package}.{nested_name}")
    return result


def extract_occurrences(schema_dir: str | Path, include_tests: bool = False) -> list[TypeOccurrence]:
    occurrences: list[TypeOccurrence] = []
    for path in sorted(Path(schema_dir).glob("*.json")):
        if is_test_schema(path.name) and not include_tests:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        import_map = data.get("import_map", {}) if isinstance(data.get("import_map"), dict) else {}
        source_path = str(data.get("path", ""))
        for class_key, class_info in data.get("classes", {}).items():
            class_name = class_key.split(":", 1)[-1]
            class_body = "\n".join(class_info.get("body", []))
            class_annotations = tuple(
                item for item in class_info.get("modifiers", []) if str(item).startswith("@")
            )
            class_modifiers = tuple(class_info.get("modifiers", []))
            for variation, role in (("extends", "extends"), ("implements", "implements")):
                for index, source_type in enumerate(class_info.get(variation, [])):
                    source_type = str(source_type)
                    identifier = f"{index}|{source_type}"
                    occurrences.append(
                        _make_occurrence(
                            path.name, source_path, class_key, class_name, "class", class_key,
                            variation, identifier, source_type, role, class_info, class_body,
                            class_annotations, class_modifiers, "", import_map,
                        )
                    )
            for index, parameter in enumerate(_type_parameters(class_info)):
                identifier = f"{index}|{parameter}"
                occurrences.append(
                    _make_occurrence(
                        path.name, source_path, class_key, class_name, "class", class_key,
                        "type_parameters", identifier, parameter, "type-parameter", class_info,
                        class_body, class_annotations, class_modifiers, "", import_map,
                    )
                )

            for field_key, field_info in class_info.get("fields", {}).items():
                body = "\n".join(field_info.get("body", []))
                annotations = tuple(
                    item for item in field_info.get("modifiers", []) if str(item).startswith("@")
                )
                for source_type in field_info.get("types", []):
                    occurrences.append(
                        _make_occurrence(
                            path.name, source_path, class_key, class_name, "field", field_key,
                            "types", str(source_type), str(source_type), "field", field_info, body,
                            annotations, tuple(field_info.get("modifiers", [])), "", import_map,
                        )
                    )

            for method_key, method_info in class_info.get("methods", {}).items():
                body = "\n".join(method_info.get("body", []))
                annotations = tuple(method_info.get("annotations", []))
                modifiers = tuple(method_info.get("modifiers", []))
                for source_type in method_info.get("return_types", []):
                    source_type = str(source_type)
                    if source_type.startswith("<") and source_type.endswith(">"):
                        continue
                    occurrences.append(
                        _make_occurrence(
                            path.name, source_path, class_key, class_name, "method", method_key,
                            "return_types", source_type, source_type, "return", method_info, body,
                            annotations, modifiers, "", import_map,
                        )
                    )
                for parameter in method_info.get("parameters", []):
                    source_type = str(parameter.get("type", ""))
                    identifier = "|".join(
                        (str(parameter.get("modifier", "")), source_type, str(parameter.get("name", "")))
                    )
                    param_annotations = tuple(
                        token for token in str(parameter.get("modifier", "")).split() if token.startswith("@")
                    )
                    occurrences.append(
                        _make_occurrence(
                            path.name, source_path, class_key, class_name, "method", method_key,
                            "parameters", identifier, source_type, "parameter", method_info, body,
                            param_annotations, modifiers, str(parameter.get("name", "")), import_map,
                        )
                    )
                for source_type in method_info.get("body_types", []):
                    occurrences.append(
                        _make_occurrence(
                            path.name, source_path, class_key, class_name, "method", method_key,
                            "body_types", str(source_type), str(source_type), "body-type", method_info,
                            body, (), modifiers, "", import_map,
                        )
                    )
                for index, parameter in enumerate(_type_parameters(method_info)):
                    identifier = f"{index}|{parameter}"
                    occurrences.append(
                        _make_occurrence(
                            path.name, source_path, class_key, class_name, "method", method_key,
                            "type_parameters", identifier, parameter, "type-parameter", method_info,
                            body, annotations, modifiers, "", import_map,
                        )
                    )
    return occurrences


def _type_parameters(fragment: dict) -> list[str]:
    value = fragment.get("type_parameters", [])
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("<") and text.endswith(">"):
            text = text[1:-1]
        return _split_top_level(text)
    if isinstance(value, list):
        return [
            str(item.get("declaration", item.get("name", "")) if isinstance(item, dict) else item).strip()
            for item in value
            if str(item).strip()
        ]
    return []


def _split_top_level(value: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in value:
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
        if char == "," and depth == 0:
            if current:
                parts.append("".join(current).strip())
                current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    return [item for item in parts if item]


def _make_occurrence(
    schema_file: str,
    source_path: str,
    class_key: str,
    class_name: str,
    fragment_kind: str,
    fragment_key: str,
    variation: str,
    identifier: str,
    source_type: str,
    role: str,
    fragment: dict,
    body: str,
    annotations: tuple[str, ...],
    modifiers: tuple[str, ...],
    parameter_name: str,
    import_map: dict[str, str],
) -> TypeOccurrence:
    base = re.split(r"[<\[]", source_type, maxsplit=1)[0].strip()
    if role == "type-parameter":
        bound = re.split(r"\s+(?:extends|super)\s+", source_type, maxsplit=1)
        base = bound[1].split("&", 1)[0].strip() if len(bound) > 1 else bound[0].strip()
    source_fqn = import_map.get(base, base)
    oid = occurrence_id(schema_file, class_key, fragment_kind, fragment_key, variation, identifier)
    return TypeOccurrence(
        occurrence_id=oid,
        schema_file=schema_file,
        source_path=source_path,
        class_key=class_key,
        fragment_kind=fragment_kind,
        fragment_key=fragment_key,
        variation=variation,
        identifier=identifier,
        source_type=source_type,
        source_fqn=source_fqn,
        role=role,
        symbol=f"{schema_file}::{class_name}::{fragment_key.split(':', 1)[-1]}::{role}",
        start_line=int(fragment.get("start", 0) or 0),
        end_line=int(fragment.get("end", 0) or 0),
        body=body,
        annotations=annotations,
        modifiers=modifiers,
        parameter_name=parameter_name,
        import_map=dict(import_map),
    )


def materialize_records(
    schema_dir: str | Path,
    occurrences: Iterable[TypeOccurrence],
    records: Iterable[TypeResolutionRecord],
) -> int:
    occurrence_map = {item.occurrence_id: item for item in occurrences}
    by_file: dict[str, list[TypeResolutionRecord]] = {}
    for record in records:
        occurrence = occurrence_map.get(record.occurrence_id)
        if occurrence is None:
            raise ValueError(f"record references unknown occurrence: {record.occurrence_id}")
        by_file.setdefault(occurrence.schema_file, []).append(record)

    count = 0
    for schema_file, file_records in by_file.items():
        path = Path(schema_dir) / schema_file
        data = json.loads(path.read_text(encoding="utf-8"))
        for record in sorted(file_records, key=lambda item: item.occurrence_id):
            occurrence = occurrence_map[record.occurrence_id]
            class_info = data["classes"][occurrence.class_key]
            if occurrence.fragment_kind == "class":
                fragment = class_info
            else:
                fragment_group = f"{occurrence.fragment_kind}s"
                fragment = class_info[fragment_group][occurrence.fragment_key]
            slots = fragment.setdefault("type_translations", {}).setdefault(
                occurrence.variation, {}
            )
            record_data = record.to_dict()
            target_type = record.target.type if record.target else ""
            imports = record.target.imports if record.target else ()
            slots[occurrence.identifier] = {
                "identifier": occurrence.identifier,
                "translated": record.status == "resolved",
                "attempted": True,
                "type_variation": occurrence.variation,
                "source_type": occurrence.source_type,
                "imports": "\n".join(imports),
                "translated_target_type": target_type,
                "reasoning": record.reasoning,
                "resolution_id": record.resolution_id,
                "status": record.status,
                "target": record_data["target"],
                "source_facts": record_data["source_facts"],
                "retrieval_route": record_data["retrieval_route"],
                "usage_requirements": record_data["usage_requirements"],
                "translation_guidance": record_data["translation_guidance"],
                "type_evidence": record_data["evidence"],
                "resolution": record_data,
            }
            count += 1
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
        temp_path.replace(path)
    return count


def get_materialized_resolution(fragment: dict, variation: str, identifier: str) -> dict:
    slot = fragment.get("type_translations", {}).get(variation, {}).get(identifier, {})
    if not isinstance(slot, dict):
        return {}
    resolution = slot.get("resolution")
    if isinstance(resolution, dict):
        return resolution
    return {}


def get_materialized_type(fragment: dict, variation: str, identifier: str) -> str:
    resolution = get_materialized_resolution(fragment, variation, identifier)
    if resolution.get("status") != "resolved":
        return ""
    target = resolution.get("target")
    if not isinstance(target, dict):
        return ""
    return str(target.get("type", "")).strip()
