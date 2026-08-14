---
id: CJ-MUT-001
tags: let, var, initialization, assignment
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_programming_concepts/program_structure.md:80-103
fact: let 变量仅可赋值一次（初始化）；var 可多次赋值。
rule: Java final 局部/字段通常选择 let；存在重新赋值时选择 var；对象内部可变性另行判断。
valid: final int x => let x:Int32
invalid: Java reassigned local => let
---
id: CJ-MUT-002
tags: initialization, local, field, global, static
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_programming_concepts/program_structure.md:85-181
fact: 全局变量和静态成员必须在声明时初始化；局部/实例成员可暂不初始化但必须标类型且在读取前完成初始化。
rule: Java static 未显式初始化依赖默认值时，在 Cangjie 声明或 static init 中生成显式初值。
valid: static let count:Int64=0
invalid: static let count:Int64 without static initializer
---
id: CJ-MUT-003
tags: constructor, definite-initialization, class, struct
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/class.md:115-160; manual/source_zh_cn/struct/define_struct.md:75-116
fact: class/struct 普通 init 必须初始化所有未初始化实例成员；多个 init 必须构成重载。
rule: Java 字段默认初始化需在每条目标构造路径显式满足 definite initialization。
valid: init(){this.x=0}
invalid: constructor exits with uninitialized field
---
id: CJ-MUT-004
tags: static-init, class, struct, one-only
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/class.md:82-113; manual/source_zh_cn/struct/define_struct.md:44-73
fact: class/struct 最多一个 static init；其中必须初始化全部未初始化静态成员；static init 不带访问修饰符。
rule: 合并 Java 多个 static initializer block 的顺序内容到一个目标 static init。
valid: static init(){a=...;b=...}
invalid: multiple static init; public static init
---
id: CJ-MUT-005
tags: value-type, reference-type, copy, alias
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_programming_concepts/program_structure.md:264-275
fact: class/Array 等为引用类型，struct 与其他基础类型多为值类型；值赋值通常复制，引用赋值共享对象。
rule: Java 对象身份/别名语义需要 class 或已知引用类型；不要用普通 struct 替代可共享可变对象。
valid: shared mutable Java object => class
invalid: shared mutable Java object => struct with assumed aliasing
---
id: CJ-MUT-006
tags: let-reference, object-mutation, final-reference
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_programming_concepts/program_structure.md:270-275; manual/source_zh_cn/class_and_interface/class.md:490-516
fact: let 限制引用关系不再赋值，但所引用对象仍可通过 var 成员修改；class 别名共享修改。
rule: Java final reference 可映射 let，且不意味着对象深度不可变。
valid: let obj=MutableClass(); obj.field=1
invalid: 把 final reference 推断为 immutable object
---
id: CJ-MUT-007
tags: struct, mutation, mut-function, this
source: CangjieCorpus@3573e3d manual/source_zh_cn/struct/mut.md:1-37
fact: 普通 struct 实例方法不能修改实例；mut func 内 this 可原地修改字段；mut 不能修饰 static。
rule: Java 值对象方法需要修改目标 struct 时标记 mut；class 方法不使用 mut。
valid: public mut func increment(){i+=1}
invalid: public func increment(){i+=1} on struct; mut static func
---
id: CJ-MUT-008
tags: mut, interface, implementation
source: CangjieCorpus@3573e3d manual/source_zh_cn/struct/mut.md:67-97
fact: interface 可声明 mut；struct 实现必须保持 mut 一致；非 struct 实现不得写 mut；struct 转 interface 为拷贝语义。
rule: 翻译 Java 接口可变操作时按目标实现种类决定 mut，并警惕 struct 装箱到接口后的拷贝行为。
valid: struct implementation uses same mut modifier
invalid: class implementation declares mut; expect interface call to mutate original struct variable
---
id: CJ-MUT-009
tags: mut, let-struct, first-class, escape
source: CangjieCorpus@3573e3d manual/source_zh_cn/struct/mut.md:125-176
fact: let 声明的 struct 不能调用其 mut 方法；struct 实例的 mut 方法不能作为一等公民逃逸，只能调用。
rule: 需要调用 mut 的 struct 局部使用 var；Java method reference 指向 mut 方法时重构为非逃逸调用/其他状态模型。
valid: var s=Foo(); s.f()
invalid: let s=Foo(); s.f(); let fn=s.f
---
id: CJ-MUT-010
tags: const, deep-const, immutable
source: CangjieCorpus@3573e3d manual/source_zh_cn/basic_programming_concepts/program_structure.md:223-253
fact: const 必须声明时初始化且具有深度 const 语义；约束强于 let；扩展中不能定义 const 变量。
rule: Java final 不自动映射 const；仅编译期常量且满足 const 上下文限制时使用 const。
valid: compile-time constant => const
invalid: arbitrary Java final object => const
