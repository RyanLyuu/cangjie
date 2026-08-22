from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.java.type_resolution.schema import load_schema, schema_paths


@dataclass(frozen=True)
class ClassNode:
    schema_name: str
    class_key: str
    source_order: int

    @property
    def node_id(self) -> str:
        return f"{self.schema_name}::{self.class_key}"

    @property
    def class_name(self) -> str:
        return self.class_key.split(":", 1)[-1]


def schema_scc_batches(
    schema_dir: str | Path,
    *,
    project: str,
    suffix: str = "",
    include_tests: bool = False,
    workspace: str | Path | None = None,
) -> list[list[Path]]:
    """Return dependency-first file batches with cycles preserved as SCCs."""
    paths, path_by_schema, file_edges = _schema_file_graph(
        schema_dir,
        project=project,
        suffix=suffix,
        include_tests=include_tests,
        workspace=workspace,
    )
    batches = _dependency_first_sccs(file_edges)
    source_order = {path.stem: index for index, path in enumerate(paths)}
    return [
        [path_by_schema[name] for name in sorted(batch, key=source_order.__getitem__)]
        for batch in batches
    ]


def schema_dependency_closure(
    schema_dir: str | Path,
    current: str | Path,
    *,
    project: str,
    suffix: str = "",
    include_tests: bool = False,
    workspace: str | Path | None = None,
) -> list[Path]:
    """Return transitive semantic dependencies in dependency-first order."""
    _, path_by_schema, file_edges = _schema_file_graph(
        schema_dir,
        project=project,
        suffix=suffix,
        include_tests=include_tests,
        workspace=workspace,
    )
    current_path = Path(current).resolve()
    current_name = next(
        (
            name
            for name, path in path_by_schema.items()
            if path.resolve() == current_path
        ),
        None,
    )
    if current_name is None:
        return []

    result: list[Path] = []
    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in visited or name in visiting:
            return
        visiting.add(name)
        for dependency in sorted(file_edges.get(name, set())):
            visit(dependency)
        visiting.remove(name)
        visited.add(name)
        if name != current_name:
            result.append(path_by_schema[name])

    visit(current_name)
    return result


def _schema_file_graph(
    schema_dir: str | Path,
    *,
    project: str,
    suffix: str,
    include_tests: bool,
    workspace: str | Path | None,
):
    paths = schema_paths(schema_dir, include_tests=include_tests)
    nodes = []
    data_by_schema = {}
    path_by_schema = {}
    for path in paths:
        data = load_schema(path)
        data_by_schema[path.stem] = data
        path_by_schema[path.stem] = path
        for order, (class_key, info) in enumerate(data.get("classes", {}).items()):
            nodes.append(ClassNode(path.stem, class_key, int(info.get("start", order) or order)))

    by_id = {node.node_id: node for node in nodes}
    by_short = {}
    by_fqn = {}
    for node in nodes:
        by_short.setdefault(node.class_name, []).append(node.node_id)
        source_path = str(data_by_schema[node.schema_name].get("path", "")).replace("\\", "/")
        package = ""
        if "/java/" in source_path:
            package = ".".join(source_path.rsplit("/java/", 1)[1].split("/")[:-1])
        if package:
            by_fqn[f"{package}.{node.class_name}"] = node.node_id

    edges = {node.node_id: set() for node in nodes}

    def resolve_type(value: str) -> str | None:
        value = str(value).split("<", 1)[0].strip()
        if value in by_fqn:
            return by_fqn[value]
        candidates = by_short.get(value.split(".")[-1], [])
        return candidates[0] if len(candidates) == 1 else None

    for node in nodes:
        info = data_by_schema[node.schema_name]["classes"][node.class_key]
        for value in [*info.get("extends", ()), *info.get("implements", ())]:
            target = resolve_type(value)
            if target and target != node.node_id:
                edges[node.node_id].add(target)
        nested = str(info.get("nested_inside", ""))
        if nested:
            target = f"{node.schema_name}::{nested}"
            if target in by_id and target != node.node_id:
                edges[node.node_id].add(target)

    _add_jdeps_edges(
        edges,
        nodes,
        by_fqn,
        by_short,
        project,
        suffix,
        workspace=workspace,
    )

    # Collapse class dependencies to files only after class identity is unambiguous.
    file_edges = {name: set() for name in path_by_schema}
    for source, dependencies in edges.items():
        source_file = by_id[source].schema_name
        for dependency in dependencies:
            dependency_file = by_id[dependency].schema_name
            if source_file != dependency_file:
                file_edges[source_file].add(dependency_file)

    return paths, path_by_schema, file_edges


