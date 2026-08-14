"""Generate Cangjie interface shims for unmapped Java API types.

The shims are intentionally conservative. They make unmapped Java types
nameable in generated Cangjie skeletons without pretending that Java runtime
semantics exist in Cangjie. Method signatures are added only when a member is
observably used in the current Java fragment and the crawled Java API docs
contain a parseable signature.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.java.type_resolution.type_expression import (
    get_cangjie_type as deterministic_get_cangjie_type,
    is_known_type_expression,
    is_type_parameter,
    merge_java_base_type_map,
    merge_truthy_type_map,
    normalize_type_map_value,
    split_generic_args,
    strip_generic_params,
    strip_wildcard_bound,
)


JAVA_DOC_PATH = Path("data/java/crawl/java.base_module_doc.json")
SHIM_DIR = Path("data/java/type_resolution/generated_interface_shims")

_IDENT_RE = re.compile(r"[^0-9A-Za-z_]")
_RESERVED = {
    "abstract",
    "as",
    "break",
    "case",
    "catch",
    "class",
    "const",
    "continue",
    "do",
    "else",
    "enum",
    "extend",
    "for",
    "foreign",
    "func",
    "if",
    "import",
    "in",
    "init",
    "interface",
    "is",
    "let",
    "macro",
    "main",
    "match",
    "mut",
    "open",
    "operator",
    "override",
    "package",
    "private",
    "protected",
    "public",
    "quote",
    "redef",
    "return",
    "spawn",
    "static",
    "struct",
    "super",
    "synchronized",
    "this",
    "throw",
    "try",
    "type",
    "unsafe",
    "var",
    "where",
    "while",
}

_MODIFIERS = {
    "public",
    "protected",
    "private",
    "static",
    "final",
    "default",
    "abstract",
    "synchronized",
    "native",
    "strictfp",
    "transient",
    "volatile",
}


@dataclass
class ShimSignature:
    name: str
    java_name: str
    return_type: str
    parameters: list[dict[str, str]] = field(default_factory=list)
    static: bool = False
    source_signature: str = ""


@dataclass
class ConstructorSignature:
    parameters: list[dict[str, str]] = field(default_factory=list)
    source_signature: str = ""


def shim_map_path(project_name: str) -> Path:
    return SHIM_DIR / f"{project_name}.json"


def load_shim_type_map(project_name: str) -> dict[str, str]:
    path = shim_map_path(project_name)
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for source_type, entry in data.items():
        cangjie_type = entry.get("cangjie_type")
        if isinstance(cangjie_type, str) and cangjie_type:
            result[source_type] = cangjie_type
        canonical = entry.get("canonical_java_type")
        if isinstance(canonical, str) and canonical:
            result.setdefault(canonical, cangjie_type)
    return result


def merge_shim_type_map(type_map: dict[str, str], project_name: str) -> None:
    type_map.update(load_shim_type_map(project_name))


def render_shim_file(project_name: str, cjpm_name: str, output_roots: list[str | os.PathLike[str]]) -> bool:
    """Render the project compat shim source into each skeleton output root."""
    path = shim_map_path(project_name)
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = _coalesce_render_entries([entry for entry in data.values() if entry.get("cangjie_type")])
    if not entries:
        return False

    content = _render_cangjie_file(cjpm_name, entries)
    for root in output_roots:
        compat_dir = Path(root) / "src" / "compat"
        compat_dir.mkdir(parents=True, exist_ok=True)
        (compat_dir / "GeneratedInterfaceShims.cj").write_text(content, encoding="utf-8")
    return True


class InterfaceShimRegistry:
    def __init__(
        self,
        project_name: str,
        cjpm_name: str | None = None,
        deterministic_type_map: dict[str, Any] | None = None,
        import_map: dict[str, str] | None = None,
        java_base_map_path: str | os.PathLike[str] = "data/java/type_resolution/java_base_type_map.json",
        doc_path: str | os.PathLike[str] = JAVA_DOC_PATH,
    ) -> None:
        self.project_name = project_name
        self.cjpm_name = cjpm_name or project_name.replace("-", "_")
        self.import_line = f"import {self.cjpm_name}.compat.*"
        self.map_path = shim_map_path(project_name)
        self.java_base_map_path = Path(java_base_map_path)
        self.doc_path = Path(doc_path)
        self.import_map = import_map or {}
        self.type_map: dict[str, str] = deterministic_type_map.copy() if deterministic_type_map else {}
        self.java_base_records = self._load_java_base_records()
        self.canonical_index = self._build_canonical_index()
        self.doc_index = self._load_doc_index()
        self.entries = self._load_entries()

        for source_type, entry in self.entries.items():
            cangjie_type = entry.get("cangjie_type")
            if isinstance(cangjie_type, str) and cangjie_type:
                self.type_map[source_type] = cangjie_type
                canonical = entry.get("canonical_java_type")
                if isinstance(canonical, str) and canonical:
                    self.type_map.setdefault(canonical, cangjie_type)

    def set_import_map(self, import_map: dict[str, str] | None) -> None:
        self.import_map = import_map or {}

    def translate_or_create(
        self,
        source_type: str,
        fragment_body: str = "",
        type_variation: str = "",
        type_info: Any = None,
    ) -> str:
        translated = self._translate_expression(
            source_type,
            fragment_body=fragment_body,
            type_variation=type_variation,
            type_info=type_info,
            create=True,
        )
        if translated:
            self._save_entries()
        return translated

    def can_shim(self, source_type: str) -> bool:
        return bool(self._translate_expression(source_type, create=False))

    def _load_entries(self) -> dict[str, dict[str, Any]]:
        if not self.map_path.exists():
            return {}
        return json.loads(self.map_path.read_text(encoding="utf-8"))

    def _save_entries(self) -> None:
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        self.map_path.write_text(
            json.dumps(self.entries, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _load_java_base_records(self) -> dict[str, dict[str, Any]]:
        if not self.java_base_map_path.exists():
            return {}
        raw = json.loads(self.java_base_map_path.read_text(encoding="utf-8"))
        return {key: value for key, value in raw.items() if isinstance(value, dict)}

    def _build_canonical_index(self) -> dict[str, str]:
        suffixes: dict[str, set[str]] = {}
        for canonical in self.java_base_records:
            parts = canonical.split(".")
            for i in range(len(parts)):
                suffix = ".".join(parts[i:])
                suffixes.setdefault(suffix, set()).add(canonical)
            suffixes.setdefault(parts[-1], set()).add(canonical)
        return {
            suffix: next(iter(canonicals))
            for suffix, canonicals in suffixes.items()
            if len(canonicals) == 1
        }

    def _load_doc_index(self) -> dict[str, dict[str, Any]]:
        if not self.doc_path.exists():
            return {}
        data = json.loads(self.doc_path.read_text(encoding="utf-8"))
        index: dict[str, dict[str, Any]] = {}
        for _module_name, packages in data.items():
            if not isinstance(packages, dict):
                continue
            for package_name, groups in packages.items():
                if not isinstance(groups, dict):
                    continue
                for _group_name, classes in groups.items():
                    if not isinstance(classes, dict):
                        continue
                    for class_name, class_doc in classes.items():
                        if isinstance(class_doc, dict):
                            index[f"{package_name}.{class_name}"] = class_doc
                            index.setdefault(class_name, class_doc)
        return index

    def _translate_expression(
        self,
        source_type: str,
        fragment_body: str = "",
        type_variation: str = "",
        type_info: Any = None,
        create: bool = False,
    ) -> str:
        if not source_type:
            return ""
        source_type = strip_wildcard_bound(str(source_type).strip())
        if not source_type:
            return ""
        if _has_unsupported_type_syntax(source_type):
            return ""
        if is_known_type_expression(source_type, self.type_map):
            return deterministic_get_cangjie_type(source_type, self.type_map)
        if source_type.endswith("[]"):
            element = self._translate_expression(
                source_type[:-2],
                fragment_body=fragment_body,
                type_variation=type_variation,
                type_info=type_info,
                create=create,
            )
            return f"Array<{element}>" if element else ""

        if "<" in source_type and source_type.endswith(">"):
            base_type = source_type[: source_type.index("<")].strip()
            generic_part = source_type[source_type.index("<") + 1 : source_type.rindex(">")]
            if self._should_shim_terminal(base_type):
                return self._create_terminal_shim(
                    base_type,
                    original_source_type=source_type,
                    fragment_body=fragment_body,
                    type_variation=type_variation,
                    type_info=type_info,
                    create=create,
                )

            if is_known_type_expression(base_type, self.type_map):
                base_cangjie = deterministic_get_cangjie_type(base_type, self.type_map)
                if "<" in base_cangjie:
                    base_cangjie = base_cangjie.split("<", 1)[0].strip()
                resolved_args: list[str] = []
                for arg in split_generic_args(generic_part):
                    arg = strip_wildcard_bound(arg)
                    if arg == "Any":
                        resolved_args.append("Any")
                        continue
                    resolved = self._translate_expression(
                        arg,
                        fragment_body=fragment_body,
                        type_variation=type_variation,
                        type_info=type_info,
                        create=create,
                    )
                    if not resolved:
                        return ""
                    resolved_args.append(resolved)
                if not resolved_args:
                    return base_cangjie
                return f"{base_cangjie}<{', '.join(resolved_args)}>"
            return ""

        if not self._should_shim_terminal(source_type):
            return ""
        return self._create_terminal_shim(
            source_type,
            original_source_type=source_type,
            fragment_body=fragment_body,
            type_variation=type_variation,
            type_info=type_info,
            create=create,
        )

    def _should_shim_terminal(self, source_type: str) -> bool:
        source_type = strip_generic_params(source_type.strip())
        if not source_type or is_type_parameter(source_type):
            return False
        if _has_unsupported_type_syntax(source_type):
            return False
        if is_known_type_expression(source_type, self.type_map):
            return False
        canonical = self._canonical_java_type(source_type)
        record = self.java_base_records.get(canonical or "")
        if record:
            return record.get("category") == 3 and not normalize_type_map_value(record)
        return _looks_like_type_name(source_type)

    def _create_terminal_shim(
        self,
        source_type: str,
        original_source_type: str,
        fragment_body: str,
        type_variation: str,
        type_info: Any,
        create: bool,
    ) -> str:
        canonical = self._canonical_java_type(source_type) or source_type
        cangjie_type = self._shim_type_name(canonical)
        if not create:
            return cangjie_type

        existing = self.entries.get(original_source_type) or self.entries.get(source_type)
        if existing:
            cangjie_type = existing["cangjie_type"]
            self.type_map[original_source_type] = cangjie_type
            self.type_map[source_type] = cangjie_type
            self.type_map.setdefault(canonical, cangjie_type)
            self._merge_usage(existing, canonical, source_type, fragment_body, type_variation, type_info)
            return cangjie_type

        doc = self.doc_index.get(canonical) or self.doc_index.get(source_type) or {}
        entry = {
            "java_type": source_type,
            "source_type": original_source_type,
            "canonical_java_type": canonical,
            "cangjie_type": cangjie_type,
            "stub_type": f"{cangjie_type}Stub",
            "import": self.import_line,
            "kind": "interface_stub",
            "source": "generated_interface_shim",
            "doc_found": bool(doc),
            "constructors": [],
            "methods": [],
            "static_members": [],
            "warnings": [],
        }
        if not doc:
            entry["warnings"].append("java_api_doc_not_found")
        self.entries[original_source_type] = entry
        self.type_map[original_source_type] = cangjie_type
        self.type_map[source_type] = cangjie_type
        self.type_map.setdefault(canonical, cangjie_type)
        self._merge_usage(entry, canonical, source_type, fragment_body, type_variation, type_info)
        return cangjie_type

    def _merge_usage(
        self,
        entry: dict[str, Any],
        canonical: str,
        source_type: str,
        fragment_body: str,
        type_variation: str,
        type_info: Any,
    ) -> None:
        usage = _extract_usage(source_type, canonical, fragment_body, type_variation, type_info)
        doc = self.doc_index.get(canonical) or self.doc_index.get(source_type) or {}
        constructors = _select_constructors(doc, usage["constructors"], self.type_map)
        methods = _select_methods(doc, usage["methods"], self.type_map)
        static_members = sorted(set(entry.get("static_members", [])) | set(usage["static_methods"]))
        entry["constructors"] = _merge_signature_lists(entry.get("constructors", []), constructors)
        entry["methods"] = _merge_signature_lists(entry.get("methods", []), methods)
        entry["static_members"] = static_members
        if usage["static_methods"] and "static_members_recorded_only" not in entry["warnings"]:
            entry.setdefault("warnings", []).append("static_members_recorded_only")

    def _canonical_java_type(self, source_type: str) -> str:
        base = strip_generic_params(source_type.strip())
        base = base[:-2] if base.endswith("[]") else base
        if base in self.import_map:
            return self.import_map[base]
        if base in self.java_base_records:
            return base
        return self.canonical_index.get(base, "")

    def _shim_type_name(self, canonical: str) -> str:
        parts = [part for part in re.split(r"[.$]", canonical) if part]
        if parts and parts[0] != "java":
            parts = ["Java"] + parts
        name = "".join(_to_identifier_part(part) for part in parts)
        if not name:
            name = "JavaCompatType"
        if name[0].isdigit():
            name = f"Java{name}"
        return name


def _render_cangjie_file(cjpm_name: str, entries: list[dict[str, Any]]) -> str:
    lines = [
        f"// Package: {cjpm_name}.compat",
        f"package {cjpm_name}.compat",
        "",
        "// Imports Begin",
        "import std.collection.*",
        "// Imports End",
        "",
    ]
    for entry in sorted(entries, key=lambda item: item["cangjie_type"]):
        lines.extend(_render_entry(entry))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _coalesce_render_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_type: dict[str, dict[str, Any]] = {}
    for entry in entries:
        cangjie_type = entry.get("cangjie_type")
        if not cangjie_type:
            continue
        target = by_type.setdefault(cangjie_type, dict(entry))
        if target is entry:
            continue
        target["constructors"] = _merge_signature_lists(target.get("constructors", []), entry.get("constructors", []))
        target["methods"] = _merge_signature_lists(target.get("methods", []), entry.get("methods", []))
        target["static_members"] = sorted(set(target.get("static_members", [])) | set(entry.get("static_members", [])))
        target["warnings"] = sorted(set(target.get("warnings", [])) | set(entry.get("warnings", [])))
    return list(by_type.values())


def _render_entry(entry: dict[str, Any]) -> list[str]:
    interface_name = entry["cangjie_type"]
    stub_name = entry.get("stub_type") or f"{interface_name}Stub"
    lines = [
        f"public interface {interface_name} {{",
        "    // Methods Begin",
    ]
    # Cangjie overloads are distinguished by parameter *types* only (parameter
    # names do not affect the signature). The shim source often contains
    # multiple Java overloads that collapse to the same Cangjie parameter-type
    # tuple after type mapping (e.g. append(Object) / append(StringBuffer) both
    # become append(Any)). Emitting duplicates triggers "overload conflicts"
    # compile errors, so we deduplicate by (name, tuple-of-cangjie-param-types)
    # and keep the first occurrence.
    seen_method_sigs: set[tuple[str, tuple[str, ...]]] = set()
    for method in entry.get("methods", []):
        name = _safe_identifier(method.get("name", "method"))
        param_types = tuple(
            (p.get("type") or "Any") for p in method.get("parameters", [])
        )
        sig_key = (name, param_types)
        if sig_key in seen_method_sigs:
            continue
        seen_method_sigs.add(sig_key)
        lines.extend(_render_method(method, indent="    "))
        lines.append("")
    lines.extend(
        [
            "    // Methods End",
            "}",
            "",
            f"public open class {stub_name} <: {interface_name} {{",
            "    public init() {}",
        ]
    )
    seen_ctor_sigs: set[tuple[str, ...]] = set()
    for ctor in entry.get("constructors", []):
        param_types = tuple(
            (p.get("type") or "Any") for p in ctor.get("parameters", [])
        )
        if param_types in seen_ctor_sigs:
            continue
        seen_ctor_sigs.add(param_types)
        params = _render_params(ctor.get("parameters", []))
        if params:
            lines.append(f"    public init({params}) {{}}")
    lines.append("}")
    return lines


def _render_method(method: dict[str, Any], indent: str) -> list[str]:
    params = _render_params(method.get("parameters", []))
    return_type = method.get("return_type") or "Unit"
    name = _safe_identifier(method.get("name", "method"))
    lines = [
        f"{indent}func {name}({params}): {return_type} {{",
        f"{indent}    {_default_statement(return_type)}",
        f"{indent}}}",
    ]
    return lines


def _render_params(params: list[dict[str, str]]) -> str:
    rendered = []
    for idx, param in enumerate(params):
        name = _safe_identifier(param.get("name") or f"arg{idx}")
        cangjie_type = param.get("type") or "Any"
        rendered.append(f"{name}: {cangjie_type}")
    return ", ".join(rendered)


def _default_statement(return_type: str) -> str:
    base = return_type.split("<", 1)[0].strip()
    if base == "Unit":
        return "return"
    if base == "Bool":
        return "return false"
    if base in {"Int8", "Int16", "Int32", "Int64", "IntNative", "UInt8", "UInt16", "UInt32", "UInt64", "UIntNative"}:
        return "return 0"
    if base in {"Float16", "Float32", "Float64"}:
        return "return 0.0"
    if base == "String":
        return 'return ""'
    return "throw Exception('TODO')"


def _extract_usage(
    source_type: str,
    canonical: str,
    fragment_body: str,
    type_variation: str,
    type_info: Any,
) -> dict[str, set[str]]:
    usage = {"methods": set(), "static_methods": set(), "constructors": set()}
    if not fragment_body:
        return usage
    type_names = _candidate_java_type_names(source_type, canonical)
    variable_names: set[str] = set()
    if type_variation == "parameters" and isinstance(type_info, dict):
        name = type_info.get("name")
        if isinstance(name, str) and name:
            variable_names.add(name)

    for type_name in type_names:
        escaped = re.escape(type_name)
        for match in re.finditer(rf"\b{escaped}\s+([A-Za-z_][A-Za-z0-9_]*)\b", fragment_body):
            variable_names.add(match.group(1))
        if re.search(rf"\bnew\s+{escaped}\s*\(", fragment_body):
            usage["constructors"].add(type_name)
        for match in re.finditer(rf"\b{escaped}\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", fragment_body):
            usage["static_methods"].add(match.group(1))

    for var_name in variable_names:
        for match in re.finditer(rf"\b{re.escape(var_name)}\s*\.\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(", fragment_body):
            usage["methods"].add(match.group(1))
    return usage


def _candidate_java_type_names(source_type: str, canonical: str) -> list[str]:
    result = []
    for value in [source_type, canonical, canonical.split("java.", 1)[-1] if canonical.startswith("java.") else ""]:
        value = strip_generic_params(value).strip()
        if value and value not in result:
            result.append(value)
        simple = value.split(".")[-1] if value else ""
        if simple and simple not in result:
            result.append(simple)
    return result


def _select_methods(doc: dict[str, Any], used_names: set[str], type_map: dict[str, Any]) -> list[dict[str, Any]]:
    if not used_names:
        return []
    result = []
    methods = doc.get("methods", {})
    if not isinstance(methods, dict):
        return result
    for method_doc in methods.values():
        signature = method_doc.get("signature") if isinstance(method_doc, dict) else ""
        parsed = _parse_method_signature(signature, type_map)
        if parsed and (parsed.java_name in used_names or parsed.name in used_names) and not parsed.static:
            result.append(_signature_to_dict(parsed))
    return result


def _select_constructors(doc: dict[str, Any], used_constructors: set[str], type_map: dict[str, Any]) -> list[dict[str, Any]]:
    if not used_constructors:
        return []
    result = []
    constructors = doc.get("constructors", {})
    if not isinstance(constructors, dict):
        return result
    for ctor_doc in constructors.values():
        signature = ctor_doc.get("signature") if isinstance(ctor_doc, dict) else ""
        parsed = _parse_constructor_signature(signature, type_map)
        if parsed:
            result.append(_constructor_to_dict(parsed))
    return result


def _parse_method_signature(signature: str, type_map: dict[str, Any]) -> ShimSignature | None:
    signature = _normalize_signature(signature)
    if not signature or "(" not in signature or ")" not in signature:
        return None
    static = " static " in f" {signature} "
    before = signature[: signature.index("(")].strip()
    params_text = signature[signature.index("(") + 1 : signature.rindex(")")]
    before = _strip_leading_modifiers(before)
    before = _strip_leading_type_params(before)
    match = re.match(r"(.+?)\s+([A-Za-z_][A-Za-z0-9_]*)$", before)
    if not match:
        return None
    return_type = _to_cangjie_doc_type(match.group(1).strip(), type_map)
    java_name = match.group(2)
    name = _safe_identifier(java_name)
    params = _parse_parameters(params_text, type_map)
    return ShimSignature(
        name=name,
        java_name=java_name,
        return_type=return_type,
        parameters=params,
        static=static,
        source_signature=signature,
    )


def _parse_constructor_signature(signature: str, type_map: dict[str, Any]) -> ConstructorSignature | None:
    signature = _normalize_signature(signature)
    if not signature or "(" not in signature or ")" not in signature:
        return None
    params_text = signature[signature.index("(") + 1 : signature.rindex(")")]
    return ConstructorSignature(parameters=_parse_parameters(params_text, type_map), source_signature=signature)


def _parse_parameters(params_text: str, type_map: dict[str, Any]) -> list[dict[str, str]]:
    params_text = params_text.strip()
    if not params_text:
        return []
    result = []
    for idx, raw_param in enumerate(split_generic_args(params_text)):
        param = re.sub(r"@\w+(?:\([^)]*\))?\s*", "", raw_param.strip())
        words = [word for word in param.split() if word not in {"final"}]
        if not words:
            continue
        if len(words) == 1:
            java_type = words[0]
            name = f"arg{idx}"
        else:
            java_type = " ".join(words[:-1])
            name = words[-1]
        java_type = java_type.replace("...", "[]")
        result.append({"name": _safe_identifier(name), "type": _to_cangjie_doc_type(java_type, type_map)})
    return result


def _to_cangjie_doc_type(java_type: str, type_map: dict[str, Any]) -> str:
    java_type = strip_wildcard_bound(java_type.strip())
    if not java_type:
        return "Any"
    java_type = re.sub(r"\bextends\b.*", "", java_type).strip()
    if is_type_parameter(java_type):
        return "Any"
    if is_known_type_expression(java_type, type_map):
        cangjie_type = deterministic_get_cangjie_type(java_type, type_map)
        return cangjie_type if _is_compat_safe_type(cangjie_type) else "Any"
    if java_type.endswith("[]"):
        element = _to_cangjie_doc_type(java_type[:-2], type_map)
        return f"Array<{element}>"
    if "<" in java_type and java_type.endswith(">"):
        base = java_type[: java_type.index("<")].strip()
        if is_known_type_expression(base, type_map):
            base_cj = deterministic_get_cangjie_type(base, type_map)
            if "<" in base_cj:
                base_cj = base_cj.split("<", 1)[0].strip()
            args = [_to_cangjie_doc_type(arg, type_map) for arg in split_generic_args(java_type[java_type.index("<") + 1 : java_type.rindex(">")])]
            rendered = f"{base_cj}<{', '.join(args)}>" if args else base_cj
            return rendered if _is_compat_safe_type(rendered) else "Any"
    return "Any"


def _is_compat_safe_type(cangjie_type: str) -> bool:
    if not cangjie_type:
        return False
    base = cangjie_type.split("<", 1)[0].strip()
    return base in {
        "Any",
        "Bool",
        "Unit",
        "String",
        "Rune",
        "Int8",
        "Int16",
        "Int32",
        "Int64",
        "IntNative",
        "UInt8",
        "UInt16",
        "UInt32",
        "UInt64",
        "UIntNative",
        "Float16",
        "Float32",
        "Float64",
        "Array",
        "ArrayList",
        "HashMap",
        "HashSet",
        "Option",
    }


def _normalize_signature(signature: str) -> str:
    return re.sub(r"\s+", " ", str(signature).replace("\n", " ")).strip()


def _strip_leading_modifiers(text: str) -> str:
    words = text.split()
    while words and words[0] in _MODIFIERS:
        words.pop(0)
    return " ".join(words)


def _strip_leading_type_params(text: str) -> str:
    text = text.strip()
    if not text.startswith("<"):
        return text
    depth = 0
    for idx, char in enumerate(text):
        if char == "<":
            depth += 1
        elif char == ">":
            depth -= 1
            if depth == 0:
                return text[idx + 1 :].strip()
    return text


def _signature_to_dict(signature: ShimSignature) -> dict[str, Any]:
    return {
        "name": signature.name,
        "java_name": signature.java_name,
        "return_type": signature.return_type,
        "parameters": signature.parameters,
        "static": signature.static,
        "source_signature": signature.source_signature,
    }


def _constructor_to_dict(signature: ConstructorSignature) -> dict[str, Any]:
    return {
        "parameters": signature.parameters,
        "source_signature": signature.source_signature,
    }


def _merge_signature_lists(existing: list[dict[str, Any]], new_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged = list(existing)
    seen = {json.dumps(item, sort_keys=True) for item in merged}
    for item in new_items:
        key = json.dumps(item, sort_keys=True)
        if key not in seen:
            merged.append(item)
            seen.add(key)
    return merged


def _safe_identifier(name: str) -> str:
    name = _IDENT_RE.sub("_", str(name).strip())
    if not name:
        name = "arg"
    if name[0].isdigit():
        name = f"_{name}"
    if name in _RESERVED:
        name = f"{name}__"
    return name


def _to_identifier_part(value: str) -> str:
    value = _IDENT_RE.sub("_", value)
    pieces = [piece for piece in value.split("_") if piece]
    if not pieces:
        return ""
    return "".join(piece[:1].upper() + piece[1:] for piece in pieces)


def _looks_like_type_name(source_type: str) -> bool:
    source_type = strip_generic_params(source_type)
    parts = re.split(r"[.$]", source_type)
    if not parts or any(not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part) for part in parts):
        return False
    return any(part[:1].isupper() for part in parts)


def _has_unsupported_type_syntax(source_type: str) -> bool:
    if "|" in source_type or "&" in source_type:
        return True
    if re.search(r"\s", strip_generic_params(source_type)):
        return True
    return False
