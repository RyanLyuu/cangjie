#!/usr/bin/env python3
"""通过直接修改仓颉源码的访问修饰符，为 mock 测试开放私有成员。

替代 add_macro.py 的宏展开做法，改为：
  apply   — 把 private/protected 字段改成 public var，私有零参构造器改成 public；
            在每处修改行的正上方插入还原桩：// CHANGE_MODE: <原始修饰关键字序列>
  restore — 根据桩注释把修改回退到原始修饰符，然后移除桩行

优点：
  - 不依赖宏包；
  - 测试代码可直接用 obj.fieldName 访问字段，无需调用 __mockGet* 访问器；
  - 桩直接嵌在源码中，无需外部 manifest。
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

# ── 桩格式 ─────────────────────────────────────────────────────────────────────
MARKER = "// CHANGE_MODE:"
MARKER_LINE_RE = re.compile(
    r"^(?P<indent>\s*)" + re.escape(MARKER) + r"\s+(?P<orig>.+?)\s*$"
)

# ── 字段匹配：private/protected [static] (let|var) name ... ───────────────────
FIELD_RE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<visibility>private|protected|public)\s+"
    r"(?P<static>static\s+)?"
    r"(?P<kind>let|var)\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?P<rest>.*)$"
)

# ── 零参构造器：private/protected [const] init() ... ──────────────────────────
NO_ARG_INIT_RE = re.compile(
    r"^(?P<indent>\s*)"
    r"(?P<visibility>private|protected)\s+"
    r"(?P<const>const\s+)?"
    r"init\s*\(\s*\)"
    r"(?P<rest>.*)$"
)

# ── 恢复时用于定位被改行的前缀 ───────────────────────────────────────────────
# apply 后的字段行形如:  <indent>public [static] var <name>...
# apply 后的 init 行形如: <indent>public [const] init()...
APPLIED_FIELD_RE = re.compile(
    r"^(?P<indent>\s*)public\s+(?P<static>static\s+)?var\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)(?P<rest>.*)$"
)
APPLIED_INIT_RE = re.compile(
    r"^(?P<indent>\s*)public\s+(?P<const>const\s+)?init\s*\(\s*\)(?P<rest>.*)$"
)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _iter_target_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*.cj") if p.is_file())


def _find_matching_brace(text: str, open_index: int) -> int:
    """返回与 open_index 处 '{' 配对的 '}' 的索引。"""
    depth = 0
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_rune = False
    escape = False

    i = open_index
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if in_rune:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_rune = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch == "'":
            in_rune = True
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError(f"Unmatched '{{' at index {open_index}")


CLASS_DECL_RE = re.compile(
    r"(?m)^(?P<indent>\s*)(?:(?:pub|public|open|abstract|sealed|internal|private|protected)\s+)*"
    r"class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b[^{]*\{"
)


def _class_body_range(text: str, class_name: str | None) -> list[tuple[int, int]]:
    """返回所有（或指定）类的 body 范围列表，格式为 (body_start, body_end) 不含大括号本身。"""
    ranges: list[tuple[int, int]] = []
    for m in CLASS_DECL_RE.finditer(text):
        if class_name is not None and m.group("name") != class_name:
            continue
        brace_open = text.find("{", m.start())
        if brace_open == -1:
            continue
        brace_close = _find_matching_brace(text, brace_open)
        ranges.append((brace_open + 1, brace_close))
    return ranges


def _position_in_any_range(pos: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in ranges)


# ── apply 逻辑 ────────────────────────────────────────────────────────────────

def _orig_token_for_field(m: re.Match) -> str:
    """把字段匹配结果编码成原始修饰关键字序列，例如 'private let' 或 'protected static var'。"""
    parts = [m.group("visibility")]
    if m.group("static"):
        parts.append("static")
    parts.append(m.group("kind"))
    return " ".join(parts)


def _orig_token_for_init(m: re.Match) -> str:
    """把 init 匹配结果编码成原始修饰关键字序列，例如 'private init' 或 'protected const init'。"""
    parts = [m.group("visibility")]
    if m.group("const"):
        parts.append("const")
    parts.append("init")
    return " ".join(parts)


def _apply_lines(
    lines: list[str],
    ranges: list[tuple[int, int]] | None,
    original_text: str,
) -> tuple[list[str], list[str]]:
    """对 lines 逐行尝试 apply 变换。

    ranges 为 None 时处理整个文件；否则只处理在 ranges 内的行。
    返回 (new_lines, summaries)。
    """
    summaries: list[str] = []
    result: list[str] = []
    # 把字符偏移量的 ranges 转成行号范围更方便；但我们直接用原始偏移量，
    # 通过逐行累积当前字符位置来判断。
    char_pos = 0
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")
        line_start = char_pos
        char_pos += len(raw)

        # 跳过已有桩的行
        if MARKER in line:
            result.append(raw)
            i += 1
            continue

        # 判断是否在目标范围内
        if ranges is not None and not _position_in_any_range(line_start, ranges):
            result.append(raw)
            i += 1
            continue

        eol = "\n" if raw.endswith("\n") else ""

        # 尝试字段匹配
        fm = FIELD_RE.match(line)
        if fm:
            # public var 本来就既可见又可写，无需改动
            if fm.group("visibility") == "public" and fm.group("kind") == "var":
                result.append(raw)
                i += 1
                continue
            orig_token = _orig_token_for_field(fm)
            static_part = fm.group("static") or ""
            new_line = (
                f"{fm.group('indent')}public {static_part}var "
                f"{fm.group('name')}{fm.group('rest')}{eol}"
            )
            marker_line = f"{fm.group('indent')}{MARKER} {orig_token}{eol}"
            result.append(marker_line)
            result.append(new_line)
            summaries.append(
                f"  field  {fm.group('name')!r}: {orig_token} → public {static_part}var"
            )
            i += 1
            continue

        # 尝试零参 init 匹配
        im = NO_ARG_INIT_RE.match(line)
        if im:
            orig_token = _orig_token_for_init(im)
            const_part = im.group("const") or ""
            new_line = (
                f"{im.group('indent')}public {const_part}init(){im.group('rest')}{eol}"
            )
            marker_line = f"{im.group('indent')}{MARKER} {orig_token}{eol}"
            result.append(marker_line)
            result.append(new_line)
            summaries.append(f"  init   (zero-arg): {orig_token} → public {const_part}init")
            i += 1
            continue

        result.append(raw)
        i += 1

    return result, summaries


# ── restore 逻辑 ──────────────────────────────────────────────────────────────

def _restore_lines(lines: list[str]) -> tuple[list[str], list[str]]:
    """扫描桩注释并还原被修改行。返回 (new_lines, summaries)。"""
    summaries: list[str] = []
    result: list[str] = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        mm = MARKER_LINE_RE.match(raw.rstrip("\n"))
        if mm is None:
            result.append(raw)
            i += 1
            continue

        orig_token = mm.group("orig")    # e.g. "private let", "protected static var"
        indent = mm.group("indent")
        orig_parts = orig_token.split()  # ["private","let"] / ["protected","static","var"] / ["private","init"]

        # 找下一行（被改行）
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        if j >= len(lines):
            # 桩后没有内容，保留桩行原样（安全兜底）
            result.append(raw)
            i += 1
            continue

        target_raw = lines[j]
        target = target_raw.rstrip("\n")
        eol = "\n" if target_raw.endswith("\n") else ""

        restored: str | None = None

        if "init" in orig_parts:
            # 还原 init 行：public [const] init() → <orig> init()
            aim = APPLIED_INIT_RE.match(target)
            if aim:
                const_part = ("const " if "const" in orig_parts else "")
                visibility = orig_parts[0]
                restored = f"{indent}{visibility} {const_part}init(){aim.group('rest')}{eol}"
                summaries.append(f"  init   (zero-arg): public → {orig_token}")
        else:
            # 还原字段行：public [static] var name... → <orig> name...
            afm = APPLIED_FIELD_RE.match(target)
            if afm:
                visibility = orig_parts[0]
                kind = orig_parts[-1]  # 最后一个 token 是 let 或 var
                static_part = "static " if "static" in orig_parts else ""
                restored = (
                    f"{indent}{visibility} {static_part}{kind} "
                    f"{afm.group('name')}{afm.group('rest')}{eol}"
                )
                summaries.append(
                    f"  field  {afm.group('name')!r}: public → {orig_token}"
                )

        if restored is not None:
            result.append(restored)     # 还原后的声明行
            # 跳过桩行(i)和被改行(j)之间的空行（通常没有）以及被改行本身
            for blank_idx in range(i + 1, j):
                pass  # 丢弃桩和被改行之间的空行（理论上不存在）
            i = j + 1
        else:
            # 无法匹配下一行，保留桩行（安全兜底）
            result.append(raw)
            i += 1

    return result, summaries


# ── 文件级入口 ────────────────────────────────────────────────────────────────

def _apply_file(path: Path, class_name: str | None) -> list[str]:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    ranges: list[tuple[int, int]] | None = None
    if class_name is not None:
        ranges = _class_body_range(original, class_name)
        if not ranges:
            return [f"{path}: class {class_name!r} not found, skipped"]

    new_lines, field_summaries = _apply_lines(lines, ranges, original)
    new_text = "".join(new_lines)

    if new_text == original:
        return [f"{path}: nothing to change"]

    path.write_text(new_text, encoding="utf-8")
    result = [f"{path}: applied {len(field_summaries)} change(s)"]
    result.extend(field_summaries)
    return result


def _restore_file(path: Path) -> list[str]:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)

    new_lines, summaries = _restore_lines(lines)
    new_text = "".join(new_lines)

    if new_text == original:
        return [f"{path}: no CHANGE_MODE markers found"]

    path.write_text(new_text, encoding="utf-8")
    result = [f"{path}: restored {len(summaries)} change(s)"]
    result.extend(summaries)
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def _run_apply(target: Path, class_name: str | None) -> int:
    all_summaries: list[str] = []
    for path in _iter_target_files(target):
        all_summaries.extend(_apply_file(path, class_name))
    for line in all_summaries:
        print(line)
    return 0


def _run_restore(target: Path) -> int:
    all_summaries: list[str] = []
    for path in _iter_target_files(target):
        all_summaries.extend(_restore_file(path))
    for line in all_summaries:
        print(line)
    return 0


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="直接修改仓颉源码修饰符，为 mock 测试前后开放/还原私有成员。"
    )
    parser.add_argument("action", choices=("apply", "restore"))
    parser.add_argument("target", help=".cj 文件或递归扫描的目录")
    parser.add_argument(
        "--class",
        dest="class_name",
        default=None,
        help="只处理指定类（apply 时有效；restore 全文件扫描桩）",
    )
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    target = Path(args.target)
    if not target.exists():
        print(f"Target not found: {target}", file=sys.stderr)
        return 2
    if args.action == "apply":
        return _run_apply(target, args.class_name)
    return _run_restore(target)


if __name__ == "__main__":
    raise SystemExit(main())
