from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .models import OccurrenceResolution, TypeOccurrence


def is_test_schema(name: str) -> bool:
    return ".src.test." in name or ".evosuite-tests." in name


def schema_paths(schema_dir: str | Path, include_tests: bool = False) -> list[Path]:
    paths = []
    for path in sorted(Path(schema_dir).glob("*.json")):
        if not include_tests and is_test_schema(path.name):
            continue
        if "package-info" in path.name or "module-info" in path.name:
            continue
        paths.append(path)
    return paths


def load_schema(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def collect_project_types(paths: Iterable[Path]) -> set[str]:
    result = set()
    for path in paths:
        data = load_schema(path)
        source_path = str(data.get("path", "")).replace("\\", "/")
        package = ""
        if "/java/" in source_path:
            relative = source_path.rsplit("/java/", 1)[1]
            package = ".".join(relative.split("/")[:-1])
        for class_key in data.get("classes", {}):
            name = class_key.split(":", 1)[-1]
            result.add(name)
            if package:
                result.add(f"{package}.{name}")
    return result


def load_occurrences(path: str | Path) -> tuple[dict, list[TypeOccurrence]]:
    path = Path(path)
    data = load_schema(path)
    source_path = str(data.get("path", ""))
    rows = data.get("type_occurrences")
    if not isinstance(rows, list) or not rows:
        rows = _legacy_occurrences(data, path.name)
    occurrences = [
        TypeOccurrence.from_dict(row, schema_file=path.name, source_path=source_path)
        for row in rows
    ]
    seen = set()
    for occurrence in occurrences:
        if occurrence.occurrence_id in seen:
            raise ValueError(f"duplicate occurrence id in {path}: {occurrence.occurrence_id}")
        seen.add(occurrence.occurrence_id)
    return data, occurrences


def materialize_resolutions(path: str | Path, resolutions: Iterable[OccurrenceResolution]) -> int:
    path = Path(path)
    data = load_schema(path)
    count = 0
    for resolution in resolutions:
        occurrence = resolution.occurrence
        fragment = _fragment(data, occurrence)
        variation_slots = fragment.setdefault("type_translations", {}).setdefault(
            occurrence.variation, {}
        )
        timestamp = datetime.now(timezone.utc).isoformat()
        slot = {
            "identifier": occurrence.occurrence_id,
            "legacy_identifier": occurrence.identifier,
            "translated": True,
            "attempted": True,
            "type_variation": occurrence.variation,
            "timestamp": timestamp,
            "source_type": occurrence.source_type,
            "generation": resolution.decision.translated_target_type,
            "imports": "\n".join(resolution.decision.imports),
            "translated_target_type": resolution.decision.translated_target_type,
            "reasoning": resolution.decision.reasoning,
            "prompt": "",
            "feedback": "\n\n".join(resolution.feedback),
            "attempts": resolution.attempts,
            "status": resolution.status,
            "probe": {
                "success": resolution.probe.success,
                "diagnostic": resolution.probe.diagnostic,
                "command": list(resolution.probe.command),
            },
        }
        variation_slots[occurrence.occurrence_id] = slot

        # Keep the historical lookup key populated for existing skeletons and tools.
        legacy = dict(slot)
        legacy["identifier"] = occurrence.identifier
        variation_slots[occurrence.identifier] = legacy

        if resolution.status == "fallback-placeholder":
            placeholders = data.setdefault("generated_type_placeholders", [])
            placeholder = {
                "name": resolution.decision.translated_target_type,
                "occurrence_id": occurrence.occurrence_id,
                "reason": resolution.decision.reasoning,
            }
            if placeholder not in placeholders:
                placeholders.append(placeholder)
        count += 1

    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)
    return count


def get_materialized_type(fragment: dict, variation: str, identifier: str) -> str:
    slots = fragment.get("type_translations", {}).get(variation, {})
    if not isinstance(slots, dict):
        return ""
    direct = slots.get(identifier)
    if isinstance(direct, dict):
        target = str(direct.get("translated_target_type", "")).strip()
        if direct.get("translated") and target:
            return target
    for slot in slots.values():
        if not isinstance(slot, dict) or not slot.get("translated"):
            continue
        if identifier not in {
            str(slot.get("identifier", "")),
            str(slot.get("legacy_identifier", "")),
            str(slot.get("source_type", "")),
        }:
            continue
        target = str(slot.get("translated_target_type", "")).strip()
        if target:
            return target
    return ""


def iter_materialized_imports(fragment: dict):
    seen = set()
    for slots in fragment.get("type_translations", {}).values():
        if not isinstance(slots, dict):
            continue
        for slot in slots.values():
            if not isinstance(slot, dict) or not slot.get("translated"):
                continue
            for line in str(slot.get("imports", "")).splitlines():
                line = line.strip()
                if line.startswith("import ") and line not in seen:
                    seen.add(line)
                    yield line


def _fragment(data: dict, occurrence: TypeOccurrence) -> dict:
    class_info = data["classes"][occurrence.class_key]
    if occurrence.fragment_kind == "class":
        return class_info
    group = "fields" if occurrence.fragment_kind == "field" else "methods"
    return class_info[group][occurrence.fragment_key]


def _legacy_occurrences(data: dict, schema_file: str) -> list[dict]:
    rows = []
    source_path = str(data.get("path", ""))

    def add(class_key, kind, key, fragment, variation, identifier, source_type, role):
        start = int(fragment.get("start", 0) or 0)
        raw = "|".join((schema_file, class_key, kind, key, variation, identifier, str(start)))
        rows.append({
            "occurrence_id": "occ-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20],
            "class_key": class_key,
            "fragment_kind": kind,
            "fragment_key": key,
            "variation": variation,
            "identifier": identifier,
            "source_type": source_type,
            "role": role,
            "start_line": start,
            "start_column": 1,
            "end_line": start,
            "end_column": max(len(source_type), 1) + 1,
            "context_before": [],
            "source_line": "\n".join(fragment.get("body", [])[:1]),
            "context_after": fragment.get("body", [])[1:4],
            "source_path": source_path,
        })

    for class_key, class_info in data.get("classes", {}).items():
        for variation, role in (("extends", "extends"), ("implements", "implements")):
            for index, value in enumerate(class_info.get(variation, [])):
                add(class_key, "class", class_key, class_info, variation,
                    f"{index}|{value}", str(value), role)
        for index, value in enumerate(class_info.get("type_parameters", [])):
            add(class_key, "class", class_key, class_info, "type_parameters",
                f"{index}|{value}", str(value), "type-parameter")
        for key, field in class_info.get("fields", {}).items():
            for value in field.get("types", []):
                add(class_key, "field", key, field, "types", str(value), str(value), "field")
        for key, method in class_info.get("methods", {}).items():
            for value in method.get("return_types", []):
                if not (str(value).startswith("<") and str(value).endswith(">")):
                    add(class_key, "method", key, method, "return_types",
                        str(value), str(value), "return")
            for parameter in method.get("parameters", []):
                value = str(parameter.get("type", ""))
                identifier = "|".join((str(parameter.get("modifier", "")), value,
                                       str(parameter.get("name", ""))))
                add(class_key, "method", key, method, "parameters",
                    identifier, value, "parameter")
            for value in method.get("body_types", []):
                add(class_key, "method", key, method, "body_types",
                    str(value), str(value), "body-type")
            for index, value in enumerate(method.get("type_parameters", [])):
                add(class_key, "method", key, method, "type_parameters",
                    f"{index}|{value}", str(value), "type-parameter")
    return rows
