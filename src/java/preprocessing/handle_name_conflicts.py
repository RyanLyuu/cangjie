#!/usr/bin/env python3
"""
Handle Java naming conflicts for Cangjie translation.

Renames inner classes to OuterClass_InnerClass format to avoid conflicts
when they are later extracted to top-level in Cangjie (which has no inner classes).

Also detects and resolves naming conflicts (same inner class name from
different outer classes).

Input:  projects/java/keyword_handled/<project>/
Output: projects/java/name_handled/<project>/
"""
import argparse
import os
import re
import shutil

from src.java.preprocessing._shared import (
    load_parser, extract_text_by_bytes, _skip_dir, clean_target_dirs
)
from src.java.utils.package_collapse import (
    add_package_edge, compute_effective_subpath_map, compute_skeleton_sub_path
)


TOP_LEVEL_TYPES = (
    'class_declaration', 'interface_declaration',
    'enum_declaration', 'record_declaration'
)


def _find_inner_classes(code, tree):
    """Find inner class declarations. Returns list of dicts with name and outer_class_name."""
    inner_classes = []

    def _find(node, outer_name=None, depth=0):
        if node.type in ('class_declaration', 'interface_declaration'):
            name_node = node.child_by_field_name('name')
            if name_node is None:
                for child in node.children:
                    _find(child, outer_name, depth)
                return

            class_name = extract_text_by_bytes(code, name_node.start_byte, name_node.end_byte)

            if depth > 0 and outer_name is not None:
                inner_classes.append({
                    'name': class_name,
                    'outer_class_name': outer_name,
                })

            body = node.child_by_field_name('body')
            if body:
                _find(body, class_name, depth + 1)
            else:
                for child in node.children:
                    _find(child, class_name if depth == 0 else outer_name, depth + 1)
        else:
            for child in node.children:
                _find(child, outer_name, depth)

    _find(tree.root_node, None, 0)
    return inner_classes


def _resolve_names(all_inner_classes, all_top_level_names):
    """Resolve unique names. Returns dict of (file_path, outer, inner) -> new_name."""
    name_map = {}
    used_names = set(all_top_level_names)

    for file_path, ic_list in all_inner_classes.items():
        for ic in ic_list:
            default = f"{ic['outer_class_name']}_{ic['name']}"
            if default not in used_names:
                name_map[(file_path, ic['outer_class_name'], ic['name'])] = default
                used_names.add(default)
            else:
                suffix = 2
                while f"{default}_{suffix}" in used_names:
                    suffix += 1
                resolved = f"{default}_{suffix}"
                name_map[(file_path, ic['outer_class_name'], ic['name'])] = resolved
                used_names.add(resolved)
                print(f"  CONFLICT: {default} → {resolved}")
    return name_map


def _iter_java_files(project_dir):
    for root, dirs, files in os.walk(project_dir):
        if _skip_dir(root):
            continue
        for fname in sorted(files):
            if fname.endswith('.java'):
                yield os.path.join(root, fname)


def _read_bytes(file_path):
    with open(file_path, 'rb') as f:
        return f.read()


def _extract_package_name(code_text):
    match = re.search(r'^\s*package\s+([A-Za-z_][\w.]*)\s*;',
                      code_text, re.MULTILINE)
    return match.group(1) if match else ''


def _extract_imports(code_text):
    imports = {}
    for match in re.finditer(
            r'^\s*import\s+(?:static\s+)?([A-Za-z_][\w.]*)(?:\.\*)?\s*;',
            code_text, re.MULTILINE):
        fqcn = match.group(1)
        imports[fqcn.rsplit('.', 1)[-1]] = fqcn
    return imports


def _dir_has_java_files(dir_path):
    if not os.path.isdir(dir_path):
        return False
    return any(name.endswith('.java') for name in os.listdir(dir_path))


def _full_source_subpath(java_path):
    """
    Return the complete Java source subpackage path relative to the root
    directory that first contains Java files.
    """
    normalized = java_path.replace(os.sep, '/')
    marker = None
    for candidate in ('src/main/java/', 'src/test/java/'):
        if candidate in normalized:
            marker = candidate
            break
    if marker is None:
        return None

    src_root = normalized.split(marker, 1)[0] + marker.rstrip('/')
    parent_dir = os.path.dirname(normalized)
    if not parent_dir.startswith(src_root):
        return None

    rel_parent = parent_dir[len(src_root):].strip('/')
    parts = rel_parent.split('/') if rel_parent else []
    java_ancestors = []
    for i in range(len(parts)):
        candidate = os.path.join(src_root, *parts[:i + 1])
        if _dir_has_java_files(candidate):
            java_ancestors.append('/'.join(parts[:i + 1]))
    if not java_ancestors:
        return None
    root_source_dir = java_ancestors[0]
    if rel_parent == root_source_dir:
        return None
    return rel_parent[len(root_source_dir):].strip('/') or None


