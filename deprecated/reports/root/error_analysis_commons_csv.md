# commons-csv 编译错误分析

---

## 错误分类表

| 类别 | 错误原因 | 占比 | 例子 | 归属 |
|---|---|---|---|---|
| 1 | shim interface 空壳，没声明 Java API 方法 | 40% | `'read' is not a member of interface 'JavaIoReader'`（fragment 1）— `JavaIoReader` 是空壳 interface，没声明 `read()` 方法，LLM 调用 `reader.read()` 编译必炸 | 类型翻译（`interface_shim.py`） |
| 2 | Java 类型未映射成 Cangjie 等价物 | 20% | `undeclared type name 'Char'`（fragment 12）— `Char` 应映射为 `Rune`；`undeclared identifier 'null'`（fragment 24）— Cangjie 无 `null`，应用 `Option.None` | 类型翻译（`java_base_type_map.json`） |
| 3 | Cangjie 语法错误，LLM 不熟悉 Cangjie 语法 | 25% | `expected '=>' in lambda expression, found keyword 'if'`（fragment 89）— Cangjie lambda 写 `{ params => body }`，LLM 写成 Java 的 `(params) -> body` | 片段翻译（Part 2/3 目标错误） |
| 4 | Java enum 翻译成非静态成员，LLM 按静态访问 | 10% | `'INVALID' is non-static member, cannot access by type name`（fragment 14）— Java `TokenType.INVALID` 在骨架里变成实例成员，`Token.INVALID` 编译报错 | 类型翻译（`create_skeleton.py` enum 处理） |
| 5 | self/this 混用 | 5% | `undeclared identifier 'self'`（fragment 23）— Cangjie 用 `this`，LLM 受 Python/Rust 影响用了 `self` | 片段翻译（Part 2 语法注入可缓解） |

---

## 结论

类别 1+2+4 合计 70%，全是类型翻译阶段的预存问题：

- **shim 空壳（40%）**：`interface_shim.py` 生成的占位 interface 只有类型名没有方法签名。LLM 翻译 `reader.read()` 时，`JavaIoReader` interface 里根本没声明 `read()` 方法，编译必炸。这跟 LLM 翻译质量无关——骨架本身就缺方法。
- **类型未映射（20%）**：当时的基础类型映射没有覆盖 `Char`→`Rune`、`null`→`Option.None`、`Objects` 等情况，骨架里保留了 Java 原名；现在统一由 `java_base_type_map.json` 维护基础映射。
- **enum 处理（10%）**：`create_skeleton.py` 把 Java enum 值翻译成类的非静态成员，但 LLM 按 Java 静态方式 `TokenType.INVALID` 访问。

**对消融对比无影响**：类别 1+2+4 在所有 5 组 ablation 里同等存在，不产生组间差异。