def fragment_order(schema: dict) -> list[dict]:
    """Order fields, initializers, constructors, and methods dependency-first."""
    result = []
    for class_key, class_info in sorted(
        schema.get("classes", {}).items(), key=lambda item: int(item[1].get("start", 0) or 0)
    ):
        fields = class_info.get("fields", {})
        field_edges = {key: set() for key in fields}
        field_names = {key.split(":", 1)[-1]: key for key in fields}
        for key, info in fields.items():
            initializer = "\n".join(info.get("body", [])).split("=", 1)[-1]
            for name, dependency in field_names.items():
                if dependency != key and name in initializer:
                    field_edges[key].add(dependency)
        for batch in _dependency_first_sccs(field_edges):
            for key in sorted(batch, key=lambda item: int(fields[item].get("start", 0) or 0)):
                if not fields[key].get("enum_constant"):
                    result.append(_fragment(class_key, key, "field", fields[key]))

        for key, info in sorted(
            class_info.get("static_initializers", {}).items(),
            key=lambda item: int(item[1].get("start", 0) or 0),
        ):
            result.append(_fragment(class_key, key, "static_initializer", info))

        methods = class_info.get("methods", {})
        constructors = [key for key, info in methods.items() if info.get("is_constructor")]
        for key in sorted(constructors, key=lambda item: int(methods[item].get("start", 0) or 0)):
            result.append(_fragment(class_key, key, "method", methods[key]))

        normal = {key: info for key, info in methods.items() if not info.get("is_constructor")}
        method_edges = {key: set() for key in normal}
        names = {}
        for key in normal:
            names.setdefault(key.split(":", 1)[-1], []).append(key)
        class_name = class_key.split(":", 1)[-1]
        for key, info in normal.items():
            for call in info.get("calls", []):
                if not isinstance(call, list) or len(call) < 3:
                    continue
                callee_class = str(call[1]).split(".")[-1].split("$")[0]
                callee_name = str(call[2]).split("(", 1)[0].split(".")[-1]
                if callee_class != class_name:
                    continue
                candidates = names.get(callee_name, [])
                if len(candidates) == 1 and candidates[0] != key:
                    method_edges[key].add(candidates[0])
        for batch in _dependency_first_sccs(method_edges):
            for key in sorted(batch, key=lambda item: int(normal[item].get("start", 0) or 0)):
                result.append(_fragment(class_key, key, "method", normal[key]))
    return result


def _fragment(class_key: str, key: str, kind: str, info: dict) -> dict:
    return {
        "class_key": class_key,
        "class_name": class_key.split(":", 1)[-1],
        "fragment_name": key,
        "fragment_type": kind,
        "signature": info.get("signature", ""),
        "is_constructor": bool(info.get("is_constructor", False)),
        "start": int(info.get("start", 0) or 0),
    }


def _add_jdeps_edges(
    edges,
    nodes,
    by_fqn,
    by_short,
    project,
    suffix,
    *,
    workspace: str | Path | None = None,
):
    root = Path(workspace) if workspace is not None else Path.cwd()
    path = root / f"data/java/dependencies{suffix}/{project}/dependencies.json"
    if not path.is_file():
        return
    raw = json.loads(path.read_text(encoding="utf-8"))
    by_schema_path = {}
    for node in nodes:
        schema_path = node.schema_name
        partial = schema_path
        prefix = f"{project}."
        if partial.startswith(prefix):
            partial = partial[len(prefix):]
        partial = partial.replace("src.main.", "").replace("src.test.", "")
        by_schema_path.setdefault(partial, []).append(node.node_id)
        by_schema_path.setdefault(node.class_name, []).append(node.node_id)
    for source_path, dependencies in raw.items():
        sources = by_schema_path.get(source_path, [])
        if "." not in source_path and len({item.split("::", 1)[0] for item in sources}) > 1:
            # A simple name shared by multiple schemas is not a safe dependency identity.
            sources = []
        for dependency in dependencies:
            if not isinstance(dependency, list) or len(dependency) < 2:
                continue
            name, fqn = str(dependency[0]), str(dependency[1])
            target = by_fqn.get(fqn)
            if target is None:
                candidates = by_short.get(name, [])
                target = candidates[0] if len(candidates) == 1 else None
            if not target:
                continue
            for source in sources:
                if source != target:
                    edges[source].add(target)


def _dependency_first_sccs(graph: dict[str, set[str]]) -> list[list[str]]:
    for dependencies in list(graph.values()):
        for node in dependencies:
            graph.setdefault(node, set())
    components = _tarjan(graph)
    component_of = {node: index for index, component in enumerate(components) for node in component}
    dependencies = {index: set() for index in range(len(components))}
    for source, targets in graph.items():
        source_component = component_of[source]
        for target in targets:
            target_component = component_of[target]
            if source_component != target_component:
                dependencies[source_component].add(target_component)
    result = []
    remaining = set(dependencies)
    while remaining:
        ready = sorted(
            (index for index in remaining if not (dependencies[index] & remaining)),
            key=lambda index: min(components[index]),
        )
        if not ready:
            raise RuntimeError("SCC condensation graph unexpectedly contains a cycle")
        for index in ready:
            result.append(sorted(components[index]))
            remaining.remove(index)
    return result


def _tarjan(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack = []
    on_stack = set()
    indices = {}
    lowlink = {}
    result = []

    def visit(node):
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for target in sorted(graph[node]):
            if target not in indices:
                visit(target)
                lowlink[node] = min(lowlink[node], lowlink[target])
            elif target in on_stack:
                lowlink[node] = min(lowlink[node], indices[target])
        if lowlink[node] == indices[node]:
            component = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            result.append(component)

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return result
