"""
插桩工具：在每个 _test.cj 执行前，根据工作日志找出有真实 side effect 的被拦截依赖方法，
在被测方法（focal method）的 Cangjie 源文件中，对应依赖调用语句之后插入赋值语句回放 side effect。
测试结束后通过 deinstrument 扫描并清除所有 stub 块。

插桩逻辑：
  - Static Fields Changed → 静态字段赋值语句
  - Instance Final       → 对 receiver 变量的字段赋值
  - Args Final（真实 mutation）→ 对调用点实参变量的赋值
  以上均插入到 focal method 源文件中对应 callee 调用语句的正后方。
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

STUB_OPEN  = "// __SIDEEFFECT_STUB_BEGIN__"
STUB_CLOSE = "// __SIDEEFFECT_STUB_END__"
EXPRESSION_SIDE_EFFECT_UNREPLAYABLE = "expression-side-effect-unreplayable"
INSTANCE_METHOD_DEPENDENCY = "instance-method-dependency"

_THIS_DIR = Path(__file__).parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from mock_helper import (
    _deep_equal,
    _is_mutable_snapshot,
    render_in_place_mutation,
    update_static_fields,
)


# ===========================================================================
# 从测试文件提取 focal method 信息
# ===========================================================================

def _extract_focal_info(test_cj_path: str) -> tuple[str, str] | None:
    """从 _test.cj 的 '// focal call: ...' 注释中提取 class 名和 method 名。"""
    for line in Path(test_cj_path).read_text(encoding="utf-8").splitlines():
        m = re.search(r"//\s*focal call:\s*[\w.$]+\.(\w+)\.(\w+)", line)
        if m:
            return m.group(1), m.group(2)
    return None


# ===========================================================================
# 查找 focal class 所在的 Cangjie 源文件
# ===========================================================================

def _find_source_file(cj_main_dir: str, class_name: str) -> Path | None:
    root = Path(cj_main_dir)
    for p in root.rglob(f"{class_name}.cj"):
        return p
    for p in root.rglob("*.cj"):
        if re.search(rf'\bclass\s+{re.escape(class_name)}\b', p.read_text(encoding="utf-8")):
            return p
    return None


# ===========================================================================
# 定位 focal method 体的行范围
# ===========================================================================

def _find_method_body_range(lines: list[str], method_name: str) -> tuple[int, int]:
    """返回 focal method 体的 [start, end)，找不到返回 (-1, -1)。"""
    pat = re.compile(rf'\bfunc\s+{re.escape(method_name)}\b')
    for i, line in enumerate(lines):
        if pat.search(line):
            depth = 0
            body_start = -1
            for j in range(i, len(lines)):
                for c in lines[j]:
                    if c == '{':
                        if depth == 0:
                            body_start = j
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            return body_start, j + 1
            break
    return -1, -1


# ===========================================================================
# 在方法体内查找 callee 调用行
# ===========================================================================

def _find_call_line(
    lines: list[str],
    body_start: int,
    body_end: int,
    short_name: str,
    occurrence_idx: int,
) -> int:
    """找第 occurrence_idx 次调用 short_name( 的全局行号，找不到返回 -1。"""
    pat = re.compile(rf'\b{re.escape(short_name)}\s*\(')
    found = 0
    for i in range(body_start + 1, body_end):
        if pat.search(lines[i]):
            if found == occurrence_idx:
                return i
            found += 1
    return -1


def _call_span(line: str, short_name: str) -> tuple[int, int] | None:
    """Return the character span of the short_name(...) call in one physical line."""
    pat = re.compile(rf'(?:\b\w[\w.]*\s*\.\s*)?\b{re.escape(short_name)}\s*\(')
    m = pat.search(line)
    if not m:
        return None
    i = m.end()
    depth = 1
    while i < len(line) and depth > 0:
        c = line[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        i += 1
    if depth != 0:
        return None
    return m.start(), i


def _strip_line_comment(text: str) -> str:
    return text.split("//", 1)[0].strip()


def _is_simple_lvalue(text: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][\w.]*(?:\[[^\]]+\])?", text.strip()))


def _call_site_replay_blocker(line: str, short_name: str) -> str | None:
    """Return a blocker reason when a side-effectful call is embedded in an unsafe expression.

    Side-effect replay inserts statements before/after a physical call line. That is only
    semantically safe for standalone calls and simple assignment/let initializers whose RHS
    is exactly the dependency call. Calls nested inside return expressions, conditions,
    arguments, chained calls, or larger expressions cannot be replayed independently.
    """
    code = _strip_line_comment(line)
    span = _call_span(code, short_name)
    if span is None:
        return EXPRESSION_SIDE_EFFECT_UNREPLAYABLE

    start, end = span
    before = code[:start].strip()
    after = code[end:].strip()

    if after not in {"", ";"}:
        return EXPRESSION_SIDE_EFFECT_UNREPLAYABLE

    if before == "":
        return None

    if re.fullmatch(r"(?:let|var)\s+[A-Za-z_]\w*(?:\s*:\s*[^=]+)?\s*=", before):
        return None

    if before.endswith("=") and _is_simple_lvalue(before[:-1]):
        return None

    return EXPRESSION_SIDE_EFFECT_UNREPLAYABLE


# ===========================================================================
# 解析调用实参和 receiver
# ===========================================================================

def _parse_call_args(line: str, short_name: str) -> list[str]:
    """从调用行中提取实参列表，正确处理嵌套括号。"""
    pat = re.compile(rf'\b{re.escape(short_name)}\s*\(')
    m = pat.search(line)
    if not m:
        return []
    i = m.end()
    depth, current, args = 1, [], []
    while i < len(line) and depth > 0:
        c = line[i]
        if c in "([{":
            depth += 1
            current.append(c)
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append("".join(current).strip())
            else:
                current.append(c)
        elif c == "," and depth == 1:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(c)
        i += 1
    return [a for a in args if a]


def _parse_receiver(line: str, short_name: str) -> str | None:
    """提取 receiver.short_name(...) 中的 receiver；静态调用（类名.方法名）返回 None。"""
    pat = re.compile(rf'(\w[\w.]*)\s*\.\s*{re.escape(short_name)}\s*\(')
    m = pat.search(line)
    if not m:
        return None
    candidate = m.group(1)
    # 类名首字母大写视为静态调用，不算 receiver
    if candidate and candidate[0].isupper():
        return None
    return candidate


# ===========================================================================
# 判断是否有真实 side effect
# ===========================================================================

def _minimize_to_changed_fields(initial: Any, final: Any) -> Any:
    """
    返回 final 的"变更子集"快照：仅保留 instance_fields 中与 initial 不同的字段。
    集合类型（ArrayList 等）原样返回，因为它们走的是 reset 整体替换路径。
    """
    if not isinstance(initial, dict) or not isinstance(final, dict):
        return final
    init_fields = initial.get("instance_fields")
    final_fields = final.get("instance_fields")
    if not isinstance(init_fields, dict) or not isinstance(final_fields, dict):
        return final
    changed: dict[str, Any] = {}
    for fname, ffinal in final_fields.items():
        finit = init_fields.get(fname)
        if finit is None:
            changed[fname] = ffinal
            continue
        if _deep_equal(finit, ffinal):
            continue
        changed[fname] = _minimize_to_changed_fields(finit, ffinal)
    result = dict(final)
    result["instance_fields"] = changed
    return result


def _real_arg_mutations(method_dict: dict) -> dict[int, Any]:
    initial_map = {int(idx): snap for idx, snap in method_dict.get("Args Initial", [])}
    result: dict[int, Any] = {}
    for idx_str, final_snap in method_dict.get("Args Final", []):
        idx = int(idx_str)
        initial_snap = initial_map.get(idx)
        if initial_snap is None:
            continue
        if _deep_equal(initial_snap, final_snap):
            continue
        if not _is_mutable_snapshot(final_snap):
            continue
        result[idx] = _minimize_to_changed_fields(initial_snap, final_snap)
    return result


def _has_real_side_effects(method_dict: dict) -> bool:
    return bool(
        method_dict.get("Static Fields Changed")
        or _real_receiver_mutation(method_dict)
        or _real_arg_mutations(method_dict)
    )


# ===========================================================================
# 生成 stub 赋值语句
# ===========================================================================

def _gen_stub_lines(
    method_dict: dict,
    call_args: list[str],
    receiver: str | None,
) -> list[str]:
    body: list[str] = []

    static_lines = update_static_fields(method_dict.get("Static Fields Changed", []))
    body.extend(static_lines)

    instance_final = method_dict.get("Instance Final")
    instance_initial = method_dict.get("Instance Initial")
    if instance_final and receiver and not _deep_equal(instance_initial, instance_final):
        minimized = _minimize_to_changed_fields(instance_initial, instance_final)
        mut_lines, _ = render_in_place_mutation(receiver, minimized)
        body.extend(mut_lines)

    for arg_idx, final_snap in _real_arg_mutations(method_dict).items():
        if arg_idx < len(call_args):
            mut_lines, _ = render_in_place_mutation(call_args[arg_idx], final_snap)
            body.extend(mut_lines)

    if not body:
        return []
    return [STUB_OPEN, *body, STUB_CLOSE]


def _dependency_has_instance_receiver(method_dict: dict) -> bool:
    return method_dict.get("Instance Initial") is not None


def _real_receiver_mutation(method_dict: dict) -> bool:
    initial = method_dict.get("Instance Initial")
    final = method_dict.get("Instance Final")
    return initial is not None and final is not None and not _deep_equal(initial, final)


def _blocker_detail(reason: str, method_dict: dict, *, line: int | None = None, source: str | None = None) -> dict:
    detail = {
        "reason": reason,
        "method_name": method_dict.get("method_name", ""),
        "occurrence_idx": method_dict.get("occurrence_idx"),
    }
    if line is not None:
        detail["line"] = line
    if source is not None:
        detail["source"] = source.strip()
    return detail


def _format_blocker_message(blockers: list[dict]) -> str:
    parts: list[str] = []
    for item in blockers:
        location = f":{item['line']}" if item.get("line") is not None else ""
        source = f" `{item['source']}`" if item.get("source") else ""
        parts.append(f"{item['reason']} {item.get('method_name', '')}{location}{source}".strip())
    return "; ".join(parts)


# ===========================================================================
# 一次性应用编辑
# ===========================================================================

def _is_return_call_line(line: str) -> bool:
    """判断该行是否形如 `return <expr>(...)` —— 此时桩必须插在该行之前。"""
    return bool(re.match(r'\s*return\s+\S', line))


def _apply_edits(
    original_lines: list[str],
    inserts_before: dict[int, list[str]],
    inserts_after: dict[int, list[str]],
) -> str:
    result: list[str] = []
    for i, line in enumerate(original_lines):
        indent = line[: len(line) - len(line.lstrip())]
        if i in inserts_before:
            for stub_line in inserts_before[i]:
                result.append(f"{indent}{stub_line}\n")
        result.append(line)
        if i in inserts_after:
            for stub_line in inserts_after[i]:
                result.append(f"{indent}{stub_line}\n")
    return "".join(result)


# ===========================================================================
# 主接口
# ===========================================================================

def analyze_replayability(test_cj_path: str, workflow_json_path: str, cj_main_dir: str) -> dict:
    """
    Analyze whether dependency mocking/side-effect replay is independently runnable.

    Strict blockers:
      - instance-method-dependency: a dependency call has a receiver instance snapshot,
        so current @On generation cannot bind it to the concrete receiver.
      - expression-side-effect-unreplayable: a side-effectful dependency call appears
        inside an expression where replay statements cannot preserve Java semantics.
    """
    blockers: list[dict] = []
    workflow: list[dict] = json.loads(Path(workflow_json_path).read_text(encoding="utf-8"))

    for method_dict in workflow:
        if _real_receiver_mutation(method_dict):
            blockers.append(_blocker_detail(INSTANCE_METHOD_DEPENDENCY, method_dict))

    focal_info = _extract_focal_info(test_cj_path)
    if not focal_info:
        return {"ok": not blockers, "blockers": blockers}
    class_name, method_name = focal_info

    src_file = _find_source_file(cj_main_dir, class_name)
    if not src_file:
        return {"ok": not blockers, "blockers": blockers}

    if not any(_has_real_side_effects(m) for m in workflow):
        return {"ok": not blockers, "blockers": blockers}

    lines = src_file.read_text(encoding="utf-8").splitlines(keepends=True)
    body_start, body_end = _find_method_body_range(lines, method_name)
    if body_start < 0:
        return {"ok": not blockers, "blockers": blockers}

    occ_ctr: dict[str, int] = {}

    for method_dict in workflow:
        mname = method_dict.get("method_name", "")
        short = mname.rpartition(".")[2]
        occ = occ_ctr.get(mname, 0)
        occ_ctr[mname] = occ + 1

        if not _has_real_side_effects(method_dict):
            continue

        call_line = _find_call_line(lines, body_start, body_end, short, occ)
        if call_line < 0:
            continue

        reason = _call_site_replay_blocker(lines[call_line], short)
        if reason:
            blockers.append(
                _blocker_detail(
                    reason,
                    method_dict,
                    line=call_line + 1,
                    source=lines[call_line],
                )
            )

    return {"ok": not blockers, "blockers": blockers}


def instrument(test_cj_path: str, workflow_json_path: str, cj_main_dir: str, *, structured: bool = False):
    """
    在 focal method 源文件中对每个有 side effect 的 callee 调用后插桩。
    默认返回被修改的源文件路径，无需插桩时返回 None；structured=True 时返回结构化状态。
    """
    analysis = analyze_replayability(test_cj_path, workflow_json_path, cj_main_dir)
    if analysis["blockers"]:
        result = {
            "status": "not-independent",
            "path": None,
            "blockers": analysis["blockers"],
            "message": _format_blocker_message(analysis["blockers"]),
        }
        return result if structured else None

    focal_info = _extract_focal_info(test_cj_path)
    if not focal_info:
        result = {"status": "no-op", "path": None, "blockers": [], "message": "missing focal call"}
        return result if structured else None
    class_name, method_name = focal_info

    src_file = _find_source_file(cj_main_dir, class_name)
    if not src_file:
        result = {"status": "no-op", "path": None, "blockers": [], "message": "source file not found"}
        return result if structured else None

    workflow: list[dict] = json.loads(Path(workflow_json_path).read_text(encoding="utf-8"))
    if not any(_has_real_side_effects(m) for m in workflow):
        result = {"status": "no-op", "path": None, "blockers": [], "message": "no side effects to instrument"}
        return result if structured else None

    lines = src_file.read_text(encoding="utf-8").splitlines(keepends=True)
    body_start, body_end = _find_method_body_range(lines, method_name)
    if body_start < 0:
        result = {"status": "no-op", "path": None, "blockers": [], "message": "focal method body not found"}
        return result if structured else None

    inserts_before: dict[int, list[str]] = {}
    inserts_after: dict[int, list[str]] = {}
    occ_ctr: dict[str, int] = {}

    for method_dict in workflow:
        mname = method_dict.get("method_name", "")
        short = mname.rpartition(".")[2]
        occ = occ_ctr.get(mname, 0)
        occ_ctr[mname] = occ + 1

        if not _has_real_side_effects(method_dict):
            continue

        call_line = _find_call_line(lines, body_start, body_end, short, occ)
        if call_line < 0:
            continue

        call_args = _parse_call_args(lines[call_line], short)
        receiver = _parse_receiver(lines[call_line], short)

        stub = _gen_stub_lines(method_dict, call_args, receiver)
        if stub:
            if _is_return_call_line(lines[call_line]):
                inserts_before.setdefault(call_line, []).extend(stub)
            else:
                inserts_after.setdefault(call_line, []).extend(stub)

    if not inserts_before and not inserts_after:
        result = {"status": "no-op", "path": None, "blockers": [], "message": "no side effects inserted"}
        return result if structured else None

    src_file.write_text(_apply_edits(lines, inserts_before, inserts_after), encoding="utf-8")
    result = {"status": "instrumented", "path": str(src_file), "blockers": [], "message": str(src_file)}
    return result if structured else str(src_file)


def deinstrument(*paths: str) -> None:
    """清除指定文件或目录下所有 .cj 文件中的 STUB 块。"""
    def _clean(p: Path) -> None:
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
        result, inside = [], False
        for line in lines:
            s = line.strip()
            if s == STUB_OPEN:
                inside = True
            elif inside:
                if s == STUB_CLOSE:
                    inside = False
            else:
                result.append(line)
        p.write_text("".join(result), encoding="utf-8")

    for path_str in paths:
        p = Path(path_str)
        if p.is_dir():
            for cj in p.rglob("*.cj"):
                _clean(cj)
        elif p.is_file():
            _clean(p)


# ===========================================================================
# CLI 入口
# ===========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="对 focal method 源文件插桩/去桩以回放 side effect")
    sub = parser.add_subparsers(dest="cmd")

    p_ins = sub.add_parser("instrument")
    p_ins.add_argument("test_cj")
    p_ins.add_argument("workflow_json")
    p_ins.add_argument("cj_main_dir")

    p_dei = sub.add_parser("deinstrument")
    p_dei.add_argument("paths", nargs="+")

    args = parser.parse_args()
    if args.cmd == "instrument":
        result = instrument(args.test_cj, args.workflow_json, args.cj_main_dir, structured=True)
        if result["status"] == "not-independent":
            print(f"[side_effect] not independent: {result['message']}")
        elif result["status"] == "instrumented":
            print(f"[side_effect] instrumented: {result['path']}")
        else:
            print(f"[side_effect] no side effects to instrument: {result['message']}")
    elif args.cmd == "deinstrument":
        deinstrument(*args.paths)
        print(f"[side_effect] deinstrumented: {args.paths}")
    else:
        parser.print_help()
