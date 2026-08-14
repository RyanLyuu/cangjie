---
id: CJ-GEN-001
tags: generic, type-parameter, function, class, interface, struct, enum
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_overview.md:3-15
fact: function、class、interface、struct、enum 均可声明类型形参；类型形参写在声明名后的尖括号中。
rule: 保留 Java 泛型声明的类型参数结构；函数类型参数移到 func 名称之后。
valid: func id<T>(value: T): T; class Box<T>
invalid: enum 不支持泛型；func <T> id(...)
---
id: CJ-GEN-002
tags: generic-constraint, where, subtype, upper-bound
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_constraint.md:3-17
fact: 泛型约束写作 where T <: Bound；不同类型变元约束用逗号分隔；同一变元多个约束用 & 连接。
rule: Java T extends Bound 的声明级对应形式为 where T <: MappedBound。
valid: class Box<T> where T <: ToString
invalid: class Box<T extends ToString>; 把 where 子句塞进字段类型表达式
---
id: CJ-GEN-003
tags: generic-bound, class-bound, interface-bound, multiple-bounds
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_constraint.md:116-118
fact: 类型变元约束只能是具体 class 或 interface；多个 class 上界必须位于同一继承链。
rule: 映射 Java 交叉上界前验证每个目标上界的种类；不能把任意类型表达式写为 Cangjie bound。
valid: where T <: Base & Printable
invalid: where T <: (Int64)->Unit; 不相关的多个 class 上界
---
id: CJ-GEN-004
tags: invariance, generic-subtype, variance, collection
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_subtype.md:15-40
fact: 所有用户自定义泛型类型在类型参数处不型变；D <: C 不推出 I<D> <: I<C>。
rule: 不使用 Java 元素子类型关系扩大 Cangjie 容器类型。
valid: I<D> 仅赋给 I<D>
invalid: ArrayList<D> => ArrayList<C> because D <: C
---
id: CJ-GEN-005
tags: variance, function-type, tuple, covariance, contravariance
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_subtype.md:28-38
fact: 内建 tuple 对元素协变；内建函数类型对参数逆变、对返回值协变；这两者是用户泛型不型变规则的例外。
rule: 仅对函数类型和 tuple 应用已声明的型变，不推广到 Array/List/Map/Set。
valid: function parameter contravariance; function return covariance
invalid: class Producer<out T>; class Consumer<in T>; List<~T>
---
id: CJ-GEN-006
tags: Java-wildcard, extends, super, existential, refactor
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_subtype.md:26-40
fact: Corpus 1.0.0 未定义 Java 风格 wildcard、<~T> 投影或用户泛型 in/out 声明。
rule: ?、? extends、? super 不得直接生成 <~T>/in/out；保留为待重构 occurrence。仅在整体签名验证后可引入新方法类型参数。
valid: mapping_status=preserved; note=wildcard requires signature redesign
invalid: ? super T => ~T; ? extends T => out T
---
id: CJ-GEN-007
tags: wildcard-return, caller-selected, existential
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_function.md:1-40
fact: Cangjie func get<T>() 中 T 是函数类型形参；调用者可参与确定 T，不等同 Java 返回值中的隐藏 wildcard 类型。
rule: 禁止把 Java List<?> 返回类型机械改为 func get<T>(): List<T>。
valid: preserve List<?> and request API redesign
invalid: List<?> get() => func get<T>(): ArrayList<T>
---
id: CJ-GEN-008
tags: raw-type, Any, missing-type-argument, invariance
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_overview.md:7-27; manual/source_zh_cn/generic/generic_subtype.md:26-40
fact: 泛型实例使用具体类型实参；用户泛型不型变。
rule: Java raw List/Map 缺失类型实参时不得默认补 Any 并宣称等价；标记 preserved/unknown，等待源使用点证据。
valid: raw List => preserved
invalid: raw List => ArrayList<Any> unconditionally
---
id: CJ-GEN-009
tags: HashMap, HashSet, TreeMap, TreeSet, constraint
source: CangjieCorpus@3573e3d libs/std/collection/collection_package_api/collection_package_class.md:1320,1839,2800,3276
fact: HashMap<K,V>/HashSet<T> 要求 Hashable 与 Equatable；TreeMap<K,V>/TreeSet<T> 要求 Comparable。
rule: 直接类型映射可记录目标约束风险，但 baseline 不求解、不替换类型参数，constraint_checks 保持 0。
valid: HashMap<Any,String> + note=unverified key bound
invalid: Any => AnyHashable；声称 Any 已满足 HashMap key bound
---
id: CJ-GEN-010
tags: AnyHashable, unsupported, legacy-rule
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_constraint.md:15-24; libs/std/core/core_package_api/core_package_interfaces.md:606-609
fact: Corpus 定义 Hashable 接口；Corpus 1.0.0 未提供 AnyHashable 类型声明。
rule: 不生成 AnyHashable 作为 Java Object 键的自动擦除包装。
valid: preserve source key or use evidence-proven concrete Hashable type
invalid: Map<Object,V> => HashMap<AnyHashable,V>
