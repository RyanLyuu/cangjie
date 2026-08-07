"""把日志里的 JSON 快照转换成仓颉 mock / unittest 可直接拼接的代码片段。

这版是对早期原型的补全版，目标不是在 Python 里执行仓颉对象，
而是把 Java 日志快照尽量完整地翻译成：
1. 仓颉侧对象/集合/流的构造代码；
2. 副作用回放代码；
3. 断言与测试骨架代码；
4. 运行时辅助函数源码。

注意：
- 该文件输出的是“仓颉代码字符串”，不是在 Python 中直接执行的 mock 引擎。
- 字段可见性由 change_mode.py 在测试前统一改为 public var，生成代码始终使用直接字段访问。
- 该实现优先选择仓颉官方文档中明确出现过的写法，例如：
  `ArrayList<T>() / ArrayList<T>(capacity)`、`HashMap<K, V>()`、`HashSet<T>()`、
  `ByteArrayStream()`、`StringReader(stream)`、`@Test/@TestCase/@Assert/@Expect`。

当前仍待解决的问题：
1. `StringWriter` 还没有可靠的“内容比较 + 原地重置”方案；当前缺少一个稳定的公共 API，
   能从现有 writer 反取并替换其绑定输出缓冲区。
2. `StringReader` 目前支持内容比较，但还不能把一个“已存在的 reader 实例”原地更新到指定快照；
   现有 `std.io` API 可读/可 seek，但不足以安全替换其底层输入源。
3. `ByteArrayStream`、`Array<T>` 这类状态型对象/数组快照还没有统一的原地 mutation 回放实现。
4. dependency 的 receiver mutation 仍未自动回放；当前只对“参数副作用”和“静态字段副作用”做了
   一部分 best-effort 支持。
5. 复杂对象参数在 `@On(...)` 签名里已改用 `argThat { arg: Type => <字段比较> }` 语义匹配；
   对于需要在 action lambda 中回放参数变更的场景，应进一步改用 `argThat(captor, filter)` 捕获参数。
6. 构造器、`private` dependency、实例成员 dependency 的自动 stub 仍主要受限于仓颉 mock 框架
   和静态编译边界；这类问题不只是 helper 细节缺失，还涉及语言/框架层能力差异。

这些问题从本质上要解决的是：
1. 让日志里记录的“状态型资源”不仅能被构造出来，还能在测试过程中被精确校验和复原，
   例如 reader / writer / byte stream 的内容、位置和绑定关系。
2. 让 dependency 的行为不只停留在“返回什么/抛什么”，而是能完整回放它对现有运行时对象施加的状态变化。
3. 让参数、副作用接收者、静态字段这三类可观察状态都能被统一表达为“可重放、可断言”的测试步骤，
   而不是只覆盖其中一部分。
4. 让 mock 分派能够稳定地区分“哪一次调用对应哪份日志记录”，尤其是在复杂对象参数、重复调用、
   别名引用和相同签名多次触发的情况下避免串桩。
5. 让快照到测试代码的映射既尽量忠实于日志语义，又不过度绑定具体实现细节，
   避免为了追求完全一致而生成不可编译、不可维护或过度脆弱的测试。
6. 让当前 `.workflow.json` 里保留下来的 spec-only 信息最终也能逐步收敛为可执行测试能力，
   而不是长期停留在“只记录、不回放”的状态。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
import json
import re

from reflection import (
    render_ioc_new_expr,
    render_runtime_support as render_reflection_runtime_support,
    required_imports as reflection_required_imports,
)


# 地址 -> 仓颉侧表达式/变量名。
reference_dict: dict[str, str] = {}

# reader/writer 变量名 -> 底层 buffer 变量名（用于原地重置）
_stream_buffer_map: dict[str, str] = {}

def _get_stream_buffer(var_name: str) -> str | None:
    """获取指定 reader/writer 变量的底层 buffer 变量名。"""
    return _stream_buffer_map.get(var_name)

def _set_stream_buffer(stream_var: str, buffer_var: str) -> None:
    """注册 reader/writer 与其底层 buffer 的映射关系。"""
    _stream_buffer_map[stream_var] = buffer_var

def clear_stream_buffer_map() -> None:
    """清空 stream->buffer 映射缓存，避免不同 workflow 之间串用。"""
    _stream_buffer_map.clear()



# -----------------------------
# Java -> Cangjie 类型映射
# -----------------------------
# 说明：
# 1. 能直接落到仓颉标准类型/标准库类型的，映射成真实类型。
# 2. 容量/精度不安全的类型（如 BigInteger / BigDecimal）保守降级为 String snapshot。
# 3. Java 输入输出流在仓颉里优先映射到 std.io 提供的真实流类型或字符串/字节快照。
# 4. Optional 家族统一交给 Option 分支处理。
# 5. HashMap/HashSet 的 key/element 类型在仓颉中必须满足 Hashable & Equatable，
#    Any 不满足这些约束。当需要带泛型参数的 HashMap<AnyHashable, V> / HashSet<AnyHashable>
#    时，请使用 <project>.runtime.AnyHashable（参见 AnyHashable.cj）。
#    本映射表仅记录基类名（不含泛型），泛型约束在 get_cangjie_type() 中自动处理。
type_map = {
    # 整数
    # Java int/Integer 在仓颉翻译端统一用 Int64（Cangjie 默认整数宽度），
    # byte/short 仍保留窄类型。
    "java.lang.Byte": "Int8",
    "java.lang.Short": "Int16",
    "java.lang.Integer": "Int64",
    "java.lang.Long": "Int64",
    "byte": "Int8",
    "short": "Int16",
    "int": "Int64",
    "long": "Int64",

    # 浮点
    "java.lang.Float": "Float32",
    "java.lang.Double": "Float64",
    "float": "Float32",
    "double": "Float64",

    # 基础类型
    "java.lang.Boolean": "Bool",
    "boolean": "Bool",
    "java.lang.String": "String",
    "java.lang.CharSequence": "String",
    "java.lang.Character": "Rune",
    "char": "Rune",
    "java.lang.Object": "Any",
    "java.lang.Class": "Type",

    # 异常
    "java.lang.Throwable": "Exception",
    "java.lang.Exception": "Exception",
    "java.lang.RuntimeException": "Exception",
    "java.lang.IllegalArgumentException": "IllegalArgumentException",
    "java.lang.IllegalStateException": "IllegalStateException",
    "java.lang.AssertionError": "AssertionError",
    "java.lang.NumberFormatException": "NumberFormatException",
    "java.io.FileNotFoundException": "Exception",
    "java.io.IOException": "Exception",
    "java.io.UnsupportedEncodingException": "IllegalArgumentException",
    "java.lang.IndexOutOfBoundsException": "IndexOutOfBoundsException",
    "java.util.ArrayIndexOutOfBoundsException": "IndexOutOfBoundsException",
    "java.lang.UnsupportedOperationException": "UnsupportedOperationException",
    "java.lang.ClassNotFoundException": "Exception",
    "java.lang.ClassCastException": "TypeCastException",
    "java.lang.CloneNotSupportedException": "Exception",
    "java.net.MalformedURLException": "IllegalArgumentException",
    "java.net.URISyntaxException": "IllegalArgumentException",
    "java.nio.charset.UnsupportedCharsetException": "IllegalArgumentException",

    # 集合
    "java.util.ArrayList": "ArrayList",
    "java.util.LinkedList": "ArrayList",
    "java.util.Vector": "ArrayList",
    "java.util.Arrays$ArrayList": "ArrayList",
    "java.util.Collections$SingletonList": "ArrayList",
    "java.util.Collections$EmptyList": "ArrayList",
    "java.util.RandomAccessSubList": "ArrayList",
    "java.util.HashSet": "HashSet",
    "java.util.Collections$SingletonSet": "HashSet",
    "java.util.HashMap": "HashMap",
    "java.util.LinkedHashMap": "HashMap",
    "java.util.TreeMap": "HashMap",
    "java.util.Map": "HashMap",
    "java.util.Properties": "HashMap",
    # Java iterator / enumeration / stream 在日志中通常更接近“已观测到的序列快照”
    # 这里统一映射为 ArrayList snapshot。
    "java.util.Iterator": "ArrayList",
    "java.util.ListIterator": "ArrayList",
    "java.util.Enumeration": "ArrayList",
    "java.util.Scanner": "ArrayList",
    "java.util.stream.Stream": "ArrayList",
    "java.util.Collections$UnmodifiableRandomAccessList": "ArrayList",
    "java.util.LinkedHashMap$LinkedValues": "ArrayList",
    "java.util.LinkedHashMap$LinkedKeySet": "ArrayList",

    # Option
    "java.util.Optional": "Option",
    "java.util.OptionalInt": "Option",
    "java.util.OptionalLong": "Option",
    "java.util.OptionalDouble": "Option",

    # 文本 / 编码 / 正则 / 路径 / 时间
    "java.nio.charset.Charset": "String",
    "java.util.Locale": "String",
    "java.util.regex.Pattern": "Regex",
    "java.util.regex.Matcher": "Regex",
    "java.net.URL": "URL",
    "java.net.URI": "URL",
    "java.nio.file.Path": "Path",
    "java.io.File": "Path",
    "java.time.Duration": "Duration",
    "java.time.Instant": "DateTime",
    "java.time.LocalDateTime": "DateTime",
    "java.time.LocalDate": "DateTime",
    "java.time.LocalTime": "DateTime",
    "java.time.OffsetDateTime": "DateTime",
    "java.time.ZonedDateTime": "DateTime",
    "java.util.TimeZone": "TimeZone",
    "sun.util.calendar.ZoneInfo": "TimeZone",
    "java.util.Calendar": "DateTime",
    "java.util.Date": "DateTime",

    # I/O
    "java.io.ByteArrayInputStream": "ByteBuffer",
    "java.io.ByteArrayOutputStream": "ByteBuffer",
    "java.io.StringReader": "StringReader",
    "java.io.StringWriter": "StringWriter",
    "java.lang.StringBuilder": "String",
    "java.lang.StringBuffer": "String",
    "java.io.BufferedReader": "StringReader",
    "java.io.BufferedWriter": "StringWriter",
    "java.io.InputStreamReader": "StringReader",
    "java.io.OutputStreamWriter": "StringWriter",
    "java.io.InputStream": "InputStream",
    "java.io.OutputStream": "OutputStream",
    "java.io.BufferedInputStream": "ByteArrayStream",
    "java.io.BufferedOutputStream": "ByteArrayStream",
    "java.io.FilterInputStream": "ByteArrayStream",
    "java.io.FilterOutputStream": "ByteArrayStream",
    "java.io.PipedInputStream": "ByteArrayStream",
    "java.io.PipedOutputStream": "ByteArrayStream",
    "java.io.PipedReader": "StringReader",
    "java.io.PipedWriter": "StringWriter",
    "java.io.PrintStream": "ByteArrayStream",
    "java.io.PrintWriter": "StringWriter",
    "java.lang.Appendable": "String",

    # 其它
    "java.util.zip.CRC32": "CRC32",
    "java.util.concurrent.TimeUnit": "Duration",
    "java.time.temporal.ChronoUnit": "Duration",
    "java.lang.reflect.Modifier": "String",
    "java.lang.reflect.Method": "Any",
    "java.lang.reflect.Constructor": "Any",
    "java.util.Comparator": "Any",
    "java.util.concurrent.ThreadFactory": "Any",
    "java.util.concurrent.Executors$DefaultThreadFactory": "Any",
    "java.util.concurrent.atomic.AtomicInteger": "Int64",
    "java.util.concurrent.atomic.AtomicLong": "Int64",
    "java.util.concurrent.atomic.AtomicBoolean": "Bool",
    "java.math.BigInteger": "Int64",
    "java.math.BigDecimal": "Float64",
    "java.util.BitSet": "ArrayList",
    "java.lang.Number": "Float64",
    "RuntimeException": "Exception",
    "java.nio.CharBuffer": "Array<Rune>",
    "java.nio.HeapCharBuffer": "Array<Rune>",
    "java.nio.ByteBuffer": "ByteBuffer",
    "java.nio.HeapByteBuffer": "ByteBuffer",
}


charset_map = {
    "UTF-8": "utf-8",
    "UTF8": "utf-8",
    "UTF-16": "utf-16",
    "UTF-16BE": "utf-16-be",
    "UTF-16LE": "utf-16-le",
    "US-ASCII": "ascii",
    "ISO-8859-1": "latin1",
    "ISO-8859-2": "iso-8859-2",
    "ISO-8859-15": "iso-8859-15",
    "windows-1252": "cp1252",
    "windows-1251": "cp1251",
    "Big5": "big5",
    "GB2312": "gb2312",
    "GB18030": "gb18030",
    "Shift_JIS": "shift_jis",
    "EUC-JP": "euc_jp",
    "KOI8-R": "koi8_r",
    "ISO-2022-JP": "iso2022_jp",
}


java_to_cangjie_locale = {
    "en": "en_US",
    "en_US": "en_US",
    "en_GB": "en_GB",
    "fr": "fr_FR",
    "fr_FR": "fr_FR",
    "de": "de_DE",
    "de_DE": "de_DE",
    "es": "es_ES",
    "es_ES": "es_ES",
    "it": "it_IT",
    "it_IT": "it_IT",
    "pt": "pt_PT",
    "pt_PT": "pt_PT",
    "pt_BR": "pt_BR",
    "zh": "zh_CN",
    "zh_CN": "zh_CN",
    "zh_TW": "zh_TW",
    "ja": "ja_JP",
    "ja_JP": "ja_JP",
    "ko": "ko_KR",
    "ko_KR": "ko_KR",
    "ru": "ru_RU",
    "ru_RU": "ru_RU",
    "ar": "ar_EG",
    "ar_EG": "ar_EG",
    "hi": "hi_IN",
    "hi_IN": "hi_IN",
}


DIRECT_LITERAL_TYPES = {
    "Int8", "Int16", "Int32", "Int64",
    "Float32", "Float64",
    "Bool", "String", "Rune", "Type",
}

DIRECT_CONTAINER_TYPES = {
    "ArrayList", "HashSet", "HashMap", "Option", "CRC32",
}

STREAM_TYPES = {
    "ByteBuffer", "ByteArrayStream", "StringReader", "StringWriter", "InputStream", "OutputStream",
}

TIME_JAVA_TYPES = {
    "java.time.Duration",
    "java.time.Instant",
    "java.time.LocalDateTime",
    "java.time.LocalDate",
    "java.time.LocalTime",
    "java.time.OffsetDateTime",
    "java.time.ZonedDateTime",
    "java.util.Date",
    "java.util.Calendar",
    "java.util.TimeZone",
    "sun.util.calendar.ZoneInfo",
}

EXCEPTION_TYPES = {
    "Exception",
    "IllegalArgumentException",
    "IllegalStateException",
    "AssertionError",
    "NumberFormatException",
    "UnsupportedOperationException",
    "IndexOutOfBoundsException",
    "TypeCastException",
}


def clear_reference_dict():
    """清空地址缓存，避免不同 workflow 之间串用相同变量名。"""
    global reference_dict
    reference_dict.clear()
    clear_stream_buffer_map()


def _extract_class_name(dotted: str) -> str:
    """从 Java 全限定名中提取简单类名（最后一个大写开头的片段）。
    e.g. com.example.minimal.App.MutableBox → MutableBox
    """
    parts = dotted.split(".")
    # find rightmost uppercase-starting part
    for part in reversed(parts):
        if part and part[0].isupper():
            return part
    return parts[-1]


# mock_helper 的 type_map 优先（保特化语义），漏的 JDK 类型再查 java_base_type_map。
_JAVA_BASE_MAP_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "java" / "type_resolution" / "java_base_type_map.json"
)


def _normalize_type_map_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        mapped = value.get("mapping", "")
        return mapped if isinstance(mapped, str) else ""
    return ""


def _simple_type_name(type_name: str) -> str:
    return type_name.split(".")[-1] if "." in type_name else type_name


def _load_java_base_type_map() -> dict[str, str]:
    raw_map = json.loads(_JAVA_BASE_MAP_PATH.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    simple_aliases: dict[str, set[str]] = {}

    for key, value in raw_map.items():
        mapped = _normalize_type_map_value(value)
        if not mapped:
            continue
        result[key] = mapped
        if "." in key:
            simple_aliases.setdefault(_simple_type_name(key), set()).add(mapped)

    for alias, mappings in simple_aliases.items():
        if len(mappings) == 1 and alias not in result and alias not in type_map:
            result[alias] = next(iter(mappings))
    return result


try:
    _java_base_type_map = _load_java_base_type_map()
except FileNotFoundError:
    _java_base_type_map = {}


def _strip_generics(value: str) -> str:
    return re.sub(r"<.*$", "", value).strip()


def _type_name(value: Any) -> str | None:
    """Extract a Java type/class name from string or nested snapshot metadata."""
    if isinstance(value, str):
        return value
    if not isinstance(value, dict):
        return None

    for key in ("type", "class_name", "owner", "owner_type", "declaring_class", "declaring_type", "value"):
        nested = value.get(key)
        if nested is value:
            continue
        resolved = _type_name(nested)
        if resolved:
            return resolved
    return None


def retrieve_from_type_map(class_name: Any, default: Any = None) -> str | None:
    """把日志里的 Java 类型翻译为仓颉类型/类路径。"""
    class_name = _type_name(class_name)
    default = _type_name(default)
    if not class_name:
        return default
    if class_name.startswith("src.main."):
        stripped = class_name[len("src.main."):].replace("$", ".")
        return _extract_class_name(stripped)
    if class_name.startswith("src.test."):
        stripped = class_name[len("src.test."):].replace("$", ".")
        return _extract_class_name(stripped)
    if class_name.startswith("src."):
        stripped = class_name[len("src."):].replace("$", ".")
        return _extract_class_name(stripped)
    if class_name.endswith("[]"):
        element_type = retrieve_from_type_map(class_name[:-2], "Any")
        return f"Array<{element_type}>"
    if class_name in type_map:
        return type_map[class_name]
    if class_name in _java_base_type_map:
        return _strip_generics(_java_base_type_map[class_name])
    return default if default is not None else class_name


def escape_cangjie_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def escape_cangjie_rune(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    escaped = escaped.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return escaped


def sanitize_identifier(name: str) -> str:
    cleaned = name.split("_HIDDEN_FIELD___")[0]
    if re.fullmatch(r"[A-Za-z_]\w*", cleaned):
        return cleaned
    return f"`{cleaned}`"


def _big_integer_literal_or_string(node: dict[str, Any]) -> str:
    raw_value = str(node.get("value", "0") or "0").strip()
    try:
        value = int(raw_value)
    except ValueError:
        return "0i64"

    if -(2 ** 63) <= value <= (2 ** 63 - 1):
        return _encode_integer_literal(value, "Int64")

    return "0i64"


def _big_decimal_literal_or_string(node: dict[str, Any]) -> str:
    raw_value = str(node.get("value", "0") or "0").strip()
    try:
        value = float(raw_value)
    except ValueError:
        return "0.0f64"

    if value == float("inf") or value == float("-inf"):
        return "0.0f64"

    return _encode_float_literal(value, "Float64")


def _snapshot_note_contains_synthetic(node: Any) -> bool:
    if not isinstance(node, dict):
        return False
    note = node.get("note")
    return isinstance(note, str) and "synthetic" in note.lower()


def is_synthetic_owner(owner_name: Any) -> bool:
    owner_name = _type_name(owner_name)
    if not owner_name:
        return False
    short_name = owner_name.rsplit(".", 1)[-1]
    if any(marker in short_name for marker in ("$$Lambda$", "CGLIB$$", "$ByteBuddy$", "$MockitoMock$")):
        return True
    return re.search(r"\$\d+(?:$|\$)", short_name) is not None


def is_synthetic_field(raw_field_name: str, field_details: Any = None, *, owner_name: str | None = None) -> bool:
    field_name = raw_field_name.split("_HIDDEN_FIELD___")[0]
    if any(
        field_name.startswith(prefix)
        for prefix in ("this$", "val$", "$SwitchMap$", "$assertionsDisabled")
    ):
        return True
    if field_name in {"serialPersistentFields"} or field_name.endswith("$VALUES"):
        return True
    if is_synthetic_owner(owner_name):
        return True
    if isinstance(field_details, dict):
        if field_details.get("synthetic") is True or _snapshot_note_contains_synthetic(field_details):
            return True
        for key in ("owner", "owner_type", "declaring_class", "declaring_type", "class_name"):
            if is_synthetic_owner(field_details.get(key)):
                return True
    return False


def _numeric_suffix(cangjie_type: str) -> str:
    return {
        "Int8": "i8",
        "Int16": "i16",
        "Int32": "i32",
        "Int64": "i64",
        "Float32": "f32",
        "Float64": "f64",
    }.get(cangjie_type, "")


def _encode_integer_literal(value: Any, cangjie_type: str) -> str:
    try:
        ivalue = int(value)
    except (TypeError, ValueError):
        ivalue = 0
    suffix = _numeric_suffix(cangjie_type)
    return f"{ivalue}{suffix}" if suffix else str(ivalue)


def _encode_float_literal(value: Any, cangjie_type: str) -> str:
    try:
        fvalue = float(value)
    except (TypeError, ValueError):
        fvalue = 0.0
    suffix = _numeric_suffix(cangjie_type)
    text = repr(fvalue)
    if suffix and not text.endswith(suffix):
        text += suffix
    return text


def _memory_address(json_obj: Any) -> str | None:
    if isinstance(json_obj, dict):
        address = json_obj.get("memory_address")
        if isinstance(address, str) and address:
            return address
    return None


def _remember_expression(json_obj: dict[str, Any], expr: str, force_new_object: bool) -> str:
    memory_address = _memory_address(json_obj)
    if force_new_object or not memory_address:
        return expr
    if memory_address in reference_dict:
        return reference_dict[memory_address]
    reference_dict[memory_address] = expr
    return expr


def _is_snapshot_dict(value: Any) -> bool:
    return isinstance(value, dict)


def _inner_value(json_obj: dict[str, Any]) -> Any:
    if not _is_snapshot_dict(json_obj):
        return json_obj
    if "value" in json_obj and json_obj.get("value") is not None and isinstance(json_obj.get("value"), dict):
        inner = json_obj.get("value")
        if inner.get("type"):
            return inner
    return json_obj


def _base_type(json_obj: Any) -> str | None:
    if not isinstance(json_obj, dict):
        return None
    resolved = retrieve_from_type_map(json_obj.get("type"), json_obj.get("type"))
    if resolved == "Any" and isinstance(json_obj.get("value"), dict) and json_obj["value"].get("type"):
        return retrieve_from_type_map(json_obj["value"].get("type"), json_obj["value"].get("type"))
    return resolved


def _is_array_type(cangjie_type: str | None) -> bool:
    return isinstance(cangjie_type, str) and cangjie_type.startswith("Array<")


def _is_direct_literal_snapshot(json_obj: Any) -> bool:
    if json_obj is None:
        return True
    if isinstance(json_obj, (bool, int, float, str)):
        return True
    if isinstance(json_obj, list):
        return True
    if not isinstance(json_obj, dict):
        return False

    cangjie_type = _base_type(json_obj)
    if cangjie_type in DIRECT_LITERAL_TYPES:
        return True
    if cangjie_type in {"Option", "CRC32"}:
        return True
    if _is_array_type(cangjie_type):
        return True
    if cangjie_type in {"ArrayList", "HashSet", "HashMap"}:
        return True
    return False


def _deep_equal(a: Any, b: Any) -> bool:
    """比较两个 JSON 快照是否等价（忽略 memory_address 差异）。"""
    if type(a) != type(b):
        return False
    if isinstance(a, dict):
        ka = set(a) - {"memory_address"}
        kb = set(b) - {"memory_address"}
        if ka != kb:
            return False
        return all(_deep_equal(a[k], b[k]) for k in ka)
    if isinstance(a, list):
        return len(a) == len(b) and all(_deep_equal(x, y) for x, y in zip(a, b))
    return a == b


def _is_mutable_snapshot(json_obj: Any) -> bool:
    if not isinstance(json_obj, dict):
        return False
    cangjie_type = _base_type(json_obj)
    if cangjie_type in {"ArrayList", "HashSet", "HashMap"}:
        return True
    if _is_array_type(cangjie_type):
        return True
    if cangjie_type in STREAM_TYPES:
        return True
    if cangjie_type in DIRECT_LITERAL_TYPES or cangjie_type == "Option":
        return False
    if json_obj.get("instance_fields"):
        return True
    if json_obj.get("static_fields"):
        return True
    return True


def extract_balanced_brackets(text: str, start: int) -> tuple[str | None, int | None]:
    stack: list[str] = []
    in_string = False
    escape = False
    index = start
    while index < len(text):
        char = text[index]
        if escape:
            escape = False
        elif char == "\\":
            escape = True
        elif char in "\"'":
            in_string = not in_string
        elif not in_string:
            if char == "[":
                stack.append(char)
            elif char == "]":
                if not stack:
                    return text[start:index].strip(), index
                stack.pop()
        index += 1
    return None, None


def normalize_struct(text: str) -> str:
    text = re.sub(r'<[^>]+?object at 0x[0-9a-fA-F]+>', '"<_anyobject_>"', text)
    text = re.sub(r"\[ option:.*?::.*?::.*?\]", '"<_anyobject_>"', text)
    text = re.sub(r'class\s+[\w.$]+', '"<class>"', text)
    text = re.sub(r"<class\s+'[\w.]+'?>", '"<class>"', text)
    text = re.sub(r"(?<!['\"])(\b\w+)\s*[:=]\s*", r"'\1': ", text)
    return text


def extract_named_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    pattern = re.compile(r"\[\s*(\w+)\s+")
    pos = 0
    while True:
        match = pattern.search(text, pos)
        if not match:
            break
        name = match.group(1)
        content, end = extract_balanced_brackets(text, match.end())
        if content is None or end is None:
            break
        sections[name] = normalize_struct(content)
        pos = end + 1
    return sections


def java_to_cangjie_regex(java_regex: str) -> str:
    regex = java_regex.encode().decode("unicode_escape")
    regex = re.sub(r"\(\?<(\w+)>", r"(?P<\1>", regex)
    regex = re.sub(r"\\p\{Alpha\}", r"[A-Za-z]", regex)
    return regex


def logically_equal_literal(java_str: str, other_str: str) -> bool:
    if java_str == other_str:
        return True
    if normalize_struct(java_str) == normalize_struct(other_str):
        return True
    java_sections = extract_named_sections(java_str)
    other_sections = extract_named_sections(other_str)
    if java_sections and other_sections and java_sections == other_sections:
        return True
    if charset_map.get(java_str) == other_str or charset_map.get(other_str) == java_str:
        return True
    if java_to_cangjie_locale.get(java_str) == other_str or java_to_cangjie_locale.get(other_str) == java_str:
        return True
    if java_to_cangjie_regex(java_str) == other_str or java_to_cangjie_regex(other_str) == java_str:
        return True
    return False


def _infer_type_from_values(values: Iterable[Any], fallback: str = "Any") -> str:
    inferred = {
        _base_type(value) for value in values if isinstance(value, dict) and _base_type(value) is not None
    }
    if len(inferred) == 1:
        return next(iter(inferred))
    return fallback


def _infer_map_types(json_obj: dict[str, Any]) -> tuple[str, str]:
    keys = json_obj.get("keys", [])
    values = json_obj.get("values", [])
    return _infer_type_from_values(keys), _infer_type_from_values(values)


def _extract_byte_values(json_obj: dict[str, Any]) -> list[Any]:
    for key in ("byte_array", "buffer_elements", "collection_elements"):
        value = json_obj.get(key)
        if value is not None:
            return value
    sink_details = json_obj.get("sink_details")
    if isinstance(sink_details, dict):
        for key in ("byte_array", "buffer_elements", "collection_elements"):
            value = sink_details.get(key)
            if value is not None:
                return value
    return []


def _byte_array_expr(values: list[Any], force_new_object: bool = False) -> str:
    # CHANGED: 字节数组字面量不再加 i8 后缀。
    # 实测确认：仓颉 ByteBuffer.write(Array<UInt8>) 接受 bare int 字面量，
    # 而 Int8 literal (如 10i8) 无法隐式转为 UInt8，编译报错。
    rendered_items: list[str] = []
    for item in values:
        if isinstance(item, dict) and item.get("type"):
            rendered_items.append(_encode_integer_literal(item.get("value", 0), "Int32"))
        elif isinstance(item, int):
            rendered_items.append(_encode_integer_literal(item, "Int32"))
        else:
            try:
                rendered_items.append(_encode_integer_literal(int(item), "Int32"))
            except Exception:
                rendered_items.append("0")
    return f"[{', '.join(rendered_items)}]"


def instantiate_cangjie_object(json_obj: dict[str, Any], force_new_object: bool = False) -> str:
    """为复杂对象生成仓颉构造表达式，不直接递归写字段。"""
    if not isinstance(json_obj, dict):
        return convert_to_cangjie(json_obj, force_new_object=force_new_object)

    node = _inner_value(json_obj)
    cangjie_type = _base_type(node) or "Any"

    if _is_direct_literal_snapshot(node):
        return convert_to_cangjie(node, force_new_object=force_new_object)

    if node.get("enum_name"):
        return f"{cangjie_type}.{sanitize_identifier(node['enum_name'])}"

    if cangjie_type in {"Exception", "IllegalArgumentException", "IllegalStateException", "AssertionError", "NumberFormatException"}:
        message = node.get("message", "")
        return _remember_expression(node, f'{cangjie_type}("{escape_cangjie_string(str(message))}")', force_new_object)

    if cangjie_type == "Path":
        path_value = node.get("file_path", node.get("value", ""))
        return _remember_expression(node, f'Path("{escape_cangjie_string(str(path_value))}")', force_new_object)

    if cangjie_type in {"ByteBuffer", "ByteArrayStream"}:
        bytes_expr = _byte_array_expr(_extract_byte_values(node), force_new_object=True)
        return _remember_expression(node, f"__mockByteBufferOf({bytes_expr})", force_new_object)

    if cangjie_type == "StringReader":
        content = node.get("content")
        if content is None:
            content = node.get("value", "")
        return _remember_expression(node, f'__mockStringReaderOf("{escape_cangjie_string(str(content or ""))}")', force_new_object)

    if cangjie_type == "StringWriter":
        content = node.get("content")
        if content is None:
            content = node.get("value", "")
        return _remember_expression(node, f'__mockStringWriterOf("{escape_cangjie_string(str(content or ""))}")', force_new_object)

    if cangjie_type == "Any":
        return _remember_expression(node, "null", force_new_object)

    ctor_expr = f"{cangjie_type}()" if _has_zero_arg_constructor(node) else render_ioc_new_expr(cangjie_type)
    return _remember_expression(node, ctor_expr, force_new_object)


def _has_zero_arg_constructor(node: dict[str, Any]) -> bool:
    """推断目标类是否有（或已被 change_mode.py 提升为 public 的）零参构造器。

    判断优先级：
    1. 快照显式记录了 constructors 列表 → 检查是否有零参项；
    2. 快照有 has_default_constructor 字段 → 直接采用；
    3. 无构造器信息时：
       - 无实例字段的简单对象通常有默认构造器，用 ClassName()；
       - 有实例字段的复杂对象保守回退到 IoC。
    """
    constructors = node.get("constructors")
    if isinstance(constructors, list):
        return any(
            isinstance(c, dict) and not c.get("parameters")
            for c in constructors
        )
    if "has_default_constructor" in node:
        return bool(node["has_default_constructor"])
    return not bool(node.get("instance_fields"))


def _parse_iso_datetime_str(value: str) -> tuple[int, int, int, int, int, int] | None:
    """Parse ISO datetime/date/time string → (year, month, day, hour, min, sec), or None on failure."""
    try:
        clean = re.sub(r'\[.*?\]$', '', value.strip())
        clean = clean.replace('Z', '+00:00')
        clean = re.sub(r'[+-]\d{2}:\d{2}$', '', clean).strip()
        clean = re.sub(r'\.\d+$', '', clean)
        if 'T' in clean:
            date_s, time_s = clean.split('T', 1)
            y, mo, d = map(int, date_s.split('-'))
            time_parts = time_s.split(':')
            h = int(time_parts[0])
            mi = int(time_parts[1]) if len(time_parts) > 1 else 0
            s = int(time_parts[2]) if len(time_parts) > 2 else 0
            return y, mo, d, h, mi, s
        elif '-' in clean:
            parts = clean.split('-')
            return int(parts[0]), int(parts[1]), int(parts[2]), 0, 0, 0
        elif ':' in clean:
            time_parts = clean.split(':')
            h = int(time_parts[0])
            mi = int(time_parts[1]) if len(time_parts) > 1 else 0
            s = int(time_parts[2]) if len(time_parts) > 2 else 0
            return 1970, 1, 1, h, mi, s
    except Exception:
        pass
    return None


def _datetime_to_cangjie(java_type: str, node: dict) -> str:
    """Convert a Java time-type node to a Cangjie DateTime expression."""
    timestamp = node.get("timestamp")
    if timestamp is not None:
        epoch_secs = int(float(timestamp))
        tz_id = node.get("timezone")
        if tz_id:
            return (f'DateTime.fromTimestamp({epoch_secs})'
                    f'.withTimeZone(TimeZone.get("{escape_cangjie_string(str(tz_id))}"))')
        return f'DateTime.fromTimestamp({epoch_secs})'

    value = str(node.get("value") or "")
    zone_match = re.search(r'\[([^\]]+)\]', value)
    zone_id = zone_match.group(1) if zone_match else None

    parsed = _parse_iso_datetime_str(value)
    if parsed is None:
        return 'DateTime(1970, 1, 1, 0, 0, 0)'
    y, mo, d, h, mi, s = parsed
    dt_expr = f'DateTime({y}, {mo}, {d}, {h}, {mi}, {s})'
    if zone_id:
        dt_expr += f'.withTimeZone(TimeZone.get("{escape_cangjie_string(zone_id)}"))'
    return dt_expr


def _duration_to_cangjie(node: dict) -> str:
    """Convert a Java Duration/TimeUnit/ChronoUnit node to a Cangjie Duration expression."""
    seconds = int(node.get("seconds", 0))
    nanos = int(node.get("nanos", 0))
    total_ns = seconds * 1_000_000_000 + nanos
    if total_ns == 0:
        return "Duration.second * 0"

    negative = total_ns < 0
    abs_ns = abs(total_ns)
    parts: list[str] = []
    for unit_ns, unit_name in [
        (3_600_000_000_000, "hour"),
        (60_000_000_000, "minute"),
        (1_000_000_000, "second"),
        (1_000_000, "millisecond"),
        (1_000, "microsecond"),
        (1, "nanosecond"),
    ]:
        count = abs_ns // unit_ns
        abs_ns %= unit_ns
        if count == 1:
            parts.append(f"Duration.{unit_name}")
        elif count > 1:
            parts.append(f"Duration.{unit_name} * {count}")

    expr = " + ".join(parts) if parts else "Duration.second * 0"
    return f"-({expr})" if negative else expr


def convert_to_cangjie(json_obj: Any, force_new_object: bool = False) -> str:
    """把日志里的 JSON 快照递归转换成仓颉字面量/构造表达式。"""
    if json_obj is None:
        return "null"
    if isinstance(json_obj, bool):
        return "true" if json_obj else "false"
    if isinstance(json_obj, int):
        return str(json_obj)
    if isinstance(json_obj, float):
        return repr(json_obj)
    if isinstance(json_obj, str):
        return f'"{escape_cangjie_string(json_obj)}"'
    if isinstance(json_obj, list):
        return f"[{', '.join(convert_to_cangjie(item, force_new_object=force_new_object) for item in json_obj)}]"
    if not isinstance(json_obj, dict):
        return f'"{escape_cangjie_string(str(json_obj))}"'

    node = _inner_value(json_obj)
    java_type = node.get("type")
    if not java_type:
        if "value" in node:
            return convert_to_cangjie(node.get("value"), force_new_object=force_new_object)
        return "null"

    if "value" in node and node.get("value") is None and not node.get("instance_fields"):
        return "null"

    cangjie_type = _base_type(node) or "Any"

    if cangjie_type == "String":
        value = node.get("value")
        if value is None and "content" in node:
            value = node.get("content", "")
        if value is None and "instant" in node:
            value = node.get("instant", "")
        if value is None and "id" in node:
            value = node.get("id", "")
        expr = f'"{escape_cangjie_string(str(value or ""))}"'
        return _remember_expression(node, expr, force_new_object)

    if cangjie_type == "Rune":
        value = str(node.get("value", "\0"))
        rune = value[0] if value else "\0"
        return _remember_expression(node, f"'{escape_cangjie_rune(rune)}'", force_new_object)

    if cangjie_type in {"Bool"}:
        value = node.get("value")
        if isinstance(value, str):
            expr = "true" if value.lower() == "true" else "false"
        else:
            expr = "true" if value else "false"
        return _remember_expression(node, expr, force_new_object)

    if java_type == "java.math.BigInteger":
        return _remember_expression(node, _big_integer_literal_or_string(node), force_new_object)

    if java_type == "java.math.BigDecimal":
        return _remember_expression(node, _big_decimal_literal_or_string(node), force_new_object)

    if cangjie_type == "DateTime":
        return _remember_expression(node, _datetime_to_cangjie(java_type, node), force_new_object)

    if cangjie_type == "Duration":
        return _remember_expression(node, _duration_to_cangjie(node), force_new_object)

    if cangjie_type == "TimeZone":
        tz_id = str(node.get("id") or "UTC")
        return _remember_expression(node, f'TimeZone.get("{escape_cangjie_string(tz_id)}")', force_new_object)

    if cangjie_type == "Regex":
        pattern = str(node.get("pattern_str") or node.get("value") or "")
        return _remember_expression(node, f'Regex("{escape_cangjie_string(pattern)}")', force_new_object)

    if cangjie_type == "URL":
        url_str = str(node.get("value") or "")
        return _remember_expression(node, f'URL.parse("{escape_cangjie_string(url_str)}")', force_new_object)

    if cangjie_type in {"Int8", "Int16", "Int32", "Int64"}:
        expr = _encode_integer_literal(node.get("value", 0), cangjie_type)
        return _remember_expression(node, expr, force_new_object)

    if cangjie_type in {"Float32", "Float64"}:
        expr = _encode_float_literal(node.get("value", 0.0), cangjie_type)
        return _remember_expression(node, expr, force_new_object)

    if cangjie_type == "Option":
        inner_value = node.get("value")
        if inner_value is None:
            return _remember_expression(node, "None", force_new_object)
        return _remember_expression(
            node,
            f"Some({convert_to_cangjie(inner_value, force_new_object=force_new_object)})",
            force_new_object,
        )

    if cangjie_type == "ArrayList":
        elements = node.get("collection_elements")
        if elements is None and node.get("collection_details"):
            elements = node.get("collection_details", {}).get("collection_elements")
        if elements is None:
            elements = []
        element_type = _infer_type_from_values(elements)
        if element_type == "Any" and node.get("_inferred_element_type"):
            element_type = node["_inferred_element_type"]
        array_expr = f"[{', '.join(convert_to_cangjie(item, force_new_object=force_new_object) for item in elements)}]"
        return _remember_expression(node, f"__mockArrayListOf<{element_type}>({array_expr})", force_new_object)

    if cangjie_type == "HashSet":
        elements = node.get("collection_elements", [])
        element_type = _infer_type_from_values(elements)
        if element_type == "Any" and node.get("_inferred_element_type"):
            element_type = node["_inferred_element_type"]
        array_expr = f"[{', '.join(convert_to_cangjie(item, force_new_object=force_new_object) for item in elements)}]"
        return _remember_expression(node, f"__mockHashSetOf<{element_type}>({array_expr})", force_new_object)

    if cangjie_type == "HashMap":
        keys = node.get("keys", [])
        values = node.get("values", [])
        key_type, value_type = _infer_map_types(node)
        if key_type == "Any" and node.get("_inferred_key_type"):
            key_type = node["_inferred_key_type"]
        if value_type == "Any" and node.get("_inferred_value_type"):
            value_type = node["_inferred_value_type"]
        pairs = ", ".join(
            f"({convert_to_cangjie(key, force_new_object=force_new_object)}, {convert_to_cangjie(value, force_new_object=force_new_object)})"
            for key, value in zip(keys, values)
        )
        return _remember_expression(node, f"__mockHashMapOf<{key_type}, {value_type}>([{pairs}])", force_new_object)

    if _is_array_type(cangjie_type):
        element_type = cangjie_type[len("Array<"):-1]
        if element_type in {"Byte", "Int8"}:
            expr = _byte_array_expr(_extract_byte_values(node), force_new_object=True)
            return _remember_expression(node, expr, force_new_object)
        elements = node.get("collection_elements")
        if elements is None:
            elements = node.get("buffer_elements", [])
        return _remember_expression(
            node,
            f"[{', '.join(convert_to_cangjie(item, force_new_object=force_new_object) for item in elements or [])}]",
            force_new_object,
        )

    if cangjie_type == "Type":
        value = node.get("value", "Any")
        resolved = retrieve_from_type_map(value, value)
        return _remember_expression(node, resolved or "Any", force_new_object)

    if cangjie_type in {"Exception", "IllegalArgumentException", "IllegalStateException", "AssertionError", "NumberFormatException"}:
        exception_type = retrieve_from_type_map(node.get("throwable_type"), cangjie_type) or "Exception"
        message = node.get("message", "")
        return _remember_expression(node, f'{exception_type}("{escape_cangjie_string(str(message))}")', force_new_object)

    if cangjie_type == "CRC32":
        value = _encode_integer_literal(node.get("value", 0), "Int64")
        return _remember_expression(node, f"CRC32({value})", force_new_object)

    if cangjie_type == "Path":
        value = node.get("file_path", node.get("value", ""))
        return _remember_expression(node, f'Path("{escape_cangjie_string(str(value))}")', force_new_object)

    if cangjie_type in {"ByteBuffer", "ByteArrayStream"}:
        return instantiate_cangjie_object(node, force_new_object=force_new_object)

    if cangjie_type == "StringReader":
        return instantiate_cangjie_object(node, force_new_object=force_new_object)

    if cangjie_type == "StringWriter":
        return instantiate_cangjie_object(node, force_new_object=force_new_object)

    if java_type in {
        "java.net.URL",
        "java.net.URI",
        "java.util.regex.Pattern",
        "java.util.regex.Matcher",
        "java.util.Locale",
        "java.util.TimeZone",
        "sun.util.calendar.ZoneInfo",
        "java.time.Duration",
        "java.time.Instant",
        "java.time.LocalDateTime",
        "java.time.LocalDate",
        "java.time.LocalTime",
        "java.time.OffsetDateTime",
        "java.time.ZonedDateTime",
        "java.util.concurrent.TimeUnit",
        "java.time.temporal.ChronoUnit",
        "java.lang.reflect.Modifier",
    }:
        for key in ("value", "instant", "id", "pattern_str", "input_str", "content"):
            if key in node and node.get(key) is not None:
                return _remember_expression(node, f'"{escape_cangjie_string(str(node.get(key)))}"', force_new_object)

    return instantiate_cangjie_object(node, force_new_object=force_new_object)


@dataclass
class RenderContext:
    """在一轮代码生成中维护 alias、临时变量名和输出语句。"""

    prefix: str = "mock"
    counter: int = 0
    statements: list[str] = field(default_factory=list)
    comments: list[str] = field(default_factory=list)

    def fresh_name(self, hint: str = "tmp") -> str:
        self.counter += 1
        hint = sanitize_identifier(hint).strip("`") or "tmp"
        hint = re.sub(r"[^A-Za-z0-9_]", "_", hint)
        if not re.match(r"[A-Za-z_]", hint):
            hint = f"v_{hint}"
        return f"__{self.prefix}_{hint}_{self.counter}"

    def remember(self, json_obj: dict[str, Any], name: str) -> None:
        memory_address = _memory_address(json_obj)
        if memory_address:
            reference_dict[memory_address] = name

    def field_target(self, parent_expr: str, raw_field_name: str) -> str:
        return f"{parent_expr}.{sanitize_identifier(raw_field_name)}"

    def render_field_write(self, parent_expr: str, raw_field_name: str, value_expr: str, _field_details: Any) -> str:
        return f"{self.field_target(parent_expr, raw_field_name)} = {value_expr}"

    def materialize_reference(self, json_obj: Any, hint: str = "tmp") -> str:
        if json_obj is None or _is_direct_literal_snapshot(json_obj):
            return convert_to_cangjie(json_obj, force_new_object=True)
        if not isinstance(json_obj, dict):
            return convert_to_cangjie(json_obj, force_new_object=True)

        memory_address = _memory_address(json_obj)
        if memory_address and memory_address in reference_dict:
            return reference_dict[memory_address]

        name = self.fresh_name(hint)
        self.bind_value(name, json_obj, declare=True)
        return name

    def bind_value(self, target_expr: str, json_obj: Any, declare: bool = False) -> None:
        if json_obj is None:
            prefix = "var " if declare else ""
            self.statements.append(f"{prefix}{target_expr} = null")
            return

        if not isinstance(json_obj, dict):
            prefix = "var " if declare else ""
            self.statements.append(f"{prefix}{target_expr} = {convert_to_cangjie(json_obj, force_new_object=True)}")
            return

        node = _inner_value(json_obj)
        self.remember(node, target_expr)

        # 自指针
        if node.get("note") in {"instance of self-referential field", "circular_reference"}:
            prefix = "var " if declare else ""
            self.statements.append(f"{prefix}{target_expr} = {target_expr}")
            return

        # 直接字面量/集合快照可以直接赋值。
        if _is_direct_literal_snapshot(node):
            prefix = "var " if declare else ""
            self.statements.append(f"{prefix}{target_expr} = {convert_to_cangjie(node, force_new_object=True)}")
            return

        ctor_expr = instantiate_cangjie_object(node, force_new_object=True)
        cangjie_type = _base_type(node) or "Any"

        # StringReader/StringWriter 需要特殊处理：caller 需同时持有底层 ByteBuffer
        if cangjie_type == "StringReader":
            content = node.get("content")
            if content is None:
                content = node.get("value", "")
            escaped_content = escape_cangjie_string(str(content or ""))
            # 生成唯一buffer变量名
            buf_var = f"{target_expr}_buf"
            # 多行构造：创建 buffer -> 写入内容 -> seek(0) -> 创建 reader
            self.statements.append(f"let {buf_var} = ByteBuffer()")
            self.statements.append(f'{buf_var}.write("{escaped_content}".toArray())')
            self.statements.append(f'{buf_var}.seek(SeekPosition.Begin(0))')
            self.statements.append(f"let {target_expr} = StringReader({buf_var})")
            # 注册 buffer->stream 映射，供 render_in_place_mutation 使用
            _set_stream_buffer(target_expr, buf_var)
            _set_stream_buffer(f"StringReader({buf_var})", buf_var)
            # 处理 instance_fields（如果有）
            instance_fields = node.get("instance_fields", {})
            owner_name = node.get("type")
            for raw_field_name, field_details in instance_fields.items():
                if is_synthetic_field(raw_field_name, field_details, owner_name=owner_name):
                    continue
                field_name = raw_field_name.split("_HIDDEN_FIELD___")[0]
                if not isinstance(field_details, dict):
                    self.statements.append(self.render_field_write(target_expr, field_name, convert_to_cangjie(field_details, force_new_object=True), field_details))
                    continue
                child_address = _memory_address(field_details)
                if child_address and child_address == _memory_address(node):
                    self.statements.append(self.render_field_write(target_expr, field_name, target_expr, field_details))
                    continue
                if field_details.get("note") in {"instance of self-referential field", "circular_reference"}:
                    self.statements.append(self.render_field_write(target_expr, field_name, target_expr, field_details))
                    continue
                if _is_direct_literal_snapshot(field_details):
                    self.statements.append(self.render_field_write(target_expr, field_name, convert_to_cangjie(field_details, force_new_object=True), field_details))
                    continue
                nested_ref = self.materialize_reference(field_details, hint=field_name)
                self.statements.append(self.render_field_write(target_expr, field_name, nested_ref, field_details))
            return

        if cangjie_type == "StringWriter":
            content = node.get("content")
            if content is None:
                content = node.get("value", "")
            escaped_content = escape_cangjie_string(str(content or ""))
            # 生成唯一buffer变量名
            buf_var = f"{target_expr}_buf"
            # 多行构造：创建 buffer -> 创建 writer -> 写入内容 -> flush
            self.statements.append(f"let {buf_var} = ByteBuffer()")
            self.statements.append(f"let {target_expr} = StringWriter({buf_var})")
            self.statements.append(f'{target_expr}.write("{escaped_content}")')
            self.statements.append(f"{target_expr}.flush()")
            # 注册 buffer->stream 映射，供 render_in_place_mutation 使用
            _set_stream_buffer(target_expr, buf_var)
            _set_stream_buffer(f"StringWriter({buf_var})", buf_var)
            # 处理 instance_fields（如果有）
            instance_fields = node.get("instance_fields", {})
            owner_name = node.get("type")
            for raw_field_name, field_details in instance_fields.items():
                if is_synthetic_field(raw_field_name, field_details, owner_name=owner_name):
                    continue
                field_name = raw_field_name.split("_HIDDEN_FIELD___")[0]
                if not isinstance(field_details, dict):
                    self.statements.append(self.render_field_write(target_expr, field_name, convert_to_cangjie(field_details, force_new_object=True), field_details))
                    continue
                child_address = _memory_address(field_details)
                if child_address and child_address == _memory_address(node):
                    self.statements.append(self.render_field_write(target_expr, field_name, target_expr, field_details))
                    continue
                if field_details.get("note") in {"instance of self-referential field", "circular_reference"}:
                    self.statements.append(self.render_field_write(target_expr, field_name, target_expr, field_details))
                    continue
                if _is_direct_literal_snapshot(field_details):
                    self.statements.append(self.render_field_write(target_expr, field_name, convert_to_cangjie(field_details, force_new_object=True), field_details))
                    continue
                nested_ref = self.materialize_reference(field_details, hint=field_name)
                self.statements.append(self.render_field_write(target_expr, field_name, nested_ref, field_details))
            return

        prefix = "var " if declare else ""
        self.statements.append(f"{prefix}{target_expr} = {ctor_expr}")

        instance_fields = node.get("instance_fields", {})
        owner_name = node.get("type")
        for raw_field_name, field_details in instance_fields.items():
            if is_synthetic_field(raw_field_name, field_details, owner_name=owner_name):
                continue
            field_name = raw_field_name.split("_HIDDEN_FIELD___")[0]

            if not isinstance(field_details, dict):
                self.statements.append(
                    self.render_field_write(
                        target_expr,
                        field_name,
                        convert_to_cangjie(field_details, force_new_object=True),
                        field_details,
                    )
                )
                continue

            # 直接自引用
            child_address = _memory_address(field_details)
            if child_address and child_address == _memory_address(node):
                self.statements.append(self.render_field_write(target_expr, field_name, target_expr, field_details))
                continue
            if field_details.get("note") in {"instance of self-referential field", "circular_reference"}:
                self.statements.append(self.render_field_write(target_expr, field_name, target_expr, field_details))
                continue

            if _is_direct_literal_snapshot(field_details):
                self.statements.append(
                    self.render_field_write(
                        target_expr,
                        field_name,
                        convert_to_cangjie(field_details, force_new_object=True),
                        field_details,
                    )
                )
                continue

            nested_ref = self.materialize_reference(field_details, hint=field_name)
            self.statements.append(self.render_field_write(target_expr, field_name, nested_ref, field_details))


def render_value_setup(target_name: str, json_obj: Any) -> list[str]:
    """生成”把一个日志快照还原到仓颉变量”的完整赋值序列。"""
    ctx = RenderContext()
    ctx.bind_value(target_name, json_obj, declare=True)
    return ctx.statements


def _render_assignment(target_expr: str, json_obj: Any, visited: set[int]) -> list[str]:
    ctx = RenderContext()
    ctx.bind_value(target_expr, json_obj, declare=False)
    return ctx.statements


def set_object_instance_fields(target_expr: str, json_obj: dict[str, Any]) -> list[str]:
    """生成把日志中的实例终态写回仓颉对象的赋值语句。"""
    return _render_assignment(target_expr, json_obj, set())


def _render_string_equal(actual_expr: str, expected_literal: str) -> str:
    return f"({actual_expr} == {expected_literal} || __mockStringEqual({actual_expr}, {expected_literal}))"


def recursive_equal(actual_expr: str, expected: Any, visited: set[int] | None = None) -> str:
    """生成仓颉布尔表达式，用来判断运行时结果是否等价于日志期望快照。"""
    if visited is None:
        visited = set()

    if expected is None:
        return f"{actual_expr} == null"

    if not isinstance(expected, dict):
        if isinstance(expected, str):
            literal = convert_to_cangjie(expected)
            return _render_string_equal(actual_expr, literal)
        return f"{actual_expr} == {convert_to_cangjie(expected)}"

    node = _inner_value(expected)

    node_id = id(node)
    if node_id in visited:
        return "true"
    visited = set(visited)
    visited.add(node_id)

    if node.get("note") in {"instance of self-referential field", "circular_reference"}:
        return "true"

    cangjie_type = _base_type(node)
    if is_synthetic_owner(node.get("type")) or _snapshot_note_contains_synthetic(node):
        return "true"

    if node.get("enum_name"):
        return f"{actual_expr} == {cangjie_type}.{sanitize_identifier(node['enum_name'])}"

    if cangjie_type in EXCEPTION_TYPES or node.get("throwable_type"):
        exception_type = retrieve_from_type_map(node.get("throwable_type"), cangjie_type) or "Exception"
        return f"({actual_expr} is {exception_type})"

    if _is_direct_literal_snapshot(node):
        literal = convert_to_cangjie(node, force_new_object=True)
        if cangjie_type == "String":
            return _render_string_equal(actual_expr, literal)
        return f"{actual_expr} == {literal}"

    if cangjie_type in STREAM_TYPES:
        # 流对象的“等价”更像是内容快照对比，而不是对象标识对比。
        if cangjie_type in {"ByteBuffer", "ByteArrayStream"}:
            bytes_expr = _byte_array_expr(_extract_byte_values(node), force_new_object=True)
            return f"__mockByteStreamEquals({actual_expr}, {bytes_expr})"
        if cangjie_type == "StringReader":
            content = node.get("content", node.get("value", ""))
            expected_literal = convert_to_cangjie(str(content or ""))
            return f"__mockReaderEquals({actual_expr}, {expected_literal})"
        if cangjie_type == "StringWriter":
            content = node.get("content", node.get("value", ""))
            expected_literal = convert_to_cangjie(str(content or ""))
            # StringWriter 需要通过底层 ByteBuffer 比较
            buf_var = _get_stream_buffer(actual_expr)
            if buf_var:
                return f"__mockWriterEquals({buf_var}, {expected_literal})"
            # 未找到 buffer，退回到简单的类型检查
            return f"({actual_expr} is StringWriter)"

    comparisons: list[str] = []
    owner_name = node.get("type")
    for raw_field_name, field_details in node.get("instance_fields", {}).items():
        if is_synthetic_field(raw_field_name, field_details, owner_name=owner_name):
            continue
        field_name = sanitize_identifier(raw_field_name.split("_HIDDEN_FIELD___")[0])
        comparisons.append(recursive_equal(f"{actual_expr}.{field_name}", field_details, visited))

    static_fields = node.get("static_fields", {})
    for raw_field_name, field_details in static_fields.items():
        if is_synthetic_field(raw_field_name, field_details, owner_name=owner_name):
            continue
        field_name = sanitize_identifier(raw_field_name.split("_HIDDEN_FIELD___")[0])
        clazz_expr = _base_type(node) or "Any"
        comparisons.append(recursive_equal(f"{clazz_expr}.{field_name}", field_details, visited))

    if not comparisons:
        # 至少退化到同类型/同字符串快照比较。
        literal = convert_to_cangjie(node, force_new_object=True)
        if cangjie_type == "String":
            return _render_string_equal(actual_expr, literal)
        return f"{actual_expr} == {literal}"

    return " && ".join(f"({comp})" for comp in comparisons)


def render_expect_true(condition: str, message: str | None = None, *, fail_fast: bool = True) -> str:
    """把布尔条件包装成仓颉测试断言。"""
    macro = "@Assert" if fail_fast else "@Expect"
    if message:
        return f"{macro}({condition}) // {escape_cangjie_string(message)}"
    return f"{macro}({condition})"


def render_expect_equal(actual_expr: str, expected: Any, message: str | None = None, *, fail_fast: bool = True) -> str:
    return render_expect_true(recursive_equal(actual_expr, expected), message=message, fail_fast=fail_fast)


def _sorted_arg_snapshots(method_dict: dict[str, Any]) -> list[Any]:
    args = method_dict.get("Args Initial", []) or []
    try:
        return [value for _, value in sorted(args, key=lambda item: int(item[0]))]
    except Exception:
        return [value for _, value in args]


def render_on_argument_matcher(arg_snapshot: Any) -> str:
    """为 @On 桩签名渲染参数匹配器。

    - 直接字面量（数字、字符串、bool、集合等）：生成对应的字面量表达式；
    - 复杂对象：生成 argThat { arg: Type => <字段比较> } 语义匹配；
    - 无法提取有效匹配条件时退化为通配符 '_'（宽松匹配)
    """
    if _is_direct_literal_snapshot(arg_snapshot):
        return convert_to_cangjie(arg_snapshot, force_new_object=True)

    if not isinstance(arg_snapshot, dict):
        return "_"

    node = _inner_value(arg_snapshot)
    cangjie_type = _base_type(node) or "Any"

    condition = recursive_equal("arg", node, set())
    # condition 中含 "arg" 说明成功生成了字段比较；仅 "true" 表示无有效条件。
    if condition and condition != "true" and "arg" in condition:
        return f"argThat {{ arg: {cangjie_type} => {condition} }}"

    return "_"


def listener_type_for_snapshot(arg_snapshot: Any, fallback: str = "Any") -> str:
    """为 ValueListener / capture 推断一个尽量具体的参数类型。"""
    if isinstance(arg_snapshot, dict):
        node = _inner_value(arg_snapshot)
        return _base_type(node) or fallback
    if isinstance(arg_snapshot, bool):
        return "Bool"
    if isinstance(arg_snapshot, int):
        return "Int64"
    if isinstance(arg_snapshot, float):
        return "Float64"
    if isinstance(arg_snapshot, str):
        return "String"
    if isinstance(arg_snapshot, list):
        return "Array<Any>"
    return fallback


def _render_existing_object_field_updates(
    target_expr: str,
    json_obj: dict[str, Any],
) -> list[str]:
    """把已有对象更新到指定快照，不重建根对象本身。"""
    if not isinstance(json_obj, dict):
        return []

    node = _inner_value(json_obj)
    ctx = RenderContext()
    ctx.remember(node, target_expr)

    owner_name = node.get("type")
    for raw_field_name, field_details in node.get("instance_fields", {}).items():
        if is_synthetic_field(raw_field_name, field_details, owner_name=owner_name):
            continue

        field_name = raw_field_name.split("_HIDDEN_FIELD___")[0]

        if not isinstance(field_details, dict):
            ctx.statements.append(
                ctx.render_field_write(
                    target_expr,
                    field_name,
                    convert_to_cangjie(field_details, force_new_object=True),
                    field_details,
                )
            )
            continue

        child_address = _memory_address(field_details)
        if child_address and child_address == _memory_address(node):
            ctx.statements.append(ctx.render_field_write(target_expr, field_name, target_expr, field_details))
            continue
        if field_details.get("note") in {"instance of self-referential field", "circular_reference"}:
            ctx.statements.append(ctx.render_field_write(target_expr, field_name, target_expr, field_details))
            continue

        if _is_direct_literal_snapshot(field_details):
            ctx.statements.append(
                ctx.render_field_write(
                    target_expr,
                    field_name,
                    convert_to_cangjie(field_details, force_new_object=True),
                    field_details,
                )
            )
            continue

        nested_ref = ctx.materialize_reference(field_details, hint=field_name)
        ctx.statements.append(ctx.render_field_write(target_expr, field_name, nested_ref, field_details))

    return ctx.statements


def render_in_place_mutation(
    target_expr: str,
    json_obj: Any,
) -> tuple[list[str], list[str]]:
    """为 dependency arg/receiver 渲染“原地副作用回放”语句。"""
    if not isinstance(json_obj, dict):
        return [], []  # primitive 值传递，无副作用语义，无需回放

    node = _inner_value(json_obj)
    cangjie_type = _base_type(node) or "Any"

    if cangjie_type == "ArrayList":
        elements = node.get("collection_elements")
        if elements is None and node.get("collection_details"):
            elements = node.get("collection_details", {}).get("collection_elements")
        elements = elements or []
        element_type = _infer_type_from_values(elements)
        array_expr = f"[{', '.join(convert_to_cangjie(item, force_new_object=True) for item in elements)}]"
        return [f"__mockResetArrayList<{element_type}>({target_expr}, {array_expr})"], []

    if cangjie_type == "HashSet":
        elements = node.get("collection_elements", [])
        element_type = _infer_type_from_values(elements)
        array_expr = f"[{', '.join(convert_to_cangjie(item, force_new_object=True) for item in elements)}]"
        return [f"__mockResetHashSet<{element_type}>({target_expr}, {array_expr})"], []

    if cangjie_type == "HashMap":
        keys = node.get("keys", [])
        values = node.get("values", [])
        key_type, value_type = _infer_map_types(node)
        pairs = ", ".join(
            f"({convert_to_cangjie(key, force_new_object=True)}, {convert_to_cangjie(value, force_new_object=True)})"
            for key, value in zip(keys, values)
        )
        return [f"__mockResetHashMap<{key_type}, {value_type}>({target_expr}, [{pairs}])"], []

    if cangjie_type == "ByteBuffer":
        bytes_expr = _byte_array_expr(_extract_byte_values(node), force_new_object=True)
        return [f"__mockResetByteBuffer({target_expr}, {bytes_expr})"], []

    if cangjie_type == "ByteArrayStream":
        bytes_expr = _byte_array_expr(_extract_byte_values(node), force_new_object=True)
        return [f"__mockResetByteBuffer({target_expr}, {bytes_expr})"], []

    if cangjie_type == "StringReader":
        content = node.get("content", node.get("value", ""))
        content_expr = convert_to_cangjie(str(content or ""))
        buf_var = _get_stream_buffer(target_expr)
        if buf_var:
            # 已注册 buffer：直接重置 buffer 并重建 reader
            return [
                f"__mockResetByteBuffer({buf_var}, {content_expr}.toArray())",
                f"let {target_expr} = StringReader({buf_var})",
            ], []
        return [], []

    if cangjie_type == "StringWriter":
        content = node.get("content", node.get("value", ""))
        content_expr = convert_to_cangjie(str(content or ""))
        buf_var = _get_stream_buffer(target_expr)
        if buf_var:
            return [
                f"__mockResetByteBuffer({buf_var}, {content_expr}.toArray())",
                f"let {target_expr} = StringWriter({buf_var})",
            ], []
        return [], []  # listener 内拿不到底层 buffer，无法原地重置

    if cangjie_type == "StringWriter":
        content = node.get("content", node.get("value", ""))
        content_expr = convert_to_cangjie(str(content or ""))
        buf_var = _get_stream_buffer(target_expr)
        if buf_var:
            return [
                f"__mockResetByteBuffer({buf_var}, {content_expr}.toArray())",
                f"let {target_expr} = StringWriter({buf_var})",
            ], []
        return [], []  # listener 内拿不到底层 buffer，无法原地重置

    if _is_array_type(cangjie_type):
        elements = node.get("collection_elements", node.get("buffer_elements", []))
        if elements:
            lines = [
                f"{target_expr}[{i}] = {convert_to_cangjie(elem, force_new_object=True)}"
                for i, elem in enumerate(elements)
            ]
            return lines, []
        return [], []  # final 是空数组，无需回放

    if node.get("instance_fields"):
        return _render_existing_object_field_updates(target_expr, node), []

    return [], []  # 无 instance_fields 快照，无法推断字段赋值


def _render_action_lambda(action_lines: Iterable[str], result_expr: str) -> str:
    rendered_lines = [line for line in action_lines if line is not None]
    rendered_body = "\n".join(f"    {line}" for line in [*rendered_lines, result_expr])
    return "{ =>\n" + rendered_body + "\n}"


def render_stub_action_fragment(method_dict: dict[str, Any], *, action_lines: Iterable[str] | None = None) -> str:
    """为单次 dependency 触发渲染 @On 操作片段，不包含基数。"""
    replay_lines = [line for line in (action_lines or []) if line.strip()]
    if method_dict.get("Exception thrown") is not None:
        exception_expr = convert_to_cangjie(method_dict["Exception thrown"], force_new_object=True)
        if replay_lines:
            return f".throws({_render_action_lambda(replay_lines, exception_expr)})"
        return f".throws({exception_expr})"
    if "Return value" in method_dict:
        return_expr = convert_to_cangjie(method_dict["Return value"], force_new_object=True)
        if replay_lines:
            return f".returns({_render_action_lambda(replay_lines, return_expr)})"
        return f".returns({return_expr})"
    if replay_lines:
        return f".returns({_render_action_lambda(replay_lines, '()')})"
    return ".returns()"


def render_on_stub_chain(
    signature_expr: str,
    method_dicts: Iterable[dict[str, Any]],
    *,
    action_line_groups: Iterable[Iterable[str]] | None = None,
) -> str:
    """把同一桩签名的多次触发压成一个 @On 链。"""
    method_list = list(method_dicts)
    rendered_action_groups = [list(group) for group in action_line_groups] if action_line_groups is not None else [
        [] for _ in method_list
    ]
    if not method_list:
        return f"@On({signature_expr}).fails()"

    prefix_comment = ""

    if (
        len(method_list) > 1
        and all(not group for group in rendered_action_groups)
        and all(method.get("Exception thrown") is None for method in method_list)
        and all("Return value" in method for method in method_list)
    ):
        values = ", ".join(
            convert_to_cangjie(method["Return value"], force_new_object=True)
            for method in method_list
        )
        return prefix_comment + f"@On({signature_expr}).returnsConsecutively({values})"

    chain_parts: list[str] = []
    for index, method_dict in enumerate(method_list):
        action_lines = rendered_action_groups[index] if index < len(rendered_action_groups) else []
        chain_parts.append(render_stub_action_fragment(method_dict, action_lines=action_lines) + ".once()")
        if index != len(method_list) - 1:
            chain_parts.append(".then()")
    return prefix_comment + f"@On({signature_expr})" + "".join(chain_parts)


def render_dependency_side_effect_notes(
    method_dict: dict[str, Any],
    *,
    replayed_arg_indices: set[int] | None = None,
    replayed_static_fields: bool = False,
) -> list[str]:
    notes: list[str] = []
    replayed_arg_indices = replayed_arg_indices or set()
    initial_map = {int(idx): snap for idx, snap in method_dict.get("Args Initial", [])}
    for arg_idx_str, final_snap in method_dict.get("Args Final", []):
        arg_idx = int(arg_idx_str)
        if arg_idx in replayed_arg_indices:
            continue
        initial_snap = initial_map.get(arg_idx)
        if initial_snap is None:
            continue
        if _deep_equal(initial_snap, final_snap):
            continue
        if not _is_mutable_snapshot(final_snap):
            continue
        notes.append(f"// TODO: 参数[{arg_idx}] 的状态变更待回放")
    if method_dict.get("Static Fields Changed") and not replayed_static_fields:
        notes.append("// TODO: 静态字段副作用未在 @On action lambda 中回放")
    return notes


def update_static_fields(json_data: list[dict[str, Any]]) -> list[str]:
    """把日志中的静态字段变化转换成仓颉类字段赋值语句。"""
    lines: list[str] = []
    for class_data in json_data:
        for class_name, fields in class_data.items():
            if is_synthetic_owner(class_name):
                continue
            cangjie_class_name = retrieve_from_type_map(class_name, class_name) or class_name
            for field_update in fields:
                for raw_field_name, field_info in field_update.items():
                    if is_synthetic_field(raw_field_name, field_info, owner_name=class_name):
                        continue
                    field_name = sanitize_identifier(raw_field_name.split("_HIDDEN_FIELD___")[0])
                    details = field_info.get("details") if isinstance(field_info, dict) else field_info
                    lines.extend(_render_assignment(f"{cangjie_class_name}.{field_name}", details, set()))
    return lines


def side_effect_is_correct(json_data: list[dict[str, Any]]) -> str:
    """生成静态字段副作用校验条件。"""
    comparisons: list[str] = []
    for class_data in json_data:
        for class_name, fields in class_data.items():
            if is_synthetic_owner(class_name):
                continue
            cangjie_class_name = retrieve_from_type_map(class_name, class_name) or class_name
            for field_update in fields:
                for raw_field_name, field_info in field_update.items():
                    if is_synthetic_field(raw_field_name, field_info, owner_name=class_name):
                        continue
                    field_name = sanitize_identifier(raw_field_name.split("_HIDDEN_FIELD___")[0])
                    details = field_info.get("details") if isinstance(field_info, dict) else field_info
                    comparisons.append(recursive_equal(f"{cangjie_class_name}.{field_name}", details))
    if not comparisons:
        return "true"
    return " && ".join(f"({comparison})" for comparison in comparisons)


def render_exception_throw(json_obj: dict[str, Any]) -> str:
    return f"throw {convert_to_cangjie(json_obj, force_new_object=True)}"


def collect_required_imports(*json_values: Any, include_test_imports: bool = True, include_mock_imports: bool = True) -> set[str]:
    """根据快照推断生成仓颉代码时需要的 import。"""
    imports: set[str] = set()
    if include_test_imports:
        imports.add("import std.unittest.*")
        imports.add("import std.unittest.testmacro.*")
    if include_mock_imports:
        imports.add("import std.unittest.mock.*")
        imports.add("import std.unittest.mock.mockmacro.*")

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if not isinstance(node, dict):
            return

        mapped_type = _base_type(node)
        if mapped_type in {"ArrayList", "HashSet", "HashMap"}:
            imports.add("import std.collection.*")
        if mapped_type in {"ByteBuffer", "ByteArrayStream", "StringReader", "StringWriter", "InputStream", "OutputStream"}:
            imports.add("import std.io.*")
        if mapped_type == "Path":
            imports.add("import std.fs.*")
        if mapped_type == "Regex":
            imports.add("import std.regex.*")
        if mapped_type == "URL":
            imports.add("import stdx.encoding.url.*")
        if mapped_type == "Type":
            imports.add("import std.reflect.*")
        if mapped_type in {"DateTime", "Duration", "TimeZone"}:
            imports.add("import std.time.*")

        for value in node.values():
            walk(value)

    for json_value in json_values:
        walk(json_value)
    return imports


def _legacy_render_runtime_support() -> str:
    """旧版内联辅助函数源码，保留用作 helper.cj 模板的来源参考。"""
    chunks = [render_reflection_runtime_support(), r'''
private func __mockArrayListOf<T>(items: Array<T>): ArrayList<T> {
    let list = ArrayList<T>(items.size)
    list.add(all: items)
    list
}

private func __mockResetArrayList<T>(target: ArrayList<T>, items: Array<T>): Unit {
    target.clear()
    target.add(all: items)
}

private func __mockHashSetOf<T>(items: Array<T>): HashSet<T> where T <: Hashable & Equatable<T> {
    let set = HashSet<T>()
    for (item in items) {
        set.add(item)
    }
    set
}

private func __mockResetHashSet<T>(target: HashSet<T>, items: Array<T>): Unit where T <: Hashable & Equatable<T> {
    target.clear()
    for (item in items) {
        target.add(item)
    }
}

private func __mockHashMapOf<K, V>(items: Array<(K, V)>): HashMap<K, V> where K <: Hashable & Equatable<K> {
    let map = HashMap<K, V>()
    for ((k, v) in items) {
        map.add(k, v)
    }
    map
}

private func __mockResetHashMap<K, V>(target: HashMap<K, V>, items: Array<(K, V)>): Unit where K <: Hashable & Equatable<K> {
    target.clear()
    for ((k, v) in items) {
        target.add(k, v)
    }
}

private func __mockByteBufferOf(items: Array<UInt8>): ByteBuffer {
    let stream = ByteBuffer()
    stream.write(items)
    stream.seek(SeekPosition.Begin(0))
    stream
}

private func __mockResetByteBuffer(target: ByteBuffer, items: Array<UInt8>): Unit {
    // 实测确认 ByteBuffer.clear() 可用：clear() + write() + seek(Begin(0)) 可将 buffer 重置为指定内容
    target.clear()
    target.write(items)
    target.seek(SeekPosition.Begin(0))
}

private func __mockStringReaderOf(text: String): StringReader<ByteBuffer> {
    let stream = ByteBuffer()
    stream.write(text.toArray())
    stream.seek(SeekPosition.Begin(0))
    StringReader(stream)
}

private func __mockStringWriterOf(text: String): StringWriter<ByteBuffer> {
    let stream = ByteBuffer()
    let writer = StringWriter(stream)
    writer.write(text)
    writer.flush()
    writer
}

private func __mockCharsetAlias(value: String): String {
    match (value) {
        case "UTF-8" => "utf-8"
        case "UTF8" => "utf-8"
        case "UTF-16" => "utf-16"
        case "UTF-16BE" => "utf-16-be"
        case "UTF-16LE" => "utf-16-le"
        case "US-ASCII" => "ascii"
        case "ISO-8859-1" => "latin1"
        case "windows-1252" => "cp1252"
        case "windows-1251" => "cp1251"
        case "Big5" => "big5"
        case "GB2312" => "gb2312"
        case "GB18030" => "gb18030"
        case "Shift_JIS" => "shift_jis"
        case "ISO-2022-JP" => "iso2022_jp"
        case other => other
    }
}

private func __mockLocaleAlias(value: String): String {
    match (value) {
        case "en" => "en_US"
        case "fr" => "fr_FR"
        case "de" => "de_DE"
        case "es" => "es_ES"
        case "it" => "it_IT"
        case "pt" => "pt_PT"
        case "zh" => "zh_CN"
        case "ja" => "ja_JP"
        case "ko" => "ko_KR"
        case "ru" => "ru_RU"
        case "ar" => "ar_EG"
        case "ar_EG" => "ar_EG"
        case "hi" => "hi_IN"
        case "hi_IN" => "hi_IN"
        case other => other
    }
}

private func __mockNormalizeStruct(value: String): String {
    __mockLocaleAlias(__mockCharsetAlias(value))
}

private func __mockStringEqual(lhs: String, rhs: String): Bool {
    lhs == rhs || __mockNormalizeStruct(lhs) == __mockNormalizeStruct(rhs)
}

private func __mockByteStreamEquals(stream: ByteBuffer, expected: Array<UInt8>): Bool {
    let pos = stream.position
    stream.seek(SeekPosition.Begin(0))
    let current = readToEnd(stream)
    stream.seek(SeekPosition.Begin(pos))
    current == expected
}

// 实测确认 StringReader.seek(Begin(0)) + readToEnd() 可用
private func __mockReaderEquals<T>(reader: StringReader<T>, expected: String): Bool where T <: InputStream & Seekable {
    reader.seek(SeekPosition.Begin(0))
    let content = reader.readToEnd()
    content == expected
}

// 实测确认 StringWriter 底层 ByteBuffer 可通过 buf.seek(Begin(0)) + readToEnd(buf) 获取写入内容
private func __mockWriterEquals(buf: ByteBuffer, expected: String): Bool {
    buf.seek(SeekPosition.Begin(0))
    let content = readToEnd(buf)
    content == expected.toArray()
}
'''.strip()]
    return "\n\n".join(chunk for chunk in chunks if chunk.strip())


def render_runtime_support() -> str:
    """运行时辅助函数已抽到 helper.cj，由 write_helper_cj 部署到工程包内。
    生成的测试文件不再内联这些 helper。"""
    return ""


def render_import_block(*json_values: Any, include_test_imports: bool = True, include_mock_imports: bool = True) -> str:
    imports = sorted(collect_required_imports(*json_values, include_test_imports=include_test_imports, include_mock_imports=include_mock_imports))
    return "\n".join(imports)


def render_test_case(
    *,
    package_name: str,
    class_name: str,
    case_name: str,
    body_lines: Iterable[str],
    extra_imports: Iterable[str] | None = None,
    include_runtime_support: bool = True,
) -> str:
    """把若干生成语句包装成一个完整的仓颉测试文件片段。"""
    imports = list(extra_imports or [])
    if include_runtime_support:
        runtime_support = render_runtime_support()
        for import_line in reflection_required_imports():
            if import_line not in imports:
                imports.append(import_line)
    else:
        runtime_support = ""

    rendered_body = "\n".join(f"        {line}" if line else "" for line in body_lines)
    rendered_imports = "\n".join(imports)
    chunks = [f"package {package_name}"]
    if rendered_imports:
        chunks.append(rendered_imports)
    if runtime_support:
        chunks.append(runtime_support)
    chunks.append(
        f"""
@Test
class {class_name} {{
    @TestCase
    func {case_name}() {{
{rendered_body}
    }}
}}
""".strip()
    )
    return "\n\n".join(chunk for chunk in chunks if chunk.strip())