def _sanitize_subpath(subpath):
    return re.sub(r'[^0-9A-Za-z_]+', '_', subpath).strip('_')


def _collect_type_refs(node, code, refs):
    if node.type in ('type_identifier', 'scoped_type_identifier',
                     'scoped_identifier'):
        refs.add(extract_text_by_bytes(code, node.start_byte, node.end_byte))
    for child in node.children:
        _collect_type_refs(child, code, refs)


def _collect_top_level_classes(node, code, records, file_info, depth=0):
    if node.type in TOP_LEVEL_TYPES:
        name_node = node.child_by_field_name('name')
        if name_node and depth == 0:
            class_name = extract_text_by_bytes(code, name_node.start_byte,
                                               name_node.end_byte)
            package_name = file_info['package']
            fqcn = f"{package_name}.{class_name}" if package_name else class_name
            records.append({
                'file_path': file_info['file_path'],
                'name': class_name,
                'package': package_name,
                'fqcn': fqcn,
                'raw_subpath': file_info['raw_subpath'],
                'full_subpath': file_info['full_subpath'],
            })

        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                _collect_top_level_classes(child, code, records, file_info,
                                           depth + 1)
        return

    for child in node.children:
        _collect_top_level_classes(child, code, records, file_info, depth)


def _simple_java_type_name(text):
    text = (text or '').strip()
    for prefix in ('extends ', 'implements '):
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    text = text.split('<', 1)[0].split(',', 1)[0].strip()
    text = text.replace('[]', '').strip()
    return text.rsplit('.', 1)[-1].strip()


def _iter_class_declarations(node):
    if node.type in TOP_LEVEL_TYPES:
        yield node
        body = node.child_by_field_name('body')
        if body:
            for child in body.children:
                yield from _iter_class_declarations(child)
        return
    for child in node.children:
        yield from _iter_class_declarations(child)


def _direct_class_members(class_node):
    body = class_node.child_by_field_name('body')
    if body is None:
        return []
    return [
        child for child in body.children
        if child.type not in TOP_LEVEL_TYPES
    ]


def _collect_field_declarators_from_field(field_node, code):
    fields = []

    def _walk(node):
        if node.type == 'variable_declarator':
            name_node = node.child_by_field_name('name')
            if name_node is not None:
                fields.append({
                    'name': extract_text_by_bytes(
                        code, name_node.start_byte, name_node.end_byte),
                    'name_node': name_node,
                })
            return
        for child in node.children:
            _walk(child)

    _walk(field_node)
    return fields


def _collect_direct_fields(class_node, code):
    fields = []
    for child in _direct_class_members(class_node):
        if child.type == 'field_declaration':
            fields.extend(_collect_field_declarators_from_field(child, code))
    return fields


def _collect_direct_methods(class_node):
    return [
        child for child in _direct_class_members(class_node)
        if child.type in ('method_declaration', 'constructor_declaration')
    ]


def _class_parent_name(class_node, code):
    superclass = class_node.child_by_field_name('superclass')
    if superclass is None:
        return ''
    return _simple_java_type_name(
        extract_text_by_bytes(code, superclass.start_byte, superclass.end_byte)
    )


def _is_this_field_identifier(node, code):
    parent = node.parent
    if parent is None or parent.type != 'field_access':
        return False
    name_node = parent.child_by_field_name('field')
    object_node = parent.child_by_field_name('object')
    return (
        name_node == node
        and object_node is not None
        and extract_text_by_bytes(code, object_node.start_byte, object_node.end_byte) == 'this'
    )


def _is_field_access_field_identifier(node):
    parent = node.parent
    if parent is None or parent.type != 'field_access':
        return False
    return parent.child_by_field_name('field') == node


def _is_method_declaration_name(node):
    parent = node.parent
    return (
        parent is not None
        and parent.type in ('method_declaration', 'constructor_declaration')
        and parent.child_by_field_name('name') == node
    )


