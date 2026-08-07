#!/usr/bin/env python3
"""根据日志解析结果生成仓颉 replay / validation 测试文件。

这版在原有 replay / assert 基础上，新增了一个“best-effort dependency stub”模块：
1. 生成 `.cj` 验证用例；
2. 对 focal call 直接生成初始状态、调用语句和断言；
3. 对满足仓颉 mock 框架约束的 dependency，自动生成 `@On(...)` 桩；
4. 对当前无法可靠映射为 `@On` 的 dependency，保留注释和 `.workflow.json` 规格，便于后续增强。
"""

from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable

from log_parser import parse_logs
from mock_helper import (
    clear_reference_dict,
    listener_type_for_snapshot,
    render_dependency_side_effect_notes,
    render_expect_equal,
    render_expect_true,
    render_in_place_mutation,
    render_import_block,
    render_on_argument_matcher,
    render_on_stub_chain,
    render_test_case,
    render_value_setup,
    retrieve_from_type_map,
    side_effect_is_correct,
    update_static_fields,
)


def sanitize_identifier(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "generated"
    if cleaned[0].isdigit():
        cleaned = f"g_{cleaned}"
    return cleaned


def _extract_simple_class_name(dotted: str) -> str:
    """从点分隔路径中提取最右边的大写开头片段（即简单类名）。"""
    parts = dotted.split(".")
    for part in reversed(parts):
        if part and part[0].isupper():
            return part
    return parts[-1]


def to_cangjie_class_path(java_class_path: str) -> str:
    """把 Java/日志里的类路径尽量翻到仓颉侧可读类路径。"""
    if not java_class_path:
        return "Unknown"
    if java_class_path.startswith("src.main.") or java_class_path.startswith("src.test.") or java_class_path.startswith("src."):
        resolved = retrieve_from_type_map(java_class_path, java_class_path)
        return resolved or java_class_path.replace("$", ".")
    # Raw Java class path without src.* prefix (e.g. com.example.minimal.App)
    # Extract simple class name: rightmost uppercase-starting segment
    dotted = java_class_path.replace("$", ".")
    if "." in dotted:
        return _extract_simple_class_name(dotted)
    return dotted


def strip_project_prefix(class_path: str, project_name: str) -> str:
    prefix = f"{project_name}."
    if class_path.startswith(prefix):
        return class_path[len(prefix):]
    return class_path


def method_name_base(method_name: str) -> str:
    if not method_name:
        return "unknown"
    base = method_name.rsplit(".", 1)[-1]
    if base == "<init>":
        return "init"
    return base


def detect_project_name(project_root: Path) -> str:
    cjpm_file = project_root / "cjpm.toml"
    if cjpm_file.exists():
        content = cjpm_file.read_text(encoding="utf-8")
        match = re.search(r'^\s*name\s*=\s*"([^"]+)"', content, flags=re.MULTILINE)
        if match:
            return match.group(1).strip()
    return project_root.name


def build_package_name(project_name: str) -> str:
    return f"{project_name}.test"


def merge_imports(*import_groups: Iterable[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in import_groups:
        for line in group:
            normalized = line.strip()
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            merged.append(normalized)
    return merged


def collect_snapshots(workflow: list[dict[str, Any]]) -> list[Any]:
    values: list[Any] = []
    for method_dict in workflow:
        for key, value in method_dict.items():
            if key in {"method_name", "modifier", "occurrence_idx", "note"}:
                continue
            values.append(value)
    return values


def focal_method_name(workflow: list[dict[str, Any]]) -> str:
    for method_dict in workflow:
        if method_dict.get("note") == "skip":
            return method_dict.get("method_name", "workflow")
    if workflow:
        return workflow[-1].get("method_name", "workflow")
    return "workflow"


def workflow_output_stem(log_path: Path, workflow_index: int, workflow: list[dict[str, Any]]) -> str:
    focal = focal_method_name(workflow)
    focal_tail = "_".join(part for part in focal.split(".")[-2:] if part)
    stem = sanitize_identifier(f"{log_path.stem}_decomposed_mocker_{workflow_index}_{focal_tail}")
    return stem


def render_dependency_comments(method_dict: dict[str, Any]) -> list[str]:
    """把 dependency 规格渲染成注释块，便于定位未自动映射的场景。"""
    lines = [
        f"// dependency spec: {method_dict.get('method_name', 'unknown')} (occurrence={method_dict.get('occurrence_idx', 0)})",
    ]
    if method_dict.get("Exception thrown") is not None:
        lines.append("//   behavior: throws the recorded exception")
    elif method_dict.get("Return value") is not None:
        lines.append("//   behavior: returns the recorded snapshot")
    else:
        lines.append("//   behavior: no explicit return snapshot recorded")

    if method_dict.get("Instance Final") is not None:
        lines.append("//   side effect: mutates receiver to recorded final snapshot")
    if method_dict.get("Args Final"):
        lines.append("//   side effect: mutates one or more arguments to recorded final snapshots")
    if method_dict.get("Static Fields Changed"):
        lines.append("//   side effect: mutates static fields to recorded final snapshots")
    return lines


def method_call_expression(
    method_dict: dict[str, Any],
    arg_names: list[str],
    instance_var: str | None,
    project_name: str,
) -> str:
    method_name = method_dict.get("method_name", "")
    if not method_name:
        return "/* unknown call */"

    args = ", ".join(arg_names)
    if method_name.endswith("<init>"):
        class_path = strip_project_prefix(
            to_cangjie_class_path(method_name.rsplit(".", 1)[0]),
            project_name,
        )
        return f"{class_path}({args})"

    method_base = method_name_base(method_name)
    if instance_var is not None:
        return f"{instance_var}.{method_base}({args})"

    class_path = strip_project_prefix(
        to_cangjie_class_path(method_name.rsplit(".", 1)[0]),
        project_name,
    )
    return f"{class_path}.{method_base}({args})"


def exception_type_name(exception_json: dict[str, Any]) -> str:
    throwable_type = exception_json.get("throwable_type") or exception_json.get("type") or "java.lang.Exception"
    resolved = retrieve_from_type_map(throwable_type, throwable_type)
    if not resolved:
        return "Exception"
    return resolved.split("(", 1)[0]


def emit_initial_static_state(lines: list[str], method_dict: dict[str, Any]) -> None:
    if method_dict.get("Static Fields Initial"):
        lines.append("// restore initial static snapshot")
        lines.extend(update_static_fields(method_dict["Static Fields Initial"]))


def _augment_empty_collection_types(initial: Any, final: Any) -> Any:
    """空集合的 Args Initial 在元素类型推断上会退化成 Any；
    若 Args Final 同 idx 有非空集合，从中抓元素类型回填到 initial 的 hint 字段。"""
    if not isinstance(initial, dict) or not isinstance(final, dict):
        return initial
    if initial.get("type") != final.get("type"):
        return initial
    init_elems = initial.get("collection_elements") or []
    final_elems = final.get("collection_elements") or []
    init_keys = initial.get("keys") or []
    init_values = initial.get("values") or []
    final_keys = final.get("keys") or []
    final_values = final.get("values") or []

    augmented = dict(initial)
    if not init_elems and final_elems:
        types = {e.get("type") for e in final_elems if isinstance(e, dict) and e.get("type")}
        if len(types) == 1:
            augmented["_inferred_element_type"] = retrieve_from_type_map(next(iter(types)), "Any")
    if not init_keys and final_keys:
        types = {k.get("type") for k in final_keys if isinstance(k, dict) and k.get("type")}
        if len(types) == 1:
            augmented["_inferred_key_type"] = retrieve_from_type_map(next(iter(types)), "Any")
    if not init_values and final_values:
        types = {v.get("type") for v in final_values if isinstance(v, dict) and v.get("type")}
        if len(types) == 1:
            augmented["_inferred_value_type"] = retrieve_from_type_map(next(iter(types)), "Any")
    return augmented


def emit_arg_setup(lines: list[str], method_dict: dict[str, Any], suffix: str = "") -> list[str]:
    final_by_idx = {int(idx): snap for idx, snap in method_dict.get("Args Final", [])}
    arg_names: list[str] = []
    for arg_idx, arg_data in method_dict.get("Args Initial", []):
        arg_name = f"arg_{arg_idx}{suffix}"
        arg_names.append(arg_name)
        snapshot = _augment_empty_collection_types(arg_data, final_by_idx.get(int(arg_idx)))
        lines.extend(render_value_setup(arg_name, snapshot))
    return arg_names


def emit_instance_setup(lines: list[str], method_dict: dict[str, Any], suffix: str = "") -> str | None:
    if method_dict.get("Instance Initial") is None:
        return None
    name = f"instance_initial{suffix}"
    lines.extend(render_value_setup(name, method_dict["Instance Initial"]))
    return name


def emit_expected_post_state_assertions(lines: list[str], method_dict: dict[str, Any], arg_names: list[str], instance_var: str | None) -> None:
    if method_dict.get("Instance Final") is not None and instance_var is not None:
        lines.append(render_expect_equal(instance_var, method_dict["Instance Final"], message="receiver final snapshot"))

    for arg_idx, arg_data in method_dict.get("Args Final", []):
        if 0 <= int(arg_idx) < len(arg_names):
            lines.append(render_expect_equal(arg_names[int(arg_idx)], arg_data, message=f"arg {arg_idx} final snapshot"))

    if method_dict.get("Static Fields Changed"):
        lines.append(render_expect_true(side_effect_is_correct(method_dict["Static Fields Changed"]), message="static side effects"))


def dependency_stub_signature(
    method_dict: dict[str, Any],
    project_name: str,
) -> tuple[str | None, str | None]:
    """返回可用于 @On 的桩签名，或无法映射时的原因。"""
    method_name = method_dict.get("method_name", "")
    if not method_name:
        return None, "missing method_name"
    if method_name.endswith("<init>"):
        return None, "constructors cannot be stubbed with @On"
    if method_dict.get("modifier") == "private":
        return None, "private declarations cannot be stubbed with @On"
    if method_dict.get("Instance Initial") is not None:
        return None, "//TODO instance-member dependency requires explicit mock/spy injection; current emitter only auto-stubs static/top-level declarations"

    owner_path, _, raw_method = method_name.rpartition(".")
    if not owner_path:
        return None, "method does not have an owner path"

    cangjie_owner = strip_project_prefix(to_cangjie_class_path(owner_path), project_name)
    rendered_method = sanitize_identifier(method_name_base(raw_method))
    rendered_args = ", ".join(
        render_on_argument_matcher(arg_data)
        for _, arg_data in sorted(method_dict.get("Args Initial", []), key=lambda item: int(item[0]))
    )
    return f"{cangjie_owner}.{rendered_method}({rendered_args})", None


def dependency_group_key(
    method_dict: dict[str, Any],
    project_name: str,
) -> tuple[str, str] | None:
    signature, reason = dependency_stub_signature(method_dict, project_name)
    if signature is None:
        return None
    return signature, method_dict.get("modifier", "")


def _sorted_args_initial(method_dict: dict[str, Any]) -> list[tuple[int, Any]]:
    args = method_dict.get("Args Initial", []) or []
    try:
        return [(int(arg_idx), value) for arg_idx, value in sorted(args, key=lambda item: int(item[0]))]
    except Exception:
        return [(index, value) for index, (_, value) in enumerate(args)]


def _arg_final_snapshots(method_dict: dict[str, Any]) -> dict[int, Any]:
    finals: dict[int, Any] = {}
    for arg_idx, arg_data in method_dict.get("Args Final", []) or []:
        try:
            finals[int(arg_idx)] = arg_data
        except Exception:
            continue
    return finals


def build_dependency_stub_emission(
    method_group: list[dict[str, Any]],
    project_name: str,
    group_index: int,
) -> list[str]:
    first_method = method_group[0]
    method_name = first_method.get("method_name", "")
    owner_path, _, raw_method = method_name.rpartition(".")
    cangjie_owner = strip_project_prefix(to_cangjie_class_path(owner_path), project_name)
    rendered_method = sanitize_identifier(method_name_base(raw_method))

    arg_snapshots = _sorted_args_initial(first_method)
    arg_finals_by_method = [_arg_final_snapshots(method_dict) for method_dict in method_group]
    replayed_args_by_method: list[set[int]] = [set() for _ in method_group]
    unresolved_notes_by_method: list[list[str]] = [[] for _ in method_group]

    prelude_lines: list[str] = []
    rendered_args: list[str] = []

    for arg_idx, arg_snapshot in arg_snapshots:
        replay_lines_by_occurrence: dict[int, list[str]] = {}
        listener_type = listener_type_for_snapshot(arg_snapshot)

        for occurrence_idx, final_map in enumerate(arg_finals_by_method):
            arg_final = final_map.get(arg_idx)
            if arg_final is None:
                continue

            replay_lines, note_lines = render_in_place_mutation(f"__dep_{group_index}_arg_{arg_idx}", arg_final)
            if replay_lines:
                replay_lines_by_occurrence[occurrence_idx] = replay_lines
                replayed_args_by_method[occurrence_idx].add(arg_idx)
            unresolved_notes_by_method[occurrence_idx].extend(note_lines)

        if replay_lines_by_occurrence:
            call_counter_name = f"__dep_{group_index}_arg_{arg_idx}_call"
            listener_name = f"__dep_{group_index}_arg_{arg_idx}_listener"
            capture_name = f"__dep_{group_index}_arg_{arg_idx}"

            prelude_lines.append(f"var {call_counter_name} = 0")
            prelude_lines.append(f"let {listener_name} = ValueListener<{listener_type}>.onEach {{ {capture_name} =>")
            prelude_lines.append(f"    {call_counter_name} += 1")

            first_branch = True
            for occurrence_idx, replay_lines in replay_lines_by_occurrence.items():
                branch_head = "if" if first_branch else "else if"
                prelude_lines.append(f"    {branch_head} ({call_counter_name} == {occurrence_idx + 1}) {{")
                for line in replay_lines:
                    prelude_lines.append(f"        {line}")
                prelude_lines.append("    }")
                first_branch = False

            prelude_lines.append("}")
            rendered_args.append(f"capture({listener_name})")
            continue

        rendered_args.append(render_on_argument_matcher(arg_snapshot))

    signature_expr = f"{cangjie_owner}.{rendered_method}({', '.join(rendered_args)})"

    action_line_groups: list[list[str]] = []
    replayed_static_by_method: list[bool] = []
    for method_dict in method_group:
        action_lines: list[str] = []
        replayed_static = False
        if method_dict.get("Static Fields Changed"):
            action_lines.extend(update_static_fields(method_dict["Static Fields Changed"]))
            replayed_static = any(not line.lstrip().startswith("//") for line in action_lines)
        action_line_groups.append(action_lines)
        replayed_static_by_method.append(replayed_static)

    rendered_lines = list(prelude_lines)
    rendered_lines.append(render_on_stub_chain(signature_expr, method_group, action_line_groups=action_line_groups))

    for occurrence_idx, method_dict in enumerate(method_group):
        rendered_lines.extend(
            render_dependency_side_effect_notes(
                method_dict,
                replayed_arg_indices=replayed_args_by_method[occurrence_idx],
                replayed_static_fields=replayed_static_by_method[occurrence_idx],
            )
        )
        rendered_lines.extend(unresolved_notes_by_method[occurrence_idx])

    return rendered_lines


def build_dependency_stub_block(workflow: list[dict[str, Any]], project_name: str) -> list[str]:
    lines: list[str] = []
    dependency_methods = [method for method in workflow if method.get("note") != "skip"]
    if not dependency_methods:
        return lines

    grouped: OrderedDict[tuple[str, str], list[dict[str, Any]]] = OrderedDict()
    unsupported_lines: list[str] = []

    for method_dict in dependency_methods:
        key = dependency_group_key(method_dict, project_name)
        if key is None:
            unsupported_lines.extend(render_dependency_comments(method_dict))
            _, reason = dependency_stub_signature(method_dict, project_name)
            if reason:
                unsupported_lines.append(f"//   mock emission skipped: {reason}")
            continue
        grouped.setdefault(key, []).append(method_dict)

    if grouped:
        lines.append("// dependency stubs emitted via Cangjie @On")
        for group_index, ((_, _), method_group) in enumerate(grouped.items(), start=1):
            lines.extend(build_dependency_stub_emission(method_group, project_name, group_index))

    if unsupported_lines:
        if lines:
            lines.append("")
        lines.append("// dependencies left as spec-only entries")
        lines.extend(unsupported_lines)

    return lines


def build_focal_body(method_dict: dict[str, Any], project_name: str, suffix: str = "") -> list[str]:
    lines: list[str] = []
    emit_initial_static_state(lines, method_dict)
    instance_var = emit_instance_setup(lines, method_dict, suffix)
    arg_names = emit_arg_setup(lines, method_dict, suffix)

    call_expr = method_call_expression(method_dict, arg_names, instance_var, project_name)
    has_return_snapshot = method_dict.get("Return value") is not None
    has_exception = method_dict.get("Exception thrown") is not None
    method_ret_var = f"method_ret{suffix}"

    lines.append(f"// focal call: {method_dict.get('method_name', 'unknown')}")

    if has_exception:
        exc_json = method_dict["Exception thrown"]
        catch_type = exception_type_name(exc_json)
        lines.append("try {")
        if has_return_snapshot:
            lines.append(f"    let {method_ret_var} = {call_expr}")
            lines.append(f"    let _ = {method_ret_var}")
        else:
            lines.append(f"    {call_expr}")
        lines.append(render_expect_true("false", message="expected exception was not thrown"))
        lines.append(f"}} catch (_: {catch_type}) {{")
        lines.append("    // expected exception path")
        lines.append("}")
    else:
        if has_return_snapshot:
            lines.append(f"let {method_ret_var} = {call_expr}")
            lines.append(render_expect_equal(method_ret_var, method_dict["Return value"], message="return value snapshot"))
        else:
            lines.append(f"{call_expr}")

    emit_expected_post_state_assertions(lines, method_dict, arg_names, instance_var)
    return lines


def build_workflow_body(workflow: list[dict[str, Any]], project_name: str) -> list[str]:
    lines: list[str] = ["// generated from one isolated-validation workflow"]

    dependency_stub_lines = build_dependency_stub_block(workflow, project_name)
    if dependency_stub_lines:
        lines.extend(dependency_stub_lines)
        lines.append("")

    focal_methods = [m for m in workflow if m.get("note") == "skip"]
    multi_focal = len(focal_methods) > 1

    if focal_methods:
        for occ_idx, method_dict in enumerate(focal_methods):
            suffix = f"_{occ_idx}" if multi_focal else ""
            lines.extend(build_focal_body(method_dict, project_name, suffix))
    else:
        lines.append("// no focal method marked with note=skip; replaying the last method as fallback")
        if workflow:
            lines.extend(build_focal_body(workflow[-1], project_name))
    return lines


def write_dependency_spec(spec_path: Path, workflow: list[dict[str, Any]]) -> None:
    dependency_only = [method_dict for method_dict in workflow if method_dict.get("note") != "skip"]
    spec_path.write_text(json.dumps(dependency_only, indent=2, ensure_ascii=False), encoding="utf-8")


def process_test_log(
    log_path: str,
    parse_logs_fn=parse_logs,
    output_dir: Path | None = None,
    project_name: str | None = None,
) -> list[Path]:
    log_file = Path(log_path)
    workflows = parse_logs_fn(log_path)
    if project_name is None:
        project_name = detect_project_name(Path.cwd())
    out_dir = output_dir if output_dir is not None else Path("src") / "test"
    out_dir.mkdir(parents=True, exist_ok=True)

    generated: list[Path] = []

    for workflow_index, workflow in enumerate(workflows):
        clear_reference_dict()
        stem = workflow_output_stem(log_file, workflow_index, workflow)
        package_name = build_package_name(project_name)
        class_name = sanitize_identifier(f"{stem}_Test")
        case_name = sanitize_identifier(f"test_{stem}")
        body_lines = build_workflow_body(workflow, project_name)
        import_block = render_import_block(*collect_snapshots(workflow))
        fixed_imports = [
            f"import {project_name}.*",
            f"import {project_name}.runtime.*",
            "import std.io.*",
            "import std.collection.*",
        ]
        resolved_imports = merge_imports(
            fixed_imports,
            import_block.splitlines() if import_block else [],
        )
        test_code = render_test_case(
            package_name=package_name,
            class_name=class_name,
            case_name=case_name,
            body_lines=body_lines,
            extra_imports=resolved_imports,
            include_runtime_support=True,
        )

        test_path = out_dir / f"{stem}_test.cj"
        test_path.write_text(test_code + "\n", encoding="utf-8")
        generated.append(test_path)

        spec_path = out_dir / f"{stem}.workflow.json"
        write_dependency_spec(spec_path, workflow)
        generated.append(spec_path)

    return generated


if __name__ == "__main__":
    import argparse as _argparse
    _parser = _argparse.ArgumentParser()
    _parser.add_argument("log_file")
    _parser.add_argument("--output-dir", type=Path, default=None)
    _args = _parser.parse_args()

    clear_reference_dict()
    generated_files = process_test_log(_args.log_file, parse_logs, output_dir=_args.output_dir)
    for path in generated_files:
        print(path)
