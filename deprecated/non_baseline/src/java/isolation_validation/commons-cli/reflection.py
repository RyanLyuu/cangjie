"""生成仓颉侧基于 simpleioc 的实例构造辅助代码。

职责：
  - 提供通过 SimpleIoc 自动选择构造器并创建实例的表达式生成函数；
  - 提供对应的运行时辅助函数源码（注入到生成的仓颉测试文件中）；
  - 提供需要额外引入的 import 列表。

字段访问器（__mockGet* / __mockSet*）已改由 change_mode.py 直接修改源码可见性取代，
本文件不再负责这部分。
"""

from __future__ import annotations


def render_ioc_new_expr(cangjie_type: str) -> str:
    return f"__mockCreateViaIoc<{cangjie_type}>()"


def required_imports() -> list[str]:
    return []


def render_runtime_support() -> str:
    return r'''
private func __mockCreateViaIoc<T>(): T where T <: Object {
    SimpleIoc.default.unregister<T>()
    let instance = SimpleIoc.default.construct<T>()
    SimpleIoc.default.unregister<T>()
    instance
}
'''.strip()
