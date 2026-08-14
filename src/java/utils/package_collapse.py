#!/usr/bin/env python3
"""Utilities for deciding Java subpackages collapsed into Cangjie packages."""
import os
import shutil
from pathlib import Path


def compute_skeleton_sub_path(java_path):
    """
    Compute the Cangjie skeleton sub_path by walking up the Java directory tree.

    Finds the nearest directory containing .java files, then finds the nearest
    ancestor that also contains .java files. The difference is the meaningful
    subpackage path.
    """
    path_parts = java_path.split('/')[:-1]
    java_parent_dir = '/'.join(path_parts)

    first_java_dir_full_path = None
    for i in range(len(path_parts) - 1, -1, -1):
        current_dir = path_parts[i]
        if current_dir == 'src':
            break
        check_dir = '/'.join(path_parts[:i + 1])
        if os.path.isdir(check_dir):
            java_files = [f for f in os.listdir(check_dir) if f.endswith('.java')]
            if java_files:
                first_java_dir_full_path = check_dir
                break

    if not first_java_dir_full_path:
        return None

    base_java_dir_full_path = None
    first_name = first_java_dir_full_path.split('/')[-1]
    if first_name in path_parts:
        first_index = path_parts.index(first_name)
        for i in range(first_index - 1, -1, -1):
            current_dir = path_parts[i]
            if current_dir == 'src':
                break
            check_dir = '/'.join(path_parts[:i + 1])
            if os.path.isdir(check_dir):
                java_files = [f for f in os.listdir(check_dir) if f.endswith('.java')]
                if java_files:
                    base_java_dir_full_path = check_dir
                    break

    if base_java_dir_full_path:
        return first_java_dir_full_path[len(base_java_dir_full_path) + 1:]
    if java_parent_dir != first_java_dir_full_path:
        return first_java_dir_full_path.split('/')[-1]
    return None


def get_effective_skeleton_sub_path(java_path, effective_subpaths=None):
    """Return the final Cangjie subpath for a Java source path."""
    sub_path = compute_skeleton_sub_path(java_path)
    if not effective_subpaths:
        return sub_path
    if isinstance(effective_subpaths, dict):
        return effective_subpaths.get(sub_path, sub_path)
    return None if sub_path in effective_subpaths else sub_path


def get_cangjie_package(java_path, cjpm_package_name, effective_subpaths=None):
    """Compute Cangjie package name from a Java source file path."""
    sub_path = get_effective_skeleton_sub_path(java_path, effective_subpaths)
    if sub_path:
        return f"{cjpm_package_name}.{sub_path.replace('/', '.')}"
    return cjpm_package_name


def extract_type_names(type_expr):
    """Extract base type names from a generic-ish type string."""
    names = set()
    depth = 0
    current = ""
    for c in str(type_expr):
        if c == '<':
            depth += 1
            if current.strip():
                names.add(current.strip())
            current = ""
        elif c == '>':
            depth -= 1
            if current.strip():
                names.add(current.strip())
            current = ""
        elif c == ',' and depth > 0:
            if current.strip():
                names.add(current.strip())
            current = ""
        elif c == ' ':
            continue
        else:
            current += c
    if current.strip():
        names.add(current.strip())
    return names


def _should_update_class_subpath(existing_subpath, candidate_subpath):
    if existing_subpath is None:
        return True
    if candidate_subpath is not None and existing_subpath != candidate_subpath:
        return True
    return False


def _iter_schema_type_expressions(schema, class_info):
    for imported_type in schema.get('import_map', {}).values():
        yield imported_type
    for ref_type in class_info.get('extends', []) + class_info.get('implements', []):
        yield ref_type
    for field_info in class_info.get('fields', {}).values():
        for type_expr in field_info.get('types', []):
            yield type_expr
    for method_info in class_info.get('methods', {}).values():
        for type_expr in method_info.get('return_types', []):
            yield type_expr
        for param in method_info.get('parameters', []):
            yield param.get('type', 'Any')


def build_schema_class_to_raw_subpath(all_schemas):
    class_to_subpath = {}
    for _schema_fname, _schema_path, schema in all_schemas:
        raw_subpath = compute_skeleton_sub_path(schema.get('path', ''))
        for class_key in schema.get('classes', {}):
            class_name = class_key.split(':')[-1]
            if _should_update_class_subpath(class_to_subpath.get(class_name), raw_subpath):
                class_to_subpath[class_name] = raw_subpath
    return class_to_subpath


def _find_dependency_key_for_schema(dependencies, schema_fname):
    schema_stem = schema_fname[:-5] if schema_fname.endswith('.json') else schema_fname
    matches = [
        key for key in dependencies
        if schema_stem == key or schema_stem.endswith(f".{key}")
    ]
    if not matches:
        return None
    return max(matches, key=len)


def add_package_edge(graph, src_subpath, dst_subpath):
    graph.setdefault(src_subpath, set())
    graph.setdefault(dst_subpath, set())
    if dst_subpath != src_subpath:
        graph[src_subpath].add(dst_subpath)


