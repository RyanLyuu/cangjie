---
id: CJ-NULL-001
tags: nullability, Option, optional, nullable, question-mark
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/option_type.md:3-18
fact: Option<T> 是包含 Some(T) 与 None 的泛型 enum；?T 与 Option<T> 等价。
rule: 仅当 Java occurrence 有可空证据时，把基础类型 T 渲染为 ?T；?T 表示一个真实 Option 类型层。
valid: String + nullable => ?String; Option<String> + nullable => ?Option<String>
invalid: 把 ?T 当作不进入类型系统的 nullable 注解；自动删除嵌套 Option 层
---
id: CJ-NULL-002
tags: Option, Some, contextual-wrap, implicit-wrap, conversion
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/option_type.md:31-39
fact: 当上下文明确要求 Option<T> 时，可直接提供 T，编译器以 Some 包装；该行为不是类型转换。
rule: 不因调用点可直接传 T 而把签名中的 Option<T> 简化为 T。
valid: let x: Option<Int64> = 100
invalid: Option<T> => T
---
id: CJ-NULL-003
tags: None, type-inference, generic-constructor, Option
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/option_type.md:41-48
fact: 无明确上下文类型时，None 不能推断目标 Option 类型；使用 None<T> 构造 Option<T>。
rule: 生成无上下文的空 Option 表达式时保留显式类型实参。
valid: let x = None<String>
invalid: let x = None
---
id: CJ-NULL-004
tags: Optional, Option, nested-option, semantic-absence, reference-nullability
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_enums.md:163-166,442-445
fact: Option<Option<T>> 是合法且可由 flatten() 显式压平的独立类型。
rule: Java Optional<T> 的“无值”语义映射为 Option<T>；若 Optional 引用本身可为 null，外加一层 Option，禁止自动 flatten。
valid: @Nullable Optional<String> => ?Option<String>
invalid: @Nullable Optional<String> => Option<String>
---
id: CJ-NULL-005
tags: nullable-evidence, Java-annotation, null-return, null-initializer
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/option_type.md:3-18
fact: Cangjie 可空表示必须落实为 Option 类型；Corpus 不提供 Java 默认可空性推断规则。
rule: Java primitive/void => not-applicable；显式 Nullable、null 初始化或 return null => nullable；无证据引用类型 => unknown。
valid: @Nullable String => status=nullable,cangjie=?String; String with no evidence => status=unknown
invalid: 所有 Java 引用默认 non-null；所有 Java 引用默认 nullable
---
id: CJ-NULL-006
tags: non-null-evidence, Java-annotation, requireNonNull, precondition
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/option_type.md:18-31
fact: T 与 Option<T> 是不同类型；选择 T 必须来自源契约证据，而非目标语法偏好。
rule: 仅以明确 NonNull/NotNull 契约或已验证 API 前置条件标记 non-null；Objects.requireNonNull 仅说明失败前置条件，不自动证明调用者可传 null。
valid: @NonNull String => status=non-null,cangjie=String
invalid: dereference/constructor/final/requireNonNull 出现 => 无条件 non-null
---
id: CJ-NULL-007
tags: Option-api, isSome, isNone, map, flatMap, filter, getOrThrow
source: CangjieCorpus@3573e3d libs/std/core/core_package_api/core_package_enums.md:194-313
fact: Option<T> 提供 filter、flatMap、getOrDefault、getOrThrow、isNone、isSome。
rule: 仅在方法体翻译阶段使用这些 API；类型解析阶段只确定 Option 类型层，不重写调用。
valid: Optional<T> type => Option<T>
invalid: 在 occurrence 类型记录中嵌入 Optional 方法体改写
---
id: CJ-NULL-008
tags: nullability-conflict, unknown, evidence
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/option_type.md:18-31
fact: ?T/Option<T> 的选择改变静态类型。
rule: Java nullable 与 non-null 证据冲突时保留全部证据并输出 unknown；不得任意选择 ?T 或 T。
valid: conflicting annotations => status=unknown
invalid: conflicting annotations => nullable/non-null without resolution