def _is_method_invocation_name(node):
    parent = node.parent
    return (
        parent is not None
        and parent.type == 'method_invocation'
        and parent.child_by_field_name('name') == node
    )


def _nearest_method_or_class(node):
    current = node.parent
    while current is not None:
        if current.type in (
            'method_declaration', 'constructor_declaration',
            'class_declaration', 'interface_declaration',
            'enum_declaration', 'record_declaration',
        ):
            return current
        current = current.parent
    return None


def _is_identifier_node(node):
    return node.type in ('identifier', 'type_identifier')


def _unique_shadow_name(base, used, suffix):
    candidate = f"{base}_{suffix}"
    index = 2
    while candidate in used:
        candidate = f"{base}_{suffix}{index}"
        index += 1
    used.add(candidate)
    return candidate


def _collect_method_parameter_renames(method_node, code, collision_names, used_names):
    renames = {}

    def _walk(node):
        if node.type == 'formal_parameter':
            name_node = node.child_by_field_name('name')
            if name_node is not None:
                name = extract_text_by_bytes(code, name_node.start_byte, name_node.end_byte)
                if name in collision_names and name not in renames:
                    renames[name] = _unique_shadow_name(name, used_names, 'param')
            return
        for child in node.children:
            _walk(child)

    _walk(method_node)
    return renames


def _collect_shadow_class_infos(output_dir, parser):
    class_infos = []
    for java_file in _iter_java_files(output_dir):
        code = _read_bytes(java_file)
        tree = parser.parse(code)
        for class_node in _iter_class_declarations(tree.root_node):
            name_node = class_node.child_by_field_name('name')
            if name_node is None:
                continue
            name = extract_text_by_bytes(code, name_node.start_byte, name_node.end_byte)
            fields = _collect_direct_fields(class_node, code)
            class_infos.append({
                'name': name,
                'file_path': java_file,
                'class_node': class_node,
                'parent': _class_parent_name(class_node, code),
                'fields': fields,
                'methods': _collect_direct_methods(class_node),
            })
    return class_infos


def _handle_inheritance_shadow_conflicts(output_dir, parser):
    print("Step 5/5: Resolving inherited member shadow conflicts...")
    class_infos = _collect_shadow_class_infos(output_dir, parser)
    by_name = {}
    for info in class_infos:
        by_name.setdefault(info['name'], info)

    direct_fields = {
        info['name']: {field['name'] for field in info['fields']}
        for info in class_infos
    }
    ancestor_cache = {}

    def ancestor_fields(class_name, seen=None):
        if class_name in ancestor_cache:
            return ancestor_cache[class_name]
        if seen is None:
            seen = set()
        if class_name in seen or class_name not in by_name:
            return set()
        seen.add(class_name)
        parent = by_name[class_name].get('parent')
        if not parent or parent not in by_name:
            result = set()
        else:
            result = set(direct_fields.get(parent, set()))
            result.update(ancestor_fields(parent, seen))
        ancestor_cache[class_name] = result
        return result

    edits_by_file = {}
    renamed_fields = []
    renamed_params = []

    for info in class_infos:
        code = _read_bytes(info['file_path'])
        ancestors = ancestor_fields(info['name'])
        own_field_names = set(direct_fields.get(info['name'], set()))
        used_names = set(own_field_names)
        field_renames = {}

        for field in info['fields']:
            old_name = field['name']
            if old_name not in ancestors:
                continue
            new_name = _unique_shadow_name(old_name, used_names, 'field')
            field_renames[old_name] = new_name
            edits_by_file.setdefault(info['file_path'], []).append(
                (field['name_node'].start_byte, field['name_node'].end_byte, new_name)
            )
            renamed_fields.append((info['name'], old_name, new_name))

        member_collision_names = ancestors | own_field_names
        method_param_renames = {}
        for method in info['methods']:
            method_used = set(used_names)
            method_renames = _collect_method_parameter_renames(
                method, code, member_collision_names, method_used
            )
            if method_renames:
                method_param_renames[method.id] = method_renames
                for old_name, new_name in sorted(method_renames.items()):
                    renamed_params.append((info['name'], old_name, new_name))

        def _walk_class(node, active_param_renames=None):
            if active_param_renames is None:
                active_param_renames = {}

            if node != info['class_node'] and node.type in TOP_LEVEL_TYPES:
                return

            if node.type in ('method_declaration', 'constructor_declaration'):
                active_param_renames = method_param_renames.get(node.id, {})

            if _is_identifier_node(node):
                name = extract_text_by_bytes(code, node.start_byte, node.end_byte)
                replacement = None

                if (
                    name in active_param_renames
                    and not _is_field_access_field_identifier(node)
                    and not _is_method_declaration_name(node)
                    and not _is_method_invocation_name(node)
                ):
                    replacement = active_param_renames[name]
                elif name in field_renames:
                    in_method = _nearest_method_or_class(node)
                    param_shadows = (
                        in_method is not None
                        and in_method.id in method_param_renames
                        and name in method_param_renames[in_method.id]
                    )
                    if _is_this_field_identifier(node, code) or (
                        not param_shadows and not _is_field_access_field_identifier(node)
                    ):
                        replacement = field_renames[name]

                if replacement is not None:
                    edits_by_file.setdefault(info['file_path'], []).append(
                        (node.start_byte, node.end_byte, replacement)
                    )

            for child in node.children:
                _walk_class(child, active_param_renames)

        if field_renames or method_param_renames:
            _walk_class(info['class_node'])

    modified_files = 0
    for java_file, edits in edits_by_file.items():
        if _apply_byte_edits(java_file, edits):
            modified_files += 1

    if renamed_fields:
        for class_name, old_name, new_name in renamed_fields:
            print(f"  field {class_name}.{old_name} -> {new_name}")
    if renamed_params:
        for class_name, old_name, new_name in renamed_params:
            print(f"  param {class_name}.{old_name} -> {new_name}")
    if not renamed_fields and not renamed_params:
        print("  No inherited shadow conflicts found.")
    else:
        print(f"  Modified {modified_files} file(s)")

    return len(renamed_fields) + len(renamed_params)


