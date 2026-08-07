"""解析日志采集结果，提取待 mock 的调用链与副作用信息。"""

import json
import re
import sys



def _parse_json_fragment(fragment: str):
    try:
        return json.loads(fragment)
    except json.JSONDecodeError:
        return fragment


def process_side_effect(line: str) -> dict:
    """
    这一段负责把单行副作用日志拆成结构化字典，供后续 mock 生成直接消费。
    在 mock 过程中，它决定了返回值、异常、实例状态和静态字段变化会以什么数据形态被回放。
    """
    lhs, rhs = line.split(':', 1)
    method_name, modifier = lhs.split("[")
    modifier = modifier.strip()

    entry = {
        "method_name": method_name,
        "modifier": modifier
    }

    args_initial = extract_args(rhs, '(Arg\d+)( initial state: )')
    if args_initial:
        entry["Args Initial"] = args_initial

    args_final = extract_args(rhs, '(Arg\d+)( final state: )')
    if args_final:
        entry["Args Final"] = args_final

    for key in ["Return value", "Instance Initial", "Instance Final", "Static Fields Changed", "Static Fields Initial", "Exception thrown"]:
        key_match = re.search(f'{key}: (\{{.*\}}|\[.*\])', rhs)
        if key_match:
            value = match_json_structure(rhs[key_match.start(1):])
            if value:
                entry[key] = _parse_json_fragment(value)
    return entry

def extract_args(text, regex):
    """
    这个函数从日志文本里抽取参数快照，专门处理嵌套 JSON 不容易直接正则截断的问题。
    在 mock 过程中，它把每个参数的初始态和结束态单独提出来，后续才能精确回放和断言参数副作用。
    """
    args_initial = []

    for match in re.finditer(regex, text):
        arg_idx = match.group(1).split("Arg")[1]
        start = match.end()

        stack = []
        json_start = None
        in_quote = None
        escaped = False

        for i in range(start, len(text)):
            char = text[i]

            if escaped:
                escaped = False
                continue

            if char == "\\":
                escaped = True
                continue

            if char in "\"'" and not escaped:
                if in_quote is None:
                    in_quote = char
                elif in_quote == char:
                    in_quote = None

            elif char == "{" and in_quote is None:
                if not stack:
                    json_start = i
                stack.append(char)

            elif char == "}" and in_quote is None:
                if stack:
                    stack.pop()
                    if not stack:
                        args_initial.append((arg_idx, _parse_json_fragment(text[json_start:i+1])))
                        break

    return args_initial

def match_json_structure(text):
    """
    这个函数用于从一段混合文本中截出第一个完整的 JSON 或数组结构。
    在 mock 过程中，它保证日志里记录的返回值或字段变更不会因为嵌套括号被截断，从而能被正确反序列化。
    """
    stack = []
    start_index = None
    in_quote = None
    escape = False

    for i, char in enumerate(text):
        if escape:
            escape = False
            continue

        if char == "\\":
            escape = True
            continue

        if char in "\"'":
            if in_quote is None:
                in_quote = char
            elif in_quote == char:
                in_quote = None
            continue

        if in_quote:
            continue

        if char in "{[":
            if not stack:
                start_index = i
            stack.append(char)
        elif char in "}]":
            if stack:
                stack.pop()
                if not stack:
                    return text[start_index:i+1]

    return None


def match_nested_braces(s: str) -> str:
    """
    这个函数返回从开头开始的完整花括号片段，适合处理只关心对象包围边界的场景。
    在 mock 过程中，它为后续解析提供一个保守的结构边界，避免把相邻日志内容错误吞进去。
    """
    stack = []
    for i, char in enumerate(s):
        if char == '{':
            stack.append(char)
        elif char == '}':
            stack.pop()
        if not stack:
            return s[:i+1]
    return None

def get_side_effect_and_end_line(start_line_index: int, lines: list) -> list:
    """
    这个函数从某个调用块的开始位置向后扫描，找到对应的结束位置和最终副作用摘要。
    在 mock 过程中，它把一次方法调用的作用域切干净，后续才能按调用块生成一组稳定的 mock 行为。
    """
    counter = 1
    for line_index in range(start_line_index + 1, len(lines)):
        line = lines[line_index].strip()
        if line.startswith("==========START OF"):
            counter += 1
        elif line.startswith("==========END OF"):
            counter -= 1
            if counter == 0:
                return [process_side_effect(lines[line_index - 1]), line_index]

