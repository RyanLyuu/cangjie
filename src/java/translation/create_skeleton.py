#!/usr/bin/env python3
"""
Create Cangjie skeleton files from Java schema.
Adapted from TRAM but targeting Cangjie instead of Python.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
from src.java.isolation_validation import runtime_support
from src.java.utils.get_dependencies import get_dependencies
from src.java.utils.get_class_order import get_class_order
from src.java.utils.get_custom_types import get_custom_type_translation_map, get_custom_types
from src.java.utils.package_collapse import (
    compute_schema_effective_subpath_map as _compute_schema_effective_subpath_map,
    compute_skeleton_sub_path as _compute_skeleton_sub_path,
    get_cangjie_package as _get_cangjie_package,
    get_effective_skeleton_sub_path as _get_effective_skeleton_sub_path,
    remove_collapsed_output_dirs as _remove_collapsed_output_dirs,
)


def _load_type_resolution_backend():
    """Load the baseline compatibility adapter."""
    from src.java.type_resolution.adapter import (
        build_default_type_map,
        get_cangjie_type,
        merge_shim_type_map,
        render_shim_file,
    )

    return (
        build_default_type_map,
        get_cangjie_type,
        merge_shim_type_map,
        render_shim_file,
    )


def normalize_type_map_value(value):
    """Normalize an adapter value without making a type decision."""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        mapped = value.get('mapping') or value.get('cangjie') or ''
        return mapped if isinstance(mapped, str) else ''
    return ''


def split_generic_args(inner):
    """Split a generic argument list while preserving nested expressions."""
    parts = []
    depth = 0
    current = []
    for char in inner:
        if char == '<':
            depth += 1
        elif char == '>':
            depth -= 1
        if char == ',' and depth == 0:
            parts.append(''.join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append(''.join(current).strip())
    return parts


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _should_include_test_sources(args):
    return _as_bool(getattr(args, "translate_tests", False))


def _is_test_schema_name(schema_fname):
    return (
        ".src.test." in schema_fname
        or schema_fname.endswith(".src.test.json")
        or ".evosuite-tests." in schema_fname
    )


def _remove_generated_test_skeletons(*roots):
    for root in roots:
        src_dir = Path(root) / "src"
        if not src_dir.is_dir():
            continue
        for test_file in src_dir.rglob("*_test.cj"):
            test_file.unlink()


def _clean_generated_skeleton_sources(*roots):
    """Remove stale generated Cangjie sources before regenerating skeletons."""
    for root in roots:
        src_dir = Path(root) / "src"
        if not src_dir.is_dir():
            continue
        for source_file in src_dir.rglob("*.cj"):
            source_file.unlink()
        for directory in sorted(
                (path for path in src_dir.rglob("*") if path.is_dir()),
                key=lambda path: len(path.parts),
                reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass


def _field_name_from_key(field_key):
    return field_key.split(':', 1)[1].strip() if ':' in field_key else field_key.strip()


def _is_framework_ignored_field(field_key, field_info=None):
    """Skip Java metadata fields that are not useful translation targets."""
    return _field_name_from_key(field_key).startswith("serialVersionUID")


def _stdx_static_path():
    sdk_home = (
        os.environ.get("CANGJIE_HOME")
        or os.environ.get("CANGJIE_SDK_HOME")
        or "/home/lin/Downloads/cangjie-sdk-linux-x64-1.0.5/cangjie"
    )
    return str(Path(sdk_home) / "linux_x86_64_cjnative" / "static" / "stdx")


def _uses_stdx_imports(imports_text):
    return any(
        line.strip().startswith("import stdx.")
        for line in str(imports_text).splitlines()
    )


def _stdx_link_option():
    return (
        "-lstdx.net.http -lstdx.net.tls -lstdx.net.tlsFFI -lstdx.net "
        "-lstdx.log -lstdx.logger -lstdx.encoding.json.stream "
        "-lstdx.encoding.json -lstdx.serialization.serialization"
    )


def _load_third_party_libraries(path="data/java/type_resolution/java_base_third_party_libraries.json"):
    if not os.path.exists(path):
        return {}
    with open(path, 'r') as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _import_prefix(import_line):
    text = str(import_line or '').strip()
    if not text.startswith('import '):
        return ''
    target = text[len('import '):].strip()
    if target.endswith('.*'):
        target = target[:-2]
    return target


def _third_party_import_prefixes(lib_info):
    prefixes = set()
    for imp in _normalize_import_list(lib_info.get('validated_imports')):
        prefix = _import_prefix(imp)
        if prefix:
            prefixes.add(prefix)
    return prefixes


def _detect_third_party_dependencies(imports_text, third_party_libraries):
    used = set()
    import_prefixes = [
        prefix for prefix in (
            _import_prefix(line) for line in str(imports_text or '').splitlines()
        )
        if prefix
    ]
    for lib_name, lib_info in third_party_libraries.items():
        if not isinstance(lib_info, dict):
            continue
        for lib_prefix in _third_party_import_prefixes(lib_info):
            for import_prefix in import_prefixes:
                if import_prefix == lib_prefix or import_prefix.startswith(f"{lib_prefix}."):
                    used.add(lib_name)
                    break
            if lib_name in used:
                break
    return used


def _render_dependency_lines(third_party_libraries, used_third_party_libs):
    lines = []
    for lib_name in sorted(used_third_party_libs):
        lib_info = third_party_libraries.get(lib_name, {})
        dependency = lib_info.get('dependency', {}) if isinstance(lib_info, dict) else {}
        git_url = dependency.get('git') or lib_info.get('url')
        if git_url:
            lines.append(f'{lib_name} = {{ git = "{git_url}" }}')
    return lines


def _generate_cjpm_content(cjpm_name, output_type, include_stdx,
                           third_party_libraries=None, used_third_party_libs=None):
    link_option = _stdx_link_option() if include_stdx else ""
    dependency_lines = _render_dependency_lines(
        third_party_libraries or {},
        used_third_party_libs or set()
    )
    dependencies = "\n".join(dependency_lines)
    stdx_dependency = ""
    if include_stdx:
        stdx_dependency = f"""
[target.x86_64-unknown-linux-gnu]
  [target.x86_64-unknown-linux-gnu.bin-dependencies]
    path-option = ["{_stdx_static_path()}"]