def _collect_project_source_info(output_dir, parser):
    file_infos = {}
    class_records = []

    for java_file in _iter_java_files(output_dir):
        code = _read_bytes(java_file)
        code_text = code.decode('utf-8')
        tree = parser.parse(code)
        refs = set()
        _collect_type_refs(tree.root_node, code, refs)

        file_info = {
            'file_path': java_file,
            'package': _extract_package_name(code_text),
            'imports': _extract_imports(code_text),
            'raw_subpath': compute_skeleton_sub_path(java_file),
            'full_subpath': _full_source_subpath(java_file),
            'type_refs': refs,
        }
        file_infos[java_file] = file_info
        _collect_top_level_classes(tree.root_node, code, class_records,
                                   file_info)

    return file_infos, class_records


def _build_java_package_graph(file_infos, class_records):
    graph = {}
    fqcn_to_record = {record['fqcn']: record for record in class_records}
    simple_to_fqcns = {}
    package_simple_to_fqcn = {}

    for record in class_records:
        graph.setdefault(record['raw_subpath'], set())
        simple_to_fqcns.setdefault(record['name'], set()).add(record['fqcn'])
        package_simple_to_fqcn[(record['package'], record['name'])] = record['fqcn']

    for file_path, info in file_infos.items():
        src_subpath = info['raw_subpath']
        graph.setdefault(src_subpath, set())

        for imported_fqcn in info['imports'].values():
            if imported_fqcn in fqcn_to_record:
                add_package_edge(graph, src_subpath,
                                 fqcn_to_record[imported_fqcn]['raw_subpath'])

        for ref in info['type_refs']:
            ref = ref.strip()
            if not ref:
                continue

            target_fqcn = None
            if '.' in ref and ref in fqcn_to_record:
                target_fqcn = ref
            else:
                short = ref.replace('$', '_').split('.')[-1]
                if short in info['imports']:
                    target_fqcn = info['imports'][short]
                elif (info['package'], short) in package_simple_to_fqcn:
                    target_fqcn = package_simple_to_fqcn[(info['package'], short)]
                elif len(simple_to_fqcns.get(short, ())) == 1:
                    target_fqcn = next(iter(simple_to_fqcns[short]))

            if target_fqcn in fqcn_to_record:
                add_package_edge(graph, src_subpath,
                                 fqcn_to_record[target_fqcn]['raw_subpath'])

    return graph


