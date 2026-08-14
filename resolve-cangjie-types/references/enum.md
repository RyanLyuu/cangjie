---
id: CJ-ENUM-001
tags: enum, algebraic-data-type, constructor, payload
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/enum.md:3-21
fact: Cangjie enum 是代数数据类型；枚举所有构造器；构造器可无参或携带多个参数。
rule: Java 常量 enum 可用无参构造器；Java sealed hierarchy/variant payload 可在语义匹配时用有参构造器重构。
valid: enum Color {| Red | RGB(UInt8,UInt8,UInt8)}
invalid: 把有状态 Java enum 常量仅映射成无参值并丢字段
---
id: CJ-ENUM-002
tags: enum-constructor, overload, arity
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/enum.md:23-32
fact: 同一 enum 可有同名构造器，但参数个数必须不同；无参构造器参数个数视为 0。
rule: 仅按 arity 区分同名构造器；参数类型不同但 arity 相同不能作为构造器重载依据。
valid: Red; Red(UInt8)
invalid: Red(Int64); Red(String)
---
id: CJ-ENUM-003
tags: non-exhaustive-enum, ellipsis, wildcard
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/enum.md:34-42; manual/source_zh_cn/enum_and_pattern_match/match.md:39-55
fact: enum 最多一个匿名 ... 构造器且必须最后；non-exhaustive enum 匹配必须有可覆盖全部构造器的模式。
rule: 开放演化的 Java enum/API 可考虑 ...；所有 match 加 _ 或绑定兜底。
valid: enum E {| A | ...}; match(e){case A=>... case _=>...}
invalid: 直接匹配 ...；non-exhaustive match without fallback
---
id: CJ-ENUM-004
tags: recursive-enum, recursive-type, ADT
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/enum.md:44-54
fact: enum 支持构造器参数递归引用自身。
rule: Java 表达式树/sealed node hierarchy 可在身份与可变性允许时映射递归 enum。
valid: enum Expr {| Num(Int64) | Add(Expr,Expr)}
invalid: 声称 Cangjie enum 不能递归
---
id: CJ-ENUM-005
tags: generic-enum, Option
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_enum.md:1-22
fact: enum 支持泛型；Option<T> 是标准泛型 enum 示例。
rule: 保留 Java 泛型 variant/enum 的类型参数；不要采用旧规则“enum 不支持泛型”。
valid: enum Result<T> {...}
invalid: erase T because target enum allegedly non-generic
---
id: CJ-ENUM-006
tags: enum-member, function, property, name-conflict
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/enum.md:56-72
fact: enum 体可定义成员函数、操作符函数、属性；构造器/函数/属性之间不能重名；enum 只能定义在顶层。
rule: Java enum 方法可迁移为 enum 成员，但先解决与构造器/属性同名冲突；嵌套 Java enum 需提升/重构。
valid: top-level enum with uniquely named member
invalid: constructor and function same name; nested enum declaration
---
id: CJ-ENUM-007
tags: enum-construction, qualification, name-resolution
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/enum.md:74-120
fact: enum 无构造函数；值由 Type.Constructor 或可唯一解析的 Constructor(args) 构造；名称冲突时必须类型限定。
rule: 翻译 Java EnumType.VALUE 优先保留 Type.Constructor 限定，避免变量/函数/class 同名解析改变。
valid: RGBColor.Red; RGBColor.Blue(100)
invalid: bare Blue(100) when class/function Blue exists
---
id: CJ-ENUM-008
tags: enum-pattern, destructuring, payload
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/pattern_overview.md:319-349
fact: enum 模式按构造器名和逐位置 payload 模式匹配；类型前缀可省略。
rule: Java instanceof+cast 的 variant 分派可在重构为 enum 后使用构造器模式直接解构 payload。
valid: case Year(n)=>...
invalid: 仅比较构造器名却忽略需要保留的 payload
---
id: CJ-ENUM-009
tags: match, exhaustive, enum, wildcard
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/match.md:25-55; manual/source_zh_cn/enum_and_pattern_match/pattern_overview.md:372-409
fact: match 必须穷尽；enum match 必须覆盖全部构造器或使用 _；按 case 顺序首个匹配执行。
rule: Java switch enum 翻译需覆盖所有构造器；default 可映射 _；不能依赖 Java fall-through。
valid: match(c){case Red=>... case Green=>... case _=>...}
invalid: non-exhaustive match; implicit fall-through between cases
---
id: CJ-ENUM-010
tags: match-type, least-common-supertype, expression
source: CangjieCorpus@3573e3d manual/source_zh_cn/enum_and_pattern_match/match.md:144-152
fact: 有上下文时各 case 结果须为上下文类型子类型；无上下文时 match 类型为各分支最小公共父类型；值未使用时为 Unit。
rule: Java switch expression 翻译后统一各分支结果类型；语句 switch 不强制制造返回值。
valid: let s:String=match(e){...}
invalid: branches with no common/context-compatible target type