def build_schema_package_dependency_graph(
        all_schemas, class_to_subpath, type_map, dependencies=None,
        translate_type=None):
    graph = {}
    dependencies = dependencies or {}
    for schema_fname, _schema_path, schema in all_schemas:
        src_subpath = compute_skeleton_sub_path(schema.get('path', ''))
        graph.setdefault(src_subpath, set())

        # Structural fallbacks are emitted as project-root interfaces by the
        # skeleton generator.  A schema in a Java subpackage that materializes
        # one of these placeholders therefore imports the root package, even
        # though the placeholder is not a Java class and cannot appear in
        # ``class_to_subpath``.  Keep that edge in the package graph so the
        # effective layout collapses the subpackage before generation.
        if src_subpath is not None and schema.get('generated_type_placeholders'):
            add_package_edge(graph, src_subpath, None)

        dependency_key = _find_dependency_key_for_schema(dependencies, schema_fname)
        if dependency_key and dependency_key in dependencies:
            for dependent_class in dependencies[dependency_key]:
                dep_class_name = dependent_class[0]
                if dep_class_name in class_to_subpath:
                    add_package_edge(graph, src_subpath, class_to_subpath[dep_class_name])

        for class_info in schema.get('classes', {}).values():
            for type_expr in _iter_schema_type_expressions(schema, class_info):
                if not type_expr:
                    continue
                type_names = extract_type_names(str(type_expr))
                if translate_type:
                    translated_type = translate_type(str(type_expr), type_map)
                    type_names |= extract_type_names(translated_type)
                for type_name in type_names:
                    short_name = type_name.strip().replace('$', '_').split('.')[-1]
                    if short_name not in class_to_subpath:
                        continue
                    add_package_edge(graph, src_subpath, class_to_subpath[short_name])
    return graph


def find_cyclic_subpaths(graph):
    index = 0
    stack = []
    indices = {}
    lowlinks = {}
    on_stack = set()
    cyclic = set()

    def strongconnect(node):
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in indices:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] == indices[node]:
            component = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            if len(component) > 1:
                cyclic.update(component)

    for node in list(graph):
        if node not in indices:
            strongconnect(node)
    return cyclic


def _apply_collapses(subpath, collapsed):
    """Apply exact or ancestor collapses without recursively flattening children."""
    if subpath is None:
        return None
    parts = subpath.split('/')
    best_idx = None
    for i in range(len(parts)):
        prefix = '/'.join(parts[:i + 1])
        if prefix in collapsed:
            best_idx = i
    if best_idx is None:
        return subpath
    remainder = parts[best_idx + 1:]
    return '/'.join(remainder) if remainder else None


def compute_effective_subpath_map(graph):
    """
    Compute minimal Cangjie package mapping for raw Java subpaths.

    A raw subpath is collapsed when it participates in a package cycle or when
    it depends on the root package. Descendant subpaths keep their remaining
    suffix instead of being flattened with the parent.
    """
    collapsed = set()
    raw_subpaths = set(graph)
    for targets in graph.values():
        raw_subpaths.update(targets)

    while True:
        raw_to_effective = {
            subpath: _apply_collapses(subpath, collapsed)
            for subpath in raw_subpaths
        }
        effective_graph = {}
        effective_to_raw = {}
        for raw, effective in raw_to_effective.items():
            effective_graph.setdefault(effective, set())
            effective_to_raw.setdefault(effective, set()).add(raw)
        for src, targets in graph.items():
            eff_src = raw_to_effective.get(src, src)
            effective_graph.setdefault(eff_src, set())
            for dst in targets:
                eff_dst = raw_to_effective.get(dst, dst)
                if eff_dst != eff_src:
                    effective_graph[eff_src].add(eff_dst)
                    effective_graph.setdefault(eff_dst, set())

        newly_effective = {
            subpath for subpath in find_cyclic_subpaths(effective_graph)
            if subpath is not None
        }
        for subpath, targets in effective_graph.items():
            if subpath is not None and None in targets:
                newly_effective.add(subpath)

        newly_raw = set()
        for effective in newly_effective:
            for raw in effective_to_raw.get(effective, set()):
                if raw is not None:
                    newly_raw.add(raw)

        before = set(collapsed)
        collapsed.update(newly_raw)
        if collapsed == before:
            return raw_to_effective


def compute_schema_effective_subpath_map(
        all_schemas, type_map, dependencies=None, translate_type=None):
    class_to_subpath = build_schema_class_to_raw_subpath(all_schemas)
    graph = build_schema_package_dependency_graph(
        all_schemas, class_to_subpath, type_map, dependencies, translate_type)
    return compute_effective_subpath_map(graph)


def remove_collapsed_output_dirs(project_dir, effective_subpaths):
    """Remove stale output dirs for raw subpaths whose effective path changed."""
    if not effective_subpaths:
        return
    src_dir = Path(project_dir) / "src"
    for raw_subpath, effective_subpath in effective_subpaths.items():
        if raw_subpath is None or raw_subpath == effective_subpath:
            continue
        target = src_dir / raw_subpath
        if target.is_dir():
            shutil.rmtree(target)