def _resolve_flattened_class_renames(class_records, effective_subpaths):
    by_effective_name = {}
    for record in class_records:
        record['effective_subpath'] = effective_subpaths.get(
            record['raw_subpath'], record['raw_subpath'])
        key = (record['effective_subpath'], record['name'])
        by_effective_name.setdefault(key, []).append(record)

    names_by_effective = {}
    for record in class_records:
        names_by_effective.setdefault(record['effective_subpath'], set()).add(
            record['name'])

    renames = {}
    def _sort_conflict_group(item):
        (effective, name), _records = item
        return (effective or '', name)

    for (_effective, _name), records in sorted(
            by_effective_name.items(), key=_sort_conflict_group):
        if len(records) <= 1:
            continue

        has_root_record = any(record['full_subpath'] is None for record in records)
        if has_root_record:
            records_to_rename = [
                record for record in records if record['full_subpath'] is not None
            ]
        else:
            records_to_rename = list(records)

        used_names = set(names_by_effective.get(_effective, set()))
        for record in records_to_rename:
            used_names.discard(record['name'])

        for record in sorted(records_to_rename,
                             key=lambda item: item['file_path']):
            prefix = _sanitize_subpath(
                record['full_subpath'] or record['raw_subpath'] or 'root')
            candidate_base = f"{prefix}_{record['name']}"
            candidate = candidate_base
            suffix = 2
            while candidate in used_names:
                candidate = f"{candidate_base}_{suffix}"
                suffix += 1
            used_names.add(candidate)
            renames[record['fqcn']] = {
                'old_name': record['name'],
                'new_name': candidate,
                'package': record['package'],
                'file_path': record['file_path'],
                'raw_subpath': record['raw_subpath'],
                'full_subpath': record['full_subpath'],
                'effective_subpath': record['effective_subpath'],
            }
    return renames


def _node_is_class_like_simple_reference(node):
    parent = node.parent
    if parent is None:
        return node.type == 'type_identifier'

    if parent.type in ('scoped_identifier', 'scoped_type_identifier'):
        return False

    if node.type == 'type_identifier':
        return True

    if parent.type in TOP_LEVEL_TYPES + ('constructor_declaration',):
        return parent.child_by_field_name('name') == node

    if parent.type in ('method_invocation', 'field_access'):
        return parent.child_by_field_name('object') == node

    return False


def _collect_reference_edits(node, code, file_info, renames_by_fqcn,
                             simple_to_renamed, edits):
    node_text = None
    if node.type in ('scoped_identifier', 'scoped_type_identifier'):
        node_text = extract_text_by_bytes(code, node.start_byte, node.end_byte)
        if node_text in renames_by_fqcn:
            name_node = node.child_by_field_name('name')
            if name_node is None:
                for child in reversed(node.children):
                    if child.type in ('identifier', 'type_identifier'):
                        name_node = child
                        break
            if name_node:
                edits.append((name_node.start_byte, name_node.end_byte,
                              renames_by_fqcn[node_text]['new_name']))

    if node.type in ('identifier', 'type_identifier'):
        old_name = extract_text_by_bytes(code, node.start_byte, node.end_byte)
        if old_name in simple_to_renamed and _node_is_class_like_simple_reference(node):
            parent = node.parent
            if parent and parent.type in TOP_LEVEL_TYPES + ('constructor_declaration',):
                for rename_fqcn in simple_to_renamed[old_name]:
                    rename = renames_by_fqcn[rename_fqcn]
                    if rename['file_path'] == file_info.get('file_path'):
                        edits.append((node.start_byte, node.end_byte,
                                      rename['new_name']))
                        break
                return

            target_fqcn = None
            imported_fqcn = file_info['imports'].get(old_name)
            same_package_fqcn = (
                f"{file_info['package']}.{old_name}"
                if file_info['package'] else old_name
            )
            if imported_fqcn in renames_by_fqcn:
                target_fqcn = imported_fqcn
            elif imported_fqcn is None and same_package_fqcn in renames_by_fqcn:
                target_fqcn = same_package_fqcn

            if target_fqcn:
                edits.append((node.start_byte, node.end_byte,
                              renames_by_fqcn[target_fqcn]['new_name']))

    for child in node.children:
        _collect_reference_edits(child, code, file_info, renames_by_fqcn,
                                 simple_to_renamed, edits)


def _apply_byte_edits(file_path, edits):
    if not edits:
        return False
    code = bytearray(_read_bytes(file_path))
    unique = {}
    for start, end, replacement in edits:
        unique[(start, end)] = replacement
    for (start, end), replacement in sorted(unique.items(), reverse=True):
        code[start:end] = replacement.encode('utf-8')
    with open(file_path, 'wb') as f:
        f.write(code)
    return True