def _find_top_level_blocks(lines: list) -> list:
    """返回日志中所有深度为 0 的 START OF 块。
    每项为 (start_line_index, depth1_nested_count)。
    """
    depth = 0
    top_level_blocks = []
    current_top = None
    current_nested = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("==========START OF"):
            if depth == 0:
                current_top = i
                current_nested = 0
            elif depth == 1:
                current_nested += 1
            depth += 1
        elif stripped.startswith("==========END OF"):
            depth -= 1
            if depth == 0 and current_top is not None:
                top_level_blocks.append((current_top, current_nested))
                current_top = None
    return top_level_blocks


def parse_logs(input_log_file: str) -> list:
    """日志解析入口：一个日志文件（= 一个 @Test）只生成一个 workflow。

    - 若存在有内部调用链的深度-0 方法，取嵌套调用数最多的那个作为 focal，
      其直接被调方法由 @On 桩覆盖；
    - 若所有深度-0 方法均无内部调用（简单方法序列），将它们全部标记为 focal
      顺序放入同一 workflow，直接依次调用。
    """
    with open(input_log_file, 'r') as file:
        lines = file.readlines()

    top_level_blocks = _find_top_level_blocks(lines)
    if not top_level_blocks:
        return []

    has_nested = [(s, n) for s, n in top_level_blocks if n > 0]

    if has_nested:
        # focal = 直接嵌套调用数最多的深度-0 方法
        focal_start, _ = max(has_nested, key=lambda x: x[1])
        methods_to_mock: list = []
        mock_indices: dict = {}
        retrieve_mocking_info_for_one_method(methods_to_mock, mock_indices, 0, len(lines) - 1, focal_start, lines)
        return [methods_to_mock]
    else:
        # 所有方法均无嵌套（如纯静态调用序列）：全部作为 focal 合并进一个 workflow
        combined: list = []
        mock_indices: dict = {}
        for start, _ in top_level_blocks:
            methods_to_mock = []
            retrieve_mocking_info_for_one_method(methods_to_mock, mock_indices, 0, len(lines) - 1, start, lines)
            combined.extend(methods_to_mock)
        return [combined]
            


def retrieve_mocking_info_for_one_method(methods_to_mock: list, mock_indices: dict, start: int, end: int, method_index: int, lines: list) -> None:
    """
    这个函数定位焦点方法所在的调用块，并把它标记成需要真实执行的 skip 节点。
    在 mock 过程中，它负责确定“哪一个调用保留原始行为、哪些下游调用改成 mock”，这是拆分测试的核心边界。
    """
    chunk_start = start
    while chunk_start <= end:
        line = lines[chunk_start].strip()
        if line.startswith("==========START OF"):
            method_name = line.split("==========START OF ")[1].split("==========")[0]
            chunk_side_effect, chunk_end = get_side_effect_and_end_line(chunk_start, lines)
            if chunk_start == method_index:
                if not method_name in mock_indices:
                    mock_indices[method_name] = 0
                mock_indices[method_name] += 1
                modifier = lines[chunk_end - 1].split(':', 1)[0].split("[")[1].strip()
                chunk_side_effect.update({
                    "occurrence_idx": mock_indices[method_name],
                    "note": "skip",
                    "modifier": modifier
                })
                methods_to_mock.append(chunk_side_effect)
                find_mocks_in_call_chain(methods_to_mock, mock_indices, chunk_start + 1, chunk_end - 1, lines)
                break
            elif chunk_end < method_index:
                chunk_start = chunk_end + 1
            else:
                chunk_start += 1
        else:
            break

def find_mocks_in_call_chain(methods_to_mock: list, mock_indices: dict, start: int, end: int, lines: list) -> None:
    """
    这个函数遍历焦点方法内部的调用链，把所有可替换调用按出现次序登记下来。
    在 mock 过程中，它决定 patch 的顺序和 occurrence 索引，避免同名方法多次出现时 mock 错位。
    """
    chunk_start = start
    while chunk_start <= end:
        line = lines[chunk_start].strip()
        if line.startswith("==========START OF"):
            method_name = line.split("==========START OF ")[1].split("==========")[0]
            chunk_side_effect, chunk_end = get_side_effect_and_end_line(chunk_start, lines)
            if method_name not in mock_indices:
                mock_indices[method_name] = -1
            mock_indices[method_name] += 1
            chunk_side_effect["occurrence_idx"] = mock_indices[method_name]
            methods_to_mock.append(chunk_side_effect)
            chunk_start = chunk_end + 1
        else:
            break





             


if __name__ == "__main__":
    input_log_file = sys.argv[1]
    result = parse_logs(input_log_file)
    import pprint
    pprint.pprint(result)