"""

    return f"""[package]
  cjc-version = "1.0.5"
  name = "{cjpm_name}"
  description = "nothing here"
  version = "1.0.0"
  src-dir = "src"
  target-dir = "target"
  output-type = "{output_type}"
  compile-option = "-Woff unused --error-count-limit all"
  override-compile-option = ""
  link-option = "{link_option}"
  package-configuration = {{}}

[dependencies]
{dependencies}
{stdx_dependency}"""


# ============================================================
# Schema Preprocessing
# ============================================================


def annotate_method_flags(schema, class_to_methods=None, all_schema_classes=None):
    """Annotate methods with is_overload, is_override, and needs_open flags.

    Also marks parent class methods as needing 'open' when they are overridden.
    """
    if class_to_methods is None:
        class_to_methods = {}
    if all_schema_classes is None:
        all_schema_classes = {}

    duplicate_methods = {}
    for class_ in schema['classes']:
        duplicate_methods.setdefault(class_, {})
        for method in schema['classes'][class_]['methods']:
            schema['classes'][class_]['methods'][method]['is_overload'] = False
            schema['classes'][class_]['methods'][method]['is_override'] = False
            schema['classes'][class_]['methods'][method]['needs_open'] = False
            method_name = method.split(':')[1].strip()
            duplicate_methods[class_].setdefault(method_name, [])
            duplicate_methods[class_][method_name].append(method)

    for class_ in duplicate_methods:
        for method_name in duplicate_methods[class_]:
            if len(duplicate_methods[class_][method_name]) > 1:
                for k in duplicate_methods[class_][method_name]:
                    schema['classes'][class_]['methods'][k]['is_overload'] = True

    # Detect overriding: check if method exists in parent class (using cross-schema class_to_methods)
    for class_key in schema['classes']:
        class_name = class_key.split(':')[-1]
        class_info = schema['classes'][class_key]
        extends = class_info.get('extends', [])
        parent_class_short = extends[0].split('.')[-1] if extends else None

        if parent_class_short and parent_class_short in class_to_methods:
            parent_methods = class_to_methods[parent_class_short].get('methods', [])
            # Check each method in current class
            for method_key in schema['classes'][class_key]['methods']:
                method_name = method_key.split(':')[1].strip()
                if method_name not in parent_methods:
                    continue

                # Get child method parameter types
                child_method = schema['classes'][class_key]['methods'][method_key]
                child_param_types = [p['type'] for p in child_method.get('parameters', [])]

                # Find matching parent method with same name AND parameter types
                is_override = False
                if parent_class_short in all_schema_classes:
                    for pm_key, pm_info in all_schema_classes[parent_class_short].get('methods', {}).items():
                        pm_name = pm_key.split(':')[1].strip()
                        if pm_name == method_name:
                            parent_param_types = [p['type'] for p in pm_info.get('parameters', [])]
                            if child_param_types == parent_param_types:
                                is_override = True
                                break

                if is_override:
                    # This is an override
                    schema['classes'][class_key]['methods'][method_key]['is_override'] = True

                    # Also mark parent method as needing 'open'
                    if parent_class_short in all_schema_classes:
                        for parent_method_key in all_schema_classes[parent_class_short].get('methods', {}):
                            parent_method_name = parent_method_key.split(':')[1].strip()
                            if parent_method_name == method_name:
                                all_schema_classes[parent_class_short]['methods'][parent_method_key]['needs_open'] = True

    return schema


# ============================================================
# Type Resolution
# ============================================================


def get_cangjie_type(java_type, type_map):
    """Delegate conversion to the baseline compatibility adapter."""
    _, resolve_type, _, _ = _load_type_resolution_backend()
    return resolve_type(java_type, type_map)


def get_materialized_type(fragment_info, variation, identifier, source_type, type_map):
    """Read the historical direct target field and fail closed when unresolved."""
    from src.java.type_resolution.schema import get_materialized_type

    resolved = get_materialized_type(fragment_info, variation, identifier)
    if not resolved:
        raise ValueError(
            f"unresolved type occurrence: variation={variation}, "
            f"identifier={identifier}, source_type={source_type}"
        )
    return resolved


def get_parameter_type(method_info, parameter, type_map):
    source_type = parameter.get('type', 'Any')
    identifier = '|'.join((
        str(parameter.get('modifier', '')),
        str(source_type),
        str(parameter.get('name', '')),
    ))
    return get_materialized_type(
        method_info, 'parameters', identifier, source_type, type_map
    )


def normalize_class_name(class_name, type_map):
    """Normalize a class name using type map."""
    if not class_name:
        return class_name

    class_name = class_name.strip()

    # Handle qualified names
    if '.' in class_name:
        short_name = class_name.split('.')[-1]
        if short_name in type_map:
            return normalize_type_map_value(type_map[short_name]) or short_name
        return short_name

    if class_name in type_map:
        return normalize_type_map_value(type_map[class_name]) or class_name

    return class_name


def _filter_jdk_types(type_list, class_to_package):
    """Filter out JDK types not present in the project from extends/implements."""
    if not type_list:
        return []
    result = []
    for t in type_list:
        short_name = t.split('.')[-1] if '.' in t else t
        if short_name in class_to_package:
            result.append(t)
    return result


def _get_class_parent(class_name, class_info, class_to_package, type_map):
    """Resolve class declaration parent from extends/implements.

    Returns (parent_name, implements_str) — both can be empty.
    """
    # Try single extends first
    parent_name = ''
    extends = class_info.get('extends', [])
    implements = class_info.get('implements', [])
    for index, t in enumerate(extends or []):
        parent_name = get_materialized_type(
            class_info, 'extends', f'{index}|{t}', t, type_map
        )
        break

    # Fallback to implements
    impls = []
    for index, t in enumerate(implements or []):
        impls.append(get_materialized_type(
            class_info, 'implements', f'{index}|{t}', t, type_map
        ))

    return parent_name, ' & '.join(impls)


def _get_interface_parents(class_name, class_info, class_to_package, type_map):
    """Resolve interface extends.

    Returns list of extended interface names.
    """
    result = []
    for index, t in enumerate(class_info.get('extends', [])):
        result.append(get_materialized_type(
            class_info, 'extends', f'{index}|{t}', t, type_map
        ))

    return result


# ============================================================
# Modifier Decisions
# ============================================================


def get_access_modifier(modifiers):
    """Convert Java modifiers to Cangjie."""
    if 'public' in modifiers:
        return 'public '
    elif 'protected' in modifiers:
        return 'protected '
    elif 'private' in modifiers:
        return 'private '
    return ''


def is_static(modifiers):
    return 'static' in modifiers


def get_method_modifiers(modifiers, is_override=False, is_interface=False,
                         is_constructor=False, needs_open=False):
    """Build Cangjie method modifier prefix string.

    Returns e.g. 'public override open ', 'public override ', 'public open ',
    'public static ', ''.
    Interface methods return '' (modifiers are implicitly public open).
    Constructors return only access modifier (no open/override/static).
    The caller handles the func/init keyword.
    """
    if is_interface:
        return ""

    if is_constructor:
        return get_access_modifier(modifiers)

    access_mod = get_access_modifier(modifiers)

    if is_static(modifiers):
        return f"{access_mod}static "

    if is_override:
        if not access_mod:
            access_mod = "public "
        if needs_open:
            return f"{access_mod}override open "
        return f"{access_mod}override "

    if method_needs_open(modifiers):
        if not access_mod:
            access_mod = "public "
        return f"{access_mod}open "

    return access_mod


def get_class_modifiers(java_modifiers, is_abstract, was_nested=False):
    """Build Cangjie class modifier prefix string.

    Returns e.g. 'public abstract ', 'public open ', 'public ', ''.

    If the class was a Java nested/inner class extracted to top-level,
    strip 'private' since Cangjie's file-level 'private' is stricter
    than Java's 'private to enclosing class'.
    """
    access_mod = get_access_modifier(java_modifiers)
    if was_nested and access_mod == 'private ':
        access_mod = ''
    if is_abstract:
        return f"{access_mod}abstract "
    if class_needs_open(java_modifiers, is_abstract):
        return f"{access_mod}open "
    return access_mod


def get_interface_modifiers(java_modifiers):
    """Build Cangjie interface modifier prefix string.

    Returns e.g. 'public ', ''.
    Interfaces are implicitly open in Cangjie — no 'open' needed.
    """
    return get_access_modifier(java_modifiers)


def get_field_modifiers(modifiers):
    """Build Cangjie field modifier prefix string.

    Returns e.g. 'static let ', 'static var ', 'let ', 'var '.
    Java instance final fields can be assigned in constructors. Skeletons
    initialize fields with TODO placeholders, so instance fields must stay
    mutable during fragment validation.
    """
    parts = []
    static_field = is_static(modifiers)
    if static_field:
        parts.append('static')
    if static_field and 'final' in modifiers:
        parts.append('let')
    else:
        parts.append('var')
    return ' '.join(parts) + ' '


def get_method_params(method_info, type_map):
    """Extract Cangjie parameter list from method info.

    Returns list of strings like ['name: String', 'count: Int32'].
    """
    params = method_info.get('parameters', [])
    result = []
    for param in params:
        param_name = param.get('name', 'arg')
        param_type = param.get('type', 'Any')
        cangjie_type = get_parameter_type(method_info, param, type_map)
        result.append(f"{param_name}: {cangjie_type}")
    return result


def get_method_return_type(method_info, type_map, is_constructor=False):
    """Extract Cangjie return type string from method info.

    Returns the type string (e.g. 'String', 'Unit'), or '' for constructors.
    """
    if is_constructor:
        return ''
    return_types = method_info.get('return_types', [])
    if not return_types:
        return 'Unit'
    rt = return_types[0]
    if rt.startswith('<') and rt.endswith('>') and len(return_types) > 1:
        rt = return_types[1]
    return get_materialized_type(
        method_info, 'return_types', rt, rt, type_map
    )


def _parse_type_param_names(type_param_text):
    """Extract bare type parameter names from a Java ``<T, U extends X>`` block."""
    if not type_param_text:
        return []
    text = type_param_text.strip()
    if text.startswith('<') and text.endswith('>'):
        text = text[1:-1]
    result = []
    for part in split_generic_args(text):
        name = re.split(r'\s+(?:extends|super)\s+|\s+', part.strip(), maxsplit=1)[0]
        if name and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name):
            result.append(name)
    return result


def get_method_type_params(method_info):
    """Return only finalized method-level type parameter targets."""
    result = []
    for index, declaration in enumerate(method_info.get('type_parameters', [])):
        result.append(get_materialized_type(
            method_info,
            'type_parameters',
            f'{index}|{declaration}',
            declaration,
            {},
        ))
    return result


def get_class_type_params(class_info, type_map):
    """Return only finalized class-level type parameter targets."""
    result = []
    for index, declaration in enumerate(class_info.get('type_parameters', [])):
        result.append(get_materialized_type(
            class_info,
            'type_parameters',
            f'{index}|{declaration}',
            declaration,
            type_map,
        ))
    return result


def split_finalized_type_parameters(targets):
    """Split finalized declarations like ``T where T <: Base`` for rendering."""
    names = []
    constraints = []
    for target in targets:
        text = str(target).strip()
        if ' where ' in text:
            name, constraint = text.split(' where ', 1)
            names.append(name.strip())
            if constraint.strip():
                constraints.append(constraint.strip())
        else:
            names.append(text)
    return names, constraints


def generate_field_skeleton(field_info, field_key, type_map):
    """
    Generate skeleton for a single field.

    Returns:
        tuple: (skeleton_string, partial_translation_list)
    """
    field_name = _field_name_from_key(field_key)
    modifiers = field_info.get('modifiers', [])

    types = field_info.get('types', [])
    if types:
        source_type = types[0]
        field_type = get_materialized_type(
            field_info, 'types', source_type, source_type, type_map
        )
    else:
        field_type = 'Any'

    field_prefix = get_field_modifiers(modifiers)

    skeleton = f"    {field_prefix}{field_name}: {field_type} = throw Exception('TODO')\n"

    # partial_translation for fields should match skeleton content
    partial_translation = [f"    {field_prefix}{field_name}: {field_type} = throw Exception('TODO')\n"]

    return skeleton, partial_translation


def generate_method_skeleton(method_info, method_key, type_map,
                              is_override=False, needs_super_call=False,
                              custom_method_name=None, is_interface=False,
                              needs_open=False):
    """
    Generate skeleton for a single method.

    Parameters:
        custom_method_name: If provided, use instead of parsing from method_key
                            (handles field-method name conflict rename).

    Returns:
        tuple: (skeleton_string, partial_translation_list)
    """
    if custom_method_name:
        method_name = custom_method_name
    else:
        method_name = method_key.split(':')[1].strip()
        if '(' in method_name:
            method_name = method_name.split('(')[0].strip()

    if not method_name:
        return "", []

    modifiers = method_info.get('modifiers', [])
    is_constructor = method_info.get('is_constructor', False)

    param_strings = get_method_params(method_info, type_map)
    return_type = get_method_return_type(method_info, type_map, is_constructor)
    type_params, type_constraints = split_finalized_type_parameters(
        get_method_type_params(method_info)
    )

    mod_prefix = get_method_modifiers(
        modifiers,
        is_override=is_override,
        is_interface=is_interface,
        is_constructor=is_constructor,
        needs_open=needs_open,
    )
    params_str = ', '.join(param_strings)
    if is_constructor:
        method_sig = f"    {mod_prefix}init({params_str})"
    else:
        generic_suffix = f"<{', '.join(type_params)}>" if type_params else ""
        method_sig = f"    {mod_prefix}func {method_name}{generic_suffix}({params_str})"
        if return_type:
            method_sig += f": {return_type}"
        if type_constraints:
            method_sig += f" where {', '.join(type_constraints)}"

    body_lines = []
    if is_constructor and needs_super_call:
        body_lines.append("        super()")
    body_lines.append("        throw Exception('TODO')")
    body_str = "\n".join(body_lines)

    skeleton = f"{method_sig} {{\n{body_str}\n    }}\n\n"

    partial_translation = [f"{method_sig} {{", body_str, "    }\n"]

    return skeleton, partial_translation


def generate_static_initializer_skeleton(static_init_info, static_init_key):
    """
    Generate skeleton for a static initializer.

    Returns:
        tuple: (skeleton_string, partial_translation_list)
    """
    skeleton = "    static init() {\n        throw Exception('TODO')\n    }\n\n"

    partial_translation = [
        "    static init() {",
        "        throw Exception('TODO')",
        "    }\n"
    ]

    return skeleton, partial_translation


def generate_class_skeleton(class_info, class_name, type_map, schema_fname,
                             class_to_package, all_schema_classes,
                             was_nested=False):
    """
    Generate class declaration + fields + static initializers + methods.
    Modifies class_info in-place with partial_translations.
    Returns (skeleton_string, has_main_from_class).
    """
    is_abstract_class = class_info.get('is_abstract', False)
    java_modifiers = class_info.get('modifiers', [])
    class_mod = get_class_modifiers(java_modifiers, is_abstract_class, was_nested)

    extends = class_info.get('extends', [])
    implements = class_info.get('implements', [])

    # Build class declaration
    parent_name, impl_str = _get_class_parent(
        class_name, class_info, class_to_package, type_map
    )
    class_type_params, type_constraints = split_finalized_type_parameters(
        get_class_type_params(class_info, type_map)
    )
    declared_name = class_name + (
        f"<{', '.join(class_type_params)}>" if class_type_params else ''
    )
    supertypes = ' & '.join(item for item in (parent_name, impl_str) if item)
    if supertypes:
        declaration = f"{class_mod}class {declared_name} <: {supertypes}"
    else:
        declaration = f"{class_mod}class {declared_name}"
    if type_constraints:
        declaration += f" where {', '.join(type_constraints)}"
    declaration += " {\n"

    skeleton = declaration
    class_info['cangjie_class_declaration'] = declaration

    # Add test annotation if needed
    if 'src.test' in schema_fname and _is_test_class(class_info):
        skeleton = "@Test\n" + skeleton

    # Fields
    skeleton += "    // Fields Begin\n"
    for field_key in sorted(class_info.get('fields', {})):
        if _is_framework_ignored_field(field_key, class_info['fields'][field_key]):
            class_info['fields'][field_key]['skipped'] = True
            class_info['fields'][field_key]['partial_translation'] = []
            continue
        field_info = class_info['fields'][field_key]
        field_skeleton, field_partial = generate_field_skeleton(field_info, field_key, type_map)
        skeleton += field_skeleton
        field_info['partial_translation'] = field_partial
    skeleton += "    // Fields End\n\n"

    # Static initializers
    if class_info.get('static_initializers'):
        skeleton += "    // Static Initializer Begin\n"
        for static_init_key, static_init_info in class_info.get('static_initializers', {}).items():
            static_init_skeleton, static_init_partial = generate_static_initializer_skeleton(
                static_init_info, static_init_key
            )
            skeleton += static_init_skeleton
            static_init_info['partial_translation'] = static_init_partial
        skeleton += "    // Static Initializer End\n\n"

    # Methods
    skeleton += "    // Methods Begin\n"

    # Check if child constructors need explicit super() call
    needs_super_call = _check_needs_super_call(extends, all_schema_classes)

    # Field names for conflict detection
    field_names = set()
    for field_key in class_info.get('fields', {}):
        fn = field_key.split(':')[1].strip()
        if fn:
            field_names.add(fn)

    used_sigs = set()
    has_main_from_class = False

    for method_key in class_info.get('methods', {}):
        method_info = class_info['methods'][method_key]
        method_name = method_key.split(':')[1].strip()
        if '(' in method_name:
            method_name = method_name.split('(')[0].strip()
        if not method_name:
            continue

        # # Main method detection (handled at file level in Cangjie)
        # if method_name == 'main':
        #     has_main_from_class = True
        #     continue

        # Skip main method
        if method_name == 'main':
            continue

        # Rename method if it conflicts with a field name
        custom_method_name = method_name
        if method_name in field_names:
            custom_method_name = method_name + '_method'
            method_info['renamed_from'] = method_name

        # Signature conflict detection
        is_constructor = method_info.get('is_constructor', False)
        cangjie_method_name = 'init' if is_constructor else custom_method_name
        cangjie_param_types = tuple(
            get_parameter_type(method_info, p, type_map)
            for p in method_info.get('parameters', [])
        )
        sig_key = (cangjie_method_name, cangjie_param_types)

        if sig_key in used_sigs:
            if is_constructor:
                method_skeleton = f"    // TODO: constructor with same signature 'init({', '.join(cangjie_param_types)})' needs manual resolution\n"
                skeleton += method_skeleton
                method_info['partial_translation'] = [method_skeleton]
                method_info['skipped'] = True
                continue
            else:
                suffix = 1
                while (f"{custom_method_name}_{suffix}", cangjie_param_types) in used_sigs:
                    suffix += 1
                custom_method_name = f"{custom_method_name}_{suffix}"
        used_sigs.add(sig_key)

        method_skeleton, method_partial = generate_method_skeleton(
            method_info, method_key, type_map,
            is_override=method_info.get('is_override', False),
            needs_super_call=needs_super_call,
            custom_method_name=custom_method_name,
            needs_open=method_info.get('needs_open', False),
        )
        skeleton += method_skeleton
        method_info['partial_translation'] = method_partial

    skeleton += "    // Methods End\n"

    # Add synthetic no-arg constructor if class has param constructors but no no-arg.
    # This gives subclasses a super() target to call in their constructors.
    if _needs_synthetic_no_arg_constructor(class_info):
        skeleton += "\n    protected init() {\n        throw Exception('TODO')\n    }\n"

    skeleton += "}\n\n"

    return skeleton, has_main_from_class


def generate_interface_skeleton(class_info, class_name, type_map, schema_fname, class_to_package):
    """
    Generate interface declaration + methods.
    Modifies class_info in-place with partial_translations.
    Returns skeleton_string.
    """
    java_modifiers = class_info.get('modifiers', [])
    interface_mod = get_interface_modifiers(java_modifiers)

    parent_names = _get_interface_parents(class_name, class_info, class_to_package, type_map)
    class_type_params, type_constraints = split_finalized_type_parameters(
        get_class_type_params(class_info, type_map)
    )
    declared_name = class_name + (
        f"<{', '.join(class_type_params)}>" if class_type_params else ''
    )
    if parent_names:
        declaration = f"{interface_mod}interface {declared_name} <: {' & '.join(parent_names)}"
    else:
        declaration = f"{interface_mod}interface {declared_name}"
    if type_constraints:
        declaration += f" where {', '.join(type_constraints)}"
    declaration += " {\n"

    skeleton = declaration
    class_info['cangjie_class_declaration'] = declaration

    # Add test annotation if needed
    if 'src.test' in schema_fname and _is_test_class(class_info):
        skeleton = "@Test\n" + skeleton

    # Methods (interfaces don't have fields/static initializers)
    skeleton += "    // Methods Begin\n"

    used_sigs = set()
    for method_key in class_info.get('methods', {}):
        method_info = class_info['methods'][method_key]
        method_name = method_key.split(':')[1].strip()
        if '(' in method_name:
            method_name = method_name.split('(')[0].strip()
        if not method_name:
            continue

        # Signature conflict detection
        is_constructor = method_info.get('is_constructor', False)
        cangjie_method_name = 'init' if is_constructor else method_name
        cangjie_param_types = tuple(
            get_parameter_type(method_info, p, type_map)
            for p in method_info.get('parameters', [])
        )
        sig_key = (cangjie_method_name, cangjie_param_types)

        if sig_key in used_sigs:
            if is_constructor:
                method_skeleton = f"    // TODO: constructor with same signature 'init({', '.join(cangjie_param_types)})' needs manual resolution\n"
                skeleton += method_skeleton
                method_info['partial_translation'] = [method_skeleton]
                method_info['skipped'] = True
                continue
            else:
                suffix = 1
                while (f"{method_name}_{suffix}", cangjie_param_types) in used_sigs:
                    suffix += 1
                method_name = f"{method_name}_{suffix}"
        used_sigs.add(sig_key)

        method_skeleton, method_partial = generate_method_skeleton(
            method_info, method_key, type_map,
            is_override=method_info.get('is_override', False),
            needs_super_call=False,
            is_interface=True
        )
        skeleton += method_skeleton
        method_info['partial_translation'] = method_partial

    skeleton += "    // Methods End\n"
    skeleton += "}\n\n"

    return skeleton


def generate_package_header(cjpm_name, sub_path):
    """Generate Cangjie package header string."""
    if sub_path:
        package_name = f"{cjpm_name}.{sub_path.replace('/', '.')}"
    else:
        package_name = cjpm_name
    return f"// Package: {package_name}\npackage {package_name}\n\n"


def is_interface(schema_classes, class_key):
    """Check if a class is an interface."""
    if class_key not in schema_classes:
        return False
    return schema_classes[class_key].get('is_interface', False)


def class_needs_open(java_modifiers, is_abstract):
    """A Cangjie class needs 'open' if inheritable (non-final, non-abstract)."""
    if is_abstract:
        return False
    return 'final' not in java_modifiers


def method_needs_open(java_modifiers):
    """A Cangjie method needs 'open' if overridable (non-static, non-final, non-private)."""
    if 'static' in java_modifiers:
        return False
    if 'final' in java_modifiers:
        return False
    if 'private' in java_modifiers:
        return False
    return True


def _is_test_class(class_info):
    """Check if any method in the class has @Test annotation."""
    return any(
        '@Test' in [x.split('(')[0] for x in class_info['methods'][m].get('annotations', [])]
        for m in class_info.get('methods', {})
    )


def _check_needs_super_call(extends, all_schema_classes):
    """Check if child constructors need explicit super() call.

    Returns True when the parent class has constructors but no no-arg constructor,
    meaning child constructors must call super() explicitly.
    """
    if not extends:
        return False
    parent_short = extends[0].split('.')[-1]
    if parent_short not in all_schema_classes:
        return False
    parent_constructors = [
        pm for pm_key, pm in all_schema_classes[parent_short].get('methods', {}).items()
        if pm.get('is_constructor', False)
    ]
    if not parent_constructors:
        return False
    return not any(len(pm.get('parameters', [])) == 0 for pm in parent_constructors)


def _needs_synthetic_no_arg_constructor(class_info):
    """Check if class needs a synthetic protected no-arg constructor.

    Cangjie requires subclasses to call super() explicitly if the parent
    has parameter constructors but no no-arg constructor. This function
    detects whether the current class needs such a synthetic constructor.
    """
    has_constructor = False
    has_no_arg = False
    for mk, mv in class_info.get('methods', {}).items():
        if mv.get('is_constructor', False):
            has_constructor = True
            if len(mv.get('parameters', [])) == 0:
                has_no_arg = True
                break
    return has_constructor and not has_no_arg


# ============================================================
# Path & Package
# ============================================================


def _parse_java_path(java_path):
    """
    Extract the Java package sub-path from a full source path.

    For a path like ``.../src/main/java/org/apache/Foo.java``,
    returns ``org/apache``.  Returns ``None`` when no standard
    Java source root (``src/main/java/`` or ``src/test/java/``)
    is found.
    """
    for marker in ('src/main/java/', 'src/test/java/'):
        if marker in java_path:
            after = java_path.split(marker, 1)[1]
            parts = after.split('/')
            return '/'.join(parts[:-1]) if len(parts) > 1 else None
    return None


# ============================================================
# Import Helpers
# ============================================================


# Java library type to Cangjie import mappings.
#
# The mapping is loaded from data/java/type_resolution/java_base_type_imports.json.
# It is keyed by Java source type names rather than Cangjie target type names,
# which lets skeleton generation use the schema import_map to resolve short
# Java names before adding Cangjie imports.


def _normalize_import_list(value):
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item.strip()]
    return []


def _load_java_type_imports(path):
    """Load Java type -> Cangjie imports and add unambiguous simple-name aliases."""
    if not os.path.exists(path):
        return {}

    with open(path, 'r') as f:
        raw_imports = json.load(f)

    java_type_imports = {}
    simple_aliases = {}
    for java_type, imports_value in raw_imports.items():
        imports = tuple(_normalize_import_list(imports_value))
        if not imports:
            continue
        java_type_imports[java_type] = list(imports)
        if '.' in java_type:
            simple_name = java_type.split('.')[-1]
            simple_aliases.setdefault(simple_name, set()).add(imports)

    for simple_name, imports_set in simple_aliases.items():
        if len(imports_set) == 1 and simple_name not in java_type_imports:
            java_type_imports[simple_name] = list(next(iter(imports_set)))

    return java_type_imports


def _strip_java_type_token(java_type):
    text = str(java_type or '').strip()
    for prefix in ('? extends ', '? super '):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    if text == '?':
        return ''
    while text.endswith('[]'):
        text = text[:-2].strip()
    return text


def _iter_java_type_names(java_type_expr):
    """Yield base Java type names from a Java type expression."""
    java_type_expr = _strip_java_type_token(java_type_expr)
    if not java_type_expr:
        return

    if '<' in java_type_expr and java_type_expr.endswith('>'):
        base_type = java_type_expr[: java_type_expr.index('<')].strip()
        if base_type:
            yield base_type
        generic_part = java_type_expr[java_type_expr.index('<') + 1 : java_type_expr.rindex('>')]
        for arg in split_generic_args(generic_part):
            yield from _iter_java_type_names(arg)
        return

    yield java_type_expr


def _java_import_lookup_keys(java_type, import_map):
    java_type = _strip_java_type_token(java_type)
    if not java_type:
        return []

    keys = []
    if java_type in import_map:
        keys.append(import_map[java_type])
    keys.append(java_type)

    simple_name = java_type.split('.')[-1]
    if simple_name in import_map:
        keys.append(import_map[simple_name])
    keys.append(simple_name)

    result = []
    seen = set()
    for key in keys:
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result


def generate_imports_skeleton(schema, class_order, schema_fname, java_path,
                               cjpm_name, type_map, class_to_package,
                               dependencies, custom_types, processed_classes,
                               java_type_imports, skeleton='',
                               collapsed_subpaths=None):
    """Build the complete import section for a skeleton file.

    Returns the import string to replace __IMPORTS_PLACEHOLDER__.
    """
    cangjie_imports = set()

    _add_project_imports(cangjie_imports, dependencies, schema_fname,
                         processed_classes, schema, class_order,
                         java_path, cjpm_name, class_to_package,
                         collapsed_subpaths)

    _add_lib_imports(cangjie_imports, schema, class_order, type_map, java_type_imports, cjpm_name)

    # Filter out custom types (they're in the same project, no import needed)
    filtered_imports = set()
    for imp in cangjie_imports:
        if imp.startswith('import ') and not imp.startswith(('import std.', 'import ohos.')):
            imported_name = imp[len('import '):].strip()
            if '.' not in imported_name and imported_name in custom_types:
                continue
        filtered_imports.add(imp)

    if filtered_imports:
        return '\n'.join(sorted(filtered_imports)) + '\n'
    return '\n'


def _add_project_imports(cangjie_imports, dependencies, schema_fname,
                         processed_classes, schema, class_order,
                         java_path, cjpm_name, class_to_package,
                         collapsed_subpaths=None):
    """Add imports for project types (dependencies + cross-package extends/implements)."""
    cur_pkg = _get_cangjie_package(java_path, cjpm_name, collapsed_subpaths)

    # Process dependencies for imports
    dependency_key = None
    for key in dependencies:
        if f'{key}.json' in schema_fname:
            dependency_key = key
            break

    if dependency_key and dependency_key in dependencies:
        for dependent_class in dependencies[dependency_key]:
            dep_class_name = dependent_class[0]
            if dep_class_name not in class_to_package:
                continue
            dep_pkg = class_to_package[dep_class_name]
            # Same package — types are auto-visible, no import needed
            if dep_pkg == cur_pkg:
                continue
            cangjie_imports.add(f"import {dep_pkg}.{dep_class_name}")

    # Cross-package imports for extends/implements
    for class_key in class_order:
        if class_key not in schema.get('classes', {}):
            continue
        class_info = schema['classes'][class_key]
        for ref_type in class_info.get('extends', []) + class_info.get('implements', []):
            ref_name = ref_type.split('.')[-1]
            if ref_name not in class_to_package:
                continue
            ref_pkg = class_to_package[ref_name]
            if ref_pkg == cur_pkg:
                continue
            cangjie_imports.add(f"import {ref_pkg}.{ref_name}")


def _add_lib_imports(cangjie_imports, schema, class_order, type_map, java_type_imports, cjpm_name):
    """Add only imports carried by finalized occurrence targets."""
    from src.java.type_resolution.schema import iter_materialized_imports

    uses_any_hashable = False

    for class_key in class_order:
        if class_key not in schema.get('classes', {}):
            continue
        class_info = schema['classes'][class_key]
        fragments = [class_info]
        fragments.extend(class_info.get('fields', {}).values())
        fragments.extend(class_info.get('methods', {}).values())
        for frag_data in fragments:
            cangjie_imports.update(iter_materialized_imports(frag_data))
            for slots in frag_data.get('type_translations', {}).values():
                if not isinstance(slots, dict):
                    continue
                for slot in slots.values():
                    if isinstance(slot, dict) and slot.get('translated'):
                        value = str(slot.get('translated_target_type', ''))
                        uses_any_hashable = uses_any_hashable or 'AnyHashable' in value

    if uses_any_hashable:
        cangjie_imports.add(runtime_support.any_hashable_import(cjpm_name))


def _add_java_type_imports(java_type_expr, cangjie_imports, java_type_imports, import_map):
    """Add Cangjie imports for Java source type names."""
    for java_type in _iter_java_type_names(java_type_expr):
        for key in _java_import_lookup_keys(java_type, import_map):
            for imp in java_type_imports.get(key, []):
                cangjie_imports.add(imp)


# ============================================================
# Per-File Orchestrator
# ============================================================


def generate_one_file_skeleton(schema, schema_fname, schema_path, cjpm_name, type_map,
                                class_to_package, all_schema_classes, class_to_methods,
                                dependencies, custom_types, skeletons_dir,
                                translations_skeleton_dir, java_type_imports,
                                collapsed_subpaths=None, third_party_libraries=None):
    """
    Generate Cangjie skeleton for one schema file.

    Handles package header, imports, class/interface skeletons,
    main method extraction, import resolution, and file output.

    Returns True if any main method was found in this file.
    """
    # Package header
    java_path = schema.get('path', '')
    sub_path = _get_effective_skeleton_sub_path(java_path, collapsed_subpaths)
    skeleton = generate_package_header(cjpm_name, sub_path)

    # Imports placeholder
    skeleton += "// Imports Begin\n__IMPORTS_PLACEHOLDER__\n// Imports End\n\n"

    # Class order
    class_order = get_class_order(schema)
    processed_classes = set()

    has_main_from_file = False

    # Process each class in dependency order
    for class_key in class_order:
        if class_key not in schema.get('classes', {}):
            continue

        class_info = schema['classes'][class_key]
        class_name = class_key.split(':')[1].strip()

        # Handle nested class names
        if '<' in class_name:
            class_name = class_name.split('<')[0].replace("new ", "").strip()
        if '(' in class_name:
            class_name = class_name.split('(')[0].replace("new ", "").strip()

        if class_name in processed_classes:
            continue
        processed_classes.add(class_name)

        is_interface_class = class_info.get('is_interface', False)

        if is_interface_class:
            class_skeleton = generate_interface_skeleton(
                class_info, class_name, type_map, schema_fname, class_to_package
            )
            skeleton += class_skeleton
        else:
            class_skeleton, has_main_from_class = generate_class_skeleton(
                class_info, class_name, type_map, schema_fname,
                class_to_package, all_schema_classes,
                was_nested=bool(class_info.get('nested_inside'))
            )
            skeleton += class_skeleton
            # if has_main_from_class:
            #     has_main_from_file = True

        # Store cangjie_class_declaration in schema for PromptGenerator
        schema['classes'][class_key]['cangjie_class_declaration'] = class_info.get('cangjie_class_declaration', '')

    imports_str = generate_imports_skeleton(
        schema, class_order, schema_fname, java_path,
        cjpm_name, type_map, class_to_package,
        dependencies, custom_types, processed_classes,
        java_type_imports, skeleton, collapsed_subpaths
    )
    skeleton = skeleton.replace('__IMPORTS_PLACEHOLDER__\n', imports_str)

    # Write skeleton file
    is_test = 'src/test' in java_path
    class_name = java_path.split('/')[-1].replace('.java', '')
    if is_test and not class_name.endswith('_test'):
        class_name = class_name + '_test'

    # Detect collapsed subpath for filename prefix to avoid collisions
    original_sub_path = _compute_skeleton_sub_path(java_path)
    if original_sub_path and collapsed_subpaths and original_sub_path in collapsed_subpaths:
        collapse_prefix = original_sub_path.replace('/', '_') + '_'
    else:
        collapse_prefix = ''

    src_dir = f"{skeletons_dir}/src"
    if sub_path:
        os.makedirs(f"{src_dir}/{sub_path}", exist_ok=True)
        file_path = f"{src_dir}/{sub_path}/{class_name}.cj"
    else:
        os.makedirs(src_dir, exist_ok=True)
        file_path = f"{src_dir}/{collapse_prefix}{class_name}.cj"

    # # Append main at package level if any class had one
    # if has_main_from_file:
    #     skeleton += "main(): Unit {\n"
    #     skeleton += "    throw Exception('TODO')\n"
    #     skeleton += "}\n"

    with open(file_path, 'w') as f:
        f.write(skeleton)

    print(f"Generated: {file_path}")

    # Translations skeleton
    relative_path = os.path.relpath(file_path, skeletons_dir)
    translations_file_path = os.path.join(translations_skeleton_dir, relative_path)
    os.makedirs(os.path.dirname(translations_file_path), exist_ok=True)

    with open(translations_file_path, 'w') as f:
        f.write(skeleton)

    print(f"Generated translations: {translations_file_path}")

    # Update schema with partial translation
    target_schema = schema.copy()
    target_schema['cangjie_skeleton_path'] = file_path
    target_schema['cangjie_translations_skeleton_path'] = translations_file_path
    with open(schema_path, 'w') as f:
        json.dump(target_schema, f, indent=4)

    return (
        'AnyHashable' in skeleton,
        _uses_stdx_imports(imports_str),
        _detect_third_party_dependencies(imports_str, third_party_libraries or {}),
    )


# ============================================================
# Main Pipeline
# ============================================================


def main(args):
    include_tests = _should_include_test_sources(args)

    build_default_type_map, _, merge_shim_type_map, render_shim_file = (
        _load_type_resolution_backend()
    )

    # Occurrence-specific records are read from schema type_translations.
    type_map = build_default_type_map()
    merge_shim_type_map(type_map, args.project)

    # Phase 1: Build Global Context

    # Schema directory
    schema_dir = f"data/java/schemas{args.suffix}/{args.model}/{args.temperature}/{args.project}"

    if not os.path.exists(schema_dir):
        print(f"Error: Schema directory not found: {schema_dir}")
        return

    # Dependencies and custom types
    args.schemas_dir = schema_dir
    dependencies = get_dependencies(args)
    schema_filter = lambda schema_fname: include_tests or not _is_test_schema_name(schema_fname)
    custom_types = get_custom_types(schema_dir, schema_filter=schema_filter)
    type_map.update(get_custom_type_translation_map(schema_dir, schema_filter=schema_filter))
    additional_custom_types = ['Exception', 'Error', 'RuntimeException']
    custom_types = list(set(custom_types + additional_custom_types))

    # Output directories
    skeletons_dir = f"data/java/skeletons/{args.project}"
    os.makedirs(skeletons_dir, exist_ok=True)
    translations_skeleton_dir = f"data/java/skeletons/translations/{args.model}/{args.temperature}/{args.project}"
    os.makedirs(translations_skeleton_dir, exist_ok=True)
    _clean_generated_skeleton_sources(skeletons_dir, translations_skeleton_dir)
    if not include_tests:
        _remove_generated_test_skeletons(skeletons_dir, translations_skeleton_dir)

    # Cangjie package name
    cjpm_name = args.project.replace('-', '_')

    # Build cross-schema mappings and load all schemas
    class_to_methods = {}
    all_schema_classes = {}
    class_to_package = {}
    all_schemas = []

    # Load schemas first. Package layout is decided after all class references
    # are known, because Cangjie package cycles require collapsing some Java
    # subpackages back into the project root package.
    for schema_fname in os.listdir(schema_dir):
        if not schema_fname.endswith('.json'):
            continue
        if f'{args.project}.src.main' not in schema_fname and f'{args.project}.src.test' not in schema_fname:
            continue
        if _is_test_schema_name(schema_fname) and not include_tests:
            continue
        schema_path = f"{schema_dir}/{schema_fname}"
        with open(schema_path, 'r') as f:
            schema = json.load(f)
        all_schemas.append((schema_fname, schema_path, schema))

    effective_subpaths = _compute_schema_effective_subpath_map(
        all_schemas, type_map, dependencies, None)
    changed_subpaths = {
        raw: effective for raw, effective in effective_subpaths.items()
        if raw is not None and raw != effective
    }
    if changed_subpaths:
        collapsed_text = ', '.join(
            f"{raw}->{effective or '<root>'}"
            for raw, effective in sorted(changed_subpaths.items())
        )
        print(f"Collapsing cyclic Java subpackages: {collapsed_text}")
        _remove_collapsed_output_dirs(skeletons_dir, effective_subpaths)
        _remove_collapsed_output_dirs(translations_skeleton_dir, effective_subpaths)

    for schema_fname, schema_path, schema in all_schemas:
        cangjie_pkg = _get_cangjie_package(schema.get('path', ''), cjpm_name,
                                           effective_subpaths)
        for class_key, class_info in schema.get('classes', {}).items():
            class_name = class_key.split(':')[-1]
            extends = class_info.get('extends', [])
            parent = extends[0].split('.')[-1] if extends else None
            methods = list(class_info.get('methods', {}).keys())
            method_names = [m.split(':')[1].strip() if ':' in m else m for m in methods]
            class_to_methods[class_name] = {'parent': parent, 'methods': method_names}
            all_schema_classes[class_name] = {'extends': extends, 'methods': class_info.get('methods', {})}
            class_to_package[class_name] = cangjie_pkg

    # Load Java base type imports.
    java_type_imports = _load_java_type_imports(
        "data/java/type_resolution/java_base_type_imports.json"
    )
    third_party_libraries = _load_third_party_libraries()

    # Phase 1b: Run annotate_method_flags on all schemas to populate needs_open flags
    for schema_fname, schema_path, schema in all_schemas:
        if 'package-info' in schema_fname or 'module-info' in schema_fname:
            continue
        annotate_method_flags(schema, class_to_methods, all_schema_classes)

    # Phase 2: Generate Skeletons (using Phase 1 schema data — no reload from disk)
    uses_any_hashable = False
    uses_stdx = False
    used_third_party_libs = set()
    for schema_fname, schema_path, schema in all_schemas:
        if 'package-info' in schema_fname or 'module-info' in schema_fname:
            continue

        file_uses_any_hashable, file_uses_stdx, file_third_party_libs = generate_one_file_skeleton(
            schema, schema_fname, schema_path, cjpm_name, type_map,
            class_to_package, all_schema_classes, class_to_methods,
            dependencies, custom_types, skeletons_dir, translations_skeleton_dir,
            java_type_imports, effective_subpaths, third_party_libraries
        )
        uses_any_hashable = file_uses_any_hashable or uses_any_hashable
        uses_stdx = file_uses_stdx or uses_stdx
        used_third_party_libs.update(file_third_party_libs)

    # Phase 3: Generate cjpm.toml
    output_type = "static"

    cjpm_content = _generate_cjpm_content(
        cjpm_name, output_type, uses_stdx,
        third_party_libraries, used_third_party_libs
    )
    with open(f"{skeletons_dir}/cjpm.toml", 'w') as f:
        f.write(cjpm_content)

    translations_cjpm_path = f"{translations_skeleton_dir}/cjpm.toml"
    with open(translations_cjpm_path, 'w') as f:
        f.write(cjpm_content)

    if uses_any_hashable:
        runtime_support.inject_any_hashable(Path(skeletons_dir) / "src", cjpm_name)
        runtime_support.inject_any_hashable(Path(translations_skeleton_dir) / "src", cjpm_name)

    if render_shim_file(args.project, cjpm_name, [skeletons_dir, translations_skeleton_dir]):
        print(f"Generated compat interface shims for {args.project}")

    print(f"\nSkeleton generation complete: {skeletons_dir}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create Cangjie skeleton from Java schema')
    parser.add_argument('--project', type=str, dest='project', help='name of the project')
    parser.add_argument('--model', type=str, dest='model', help='name of the model')
    parser.add_argument('--suffix', type=str, dest='suffix', help='suffix (e.g., _decomposed_tests)')
    parser.add_argument('--temperature', type=float, dest='temperature', help='temperature')
    parser.add_argument(
        '--translate_tests',
        type=str,
        default='false',
        help='Include src/test Java classes in skeleton generation (true/false)',
    )
    args = parser.parse_args()

    main(args)