def _rename_java_files(renames_by_fqcn):
    moved = {}
    for rename in renames_by_fqcn.values():
        old_path = rename['file_path']
        dirname = os.path.dirname(old_path)
        new_path = os.path.join(dirname, f"{rename['new_name']}.java")
        if old_path == new_path:
            continue
        if os.path.exists(new_path):
            raise RuntimeError(f"Cannot rename {old_path}: {new_path} exists")
        os.rename(old_path, new_path)
        moved[old_path] = new_path
        rename['file_path'] = new_path
    return moved


def _handle_flattened_subpackage_conflicts(output_dir, parser):
    print("Step 4/5: Detecting flattened subpackage class conflicts...")
    file_infos, class_records = _collect_project_source_info(output_dir, parser)
    graph = _build_java_package_graph(file_infos, class_records)
    effective_subpaths = compute_effective_subpath_map(graph)
    renames_by_fqcn = _resolve_flattened_class_renames(
        class_records, effective_subpaths)

    changed_subpaths = {
        raw: effective for raw, effective in effective_subpaths.items()
        if raw is not None and raw != effective
    }
    if changed_subpaths:
        collapsed_text = ', '.join(
            f"{raw}->{effective or '<root>'}"
            for raw, effective in sorted(changed_subpaths.items())
        )
        print(f"  Effective collapsed packages: {collapsed_text}")

    if not renames_by_fqcn:
        print("  No flattened subpackage class conflicts found.")
        return 0

    simple_to_renamed = {}
    for fqcn, rename in renames_by_fqcn.items():
        simple_to_renamed.setdefault(rename['old_name'], set()).add(fqcn)

# Build fqcn replacement map: old_fqcn -> new_fqcn
    # After subpackage flattening, files stay in their original package directory
    # because handle_name_conflicts only renames classes, not moves files or
    # updates package declarations.  So the correct new FQCN uses the original
    # (pre-flatten) package path plus the new class name.
    #
    # Example: org.apache.commons.validator.routines.EmailValidator
    #   -> routines_EmailValidator (renamed class, still in routines package)
    #   -> org.apache.commons.validator.routines.routines_EmailValidator (new FQCN)
    #
    # We use text-level regex replacement instead of AST byte-offset editing
    # because the AST approach (_collect_reference_edits + _apply_byte_edits)
    # produced corrupted output when multiple edits had overlapping byte ranges
    # in files with many references to the same renamed class.
    fqcn_replacements = {}
    for old_fqcn, rename in renames_by_fqcn.items():
        pkg = rename['package']
        new_name = rename['new_name']
        new_fqcn = f"{pkg}.{new_name}" if pkg else new_name
        if old_fqcn != new_fqcn:
            fqcn_replacements[old_fqcn] = new_fqcn

    # Group renames by old simple name for bare-name replacement
    # Maps old simple name -> list of (old_fqcn, new_fqcn, new_name)
    simple_name_groups = {}
    for old_fqcn, rename in renames_by_fqcn.items():
        old_name = rename['old_name']
        simple_name_groups.setdefault(old_name, []).append(
            (old_fqcn, fqcn_replacements.get(old_fqcn, old_fqcn), rename['new_name'])
        )

    modified_files = 0
    for java_file in list(_iter_java_files(output_dir)):
        with open(java_file, 'r', encoding='utf-8') as f:
            text = f.read()
        original_text = text

        # Extract imports BEFORE Pass 1, because Pass 1 rewrites FQCNs in imports
        # which changes the import key from the old simple name (e.g. UrlValidator)
        # to a new simple name (e.g. routines_UrlValidator), making it impossible
        # to match bare references to the old simple name in Pass 2.
        pre_pass1_imports = _extract_imports(text)
        pre_pass1_package = _extract_package_name(text)

        # Pass 1: Replace FQCN references (scoped identifiers / fully-qualified names)
        # This handles import statements, FQCN method calls, javadoc {@link} tags, etc.
        # Replace longest FQCNs first to avoid partial matches.
        for old_fqcn, new_fqcn in sorted(
                fqcn_replacements.items(),
                key=lambda item: len(item[0]),
                reverse=True):
            text = text.replace(old_fqcn, new_fqcn)

        # Pass 2: Replace simple name references based on imports and same-package
        # For each old simple name, check if it's imported or in the same package,
        # and if so, rename it.  This handles bare references like EmailValidator
        # that refer to the renamed class.
        #
        # We use pre-Pass-1 imports because after Pass 1 rewrites FQCNs, the import
        # keys change (e.g. UrlValidator -> routines_UrlValidator), making it
        # impossible to detect that the old simple name should be renamed.
        if simple_name_groups:
            file_imports = pre_pass1_imports
            file_package = pre_pass1_package

            for old_name, entries in simple_name_groups.items():
                if old_name not in text:
                    continue

                for old_fqcn, new_fqcn, new_name in entries:
                    # Check if this file imports or same-package-resolves the old FQCN
                    imported_fqcn = file_imports.get(old_name)
                    same_package_fqcn = (
                        f"{file_package}.{old_name}"
                        if file_package else old_name
                    )
                    # Determine if this simple name should be renamed in this file
                    should_rename = False

                    # Case 1: The old FQCN is imported (the original import, before
                    # Pass 1 rewrote it).  This means bare references to old_name
                    # in this file refer to the renamed class, so they must be
                    # updated to the new simple name.
                    if imported_fqcn == old_fqcn:
                        should_rename = True
                    # Case 2: Same-package reference — the class is in the same
                    # package so it doesn't need an import.
                    elif imported_fqcn is None and same_package_fqcn == old_fqcn:
                        should_rename = True

                    if should_rename:
                        # Use negative lookbehind to avoid replacing simple names
                        # that are part of fully-qualified names (e.g.
                        # "org.apache.commons.validator.DateValidator" should NOT
                        # have its trailing "DateValidator" replaced when the
                        # import resolves to routines.DateValidator — the FQCN
                        # refers to a different class in the same package).
                        # Pattern: word-boundary + old_name, but NOT preceded by
                        # a word char + dot (which means it's the last component
                        # of a qualified name).
                        text = re.sub(
                            rf'(?<!\w\.)\b{re.escape(old_name)}\b',
                            new_name, text)
                        # Only rename once per old_name per file
                        break

        if text != original_text:
            with open(java_file, 'w', encoding='utf-8') as f:
                f.write(text)
            modified_files += 1

    _rename_java_files(renames_by_fqcn)

    for fqcn, rename in sorted(renames_by_fqcn.items()):
        rel = os.path.relpath(rename['file_path'], output_dir)
        print(f"  {fqcn} -> {rename['new_name']} ({rel})")
    print(f"  Modified {modified_files} file(s)")
    return len(renames_by_fqcn)


def main(args):
    input_dir = f"projects/java/keyword_handled/{args.project}"
    output_dir = f"projects/java/name_handled/{args.project}"

    if not os.path.exists(input_dir):
        print(f"Error: Input directory not found: {input_dir}")
        return

    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)

    def _ignore_git_and_benchmarks(directory, files):
        """Ignore .git dirs and benchmarks directories during copy."""
        ignored = set()
        for f in files:
            full = os.path.join(directory, f)
            if f == '.git' and os.path.isdir(full):
                ignored.add(f)
            if f == 'benchmarks' and os.path.isdir(full):
                ignored.add(f)
        return ignored

    shutil.copytree(input_dir, output_dir, ignore=_ignore_git_and_benchmarks)

    # Step 1: Collect all top-level class names (for conflict detection)
    # and extends relationships (for inner class bare-name replacement in subclasses).
    print("Step 1/5: Collecting class names...")
    parser = load_parser()
    all_names = set()
    # file_path -> set of simple parent class names (from extends/implements)
    file_extends = {}

    def _extract_super_name(node, code):
        """Extract the simple class name from a superclass/interfaces node."""
        text = extract_text_by_bytes(code, node.start_byte, node.end_byte)
        # Strip 'extends ' prefix
        if text.startswith('extends '):
            text = text[8:]
        # Strip generics and trailing args: BaseNCodec<Integer> -> BaseNCodec
        text = text.split('<')[0].split(',')[0].strip()
        # Get last component of fully-qualified name
        return text.rsplit('.', 1)[-1]

    for root, dirs, files in os.walk(output_dir):
        if _skip_dir(root):
            continue
        for fname in files:
            if not fname.endswith('.java'):
                continue
            file_path = os.path.join(root, fname)
            with open(file_path, 'rb') as f:
                code = f.read()
            tree = parser.parse(code)

            def _collect_names(node, depth=0):
                if node.type in ('class_declaration', 'interface_declaration',
                                 'enum_declaration'):
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        cls_name = extract_text_by_bytes(code,
                                        name_node.start_byte, name_node.end_byte)
                        all_names.add(cls_name)
                        # Collect extends for top-level classes (depth==1: program → class)
                        if depth == 1:
                            superclass = node.child_by_field_name('superclass')
                            if superclass:
                                super_name = _extract_super_name(superclass, code)
                                if super_name:
                                    file_extends.setdefault(file_path, set()).add(super_name)
                            # interfaces (implements)
                            interfaces = node.child_by_field_name('interfaces')
                            if interfaces:
                                for child in interfaces.children:
                                    if child.type != ',':
                                        iface_name = _extract_super_name(child, code)
                                        if iface_name:
                                            file_extends.setdefault(file_path, set()).add(iface_name)
                for child in node.children:
                    _collect_names(child, depth + 1)
            _collect_names(tree.root_node, 0)
    print(f"  Found {len(all_names)} class names, "
          f"{len(file_extends)} files with extends/implements")

    # Step 2: Find all inner classes
    print("Step 2/5: Detecting inner classes...")
    all_inner_classes = {}

    for root, dirs, files in os.walk(output_dir):
        if _skip_dir(root):
            continue
        for fname in sorted(files):
            if not fname.endswith('.java'):
                continue
            file_path = os.path.join(root, fname)
            with open(file_path, 'rb') as f:
                code = f.read()
            tree = parser.parse(code)
            ics = _find_inner_classes(code, tree)
            if ics:
                all_inner_classes[file_path] = ics

    total = sum(len(v) for v in all_inner_classes.values())
    if not all_inner_classes:
        print("  No inner classes found.")
    else:
        print(f"  Found {total} inner classes in {len(all_inner_classes)} files")

    # Step 3: Resolve names and rename
    print("Step 3/5: Resolving inner class names and renaming...")
    if all_inner_classes:
        name_map = _resolve_names(all_inner_classes, all_names)

        for file_path, ic_list in all_inner_classes.items():
            rel = os.path.relpath(file_path, output_dir)

            for ic in ic_list:
                old_name = ic['name']
                new_name = name_map[(file_path, ic['outer_class_name'], old_name)]
                if old_name == new_name:
                    continue

                outer = ic['outer_class_name']
                qualified_pattern = rf'({re.escape(outer)})\.{re.escape(old_name)}\b'
                qualified_replacement = rf'\1.{new_name}'
                dot_new_pattern = rf'\.new\s+{re.escape(old_name)}\b'
                bare_pattern = rf'(?<!\.)\b{re.escape(old_name)}\b'

                for root2, dirs2, files2 in os.walk(output_dir):
                    if _skip_dir(root2):
                        continue
                    for fname2 in files2:
                        if not fname2.endswith('.java'):
                            continue
                        fp2 = os.path.join(root2, fname2)
                        with open(fp2, 'r', encoding='utf-8') as f:
                            fc = f.read()

                        had_qualified = False
                        if re.search(qualified_pattern, fc):
                            fc = re.sub(qualified_pattern, qualified_replacement, fc)
                            had_qualified = True
                        if re.search(dot_new_pattern, fc):
                            fc = re.sub(dot_new_pattern, f'.new {new_name}', fc)
                            had_qualified = True

                        # Rename bare references in:
                        # - the defining file, or
                        # - files with qualified references (imports / usages), or
                        # - subclasses that inherit the inner class via extends
                        subclasses_outer = outer in file_extends.get(fp2, set())
                        if fp2 == file_path or had_qualified or subclasses_outer:
                            if re.search(bare_pattern, fc):
                                fc = re.sub(bare_pattern, new_name, fc)

                        if fp2 == file_path or had_qualified or subclasses_outer:
                            with open(fp2, 'w', encoding='utf-8') as f:
                                f.write(fc)

                print(f"  {rel}: {outer}.{old_name} → {new_name}")
    else:
        print("  Skipped.")

    flattened_renames = _handle_flattened_subpackage_conflicts(output_dir,
                                                               parser)
    shadow_renames = _handle_inheritance_shadow_conflicts(output_dir, parser)

    removed = clean_target_dirs(output_dir)
    if removed:
        print(f"\nCleaned {len(removed)} target director(ies)")

    print(f"\nDone: {total} inner classes found, "
          f"{flattened_renames} flattened class conflict(s) renamed, "
          f"{shadow_renames} inherited shadow conflict(s) renamed")
    print(f"Output: {output_dir}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser(
        description='Handle Java naming conflicts for Cangjie translation')
    ap.add_argument('--project', type=str, required=True, help='project name')
    args = ap.parse_args()
    main(args)
