---
id: CJ-EXT-001
tags: class, inheritance, open, sealed, single-inheritance
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/class.md:543-585
fact: 非抽象 class 仅在 open 时可继承；class 使用 <: 继承且只支持单 class 继承；未声明父类时直接父类为 Object。
rule: Java class extends 映射为单一 class <:；多个 Java interface 不占 class 单继承名额。
valid: open class Base {}; class Sub <: Base {}
invalid: class C <: A & B where A/B are classes
---
id: CJ-EXT-002
tags: interface, implements, multiple-interface, ampersand
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/interface.md:302-373
fact: 类型可用 & 实现多个接口；接口可继承多个接口但不能继承 class；实现子接口也实现其所有父接口。
rule: Java implements I1,I2 映射为 <: I1 & I2；先区分 class 父类与 interface 父类型。
valid: class C <: Base & I1 & I2
invalid: interface I <: SomeClass
---
id: CJ-EXT-003
tags: interface-implementation, signature, covariant-return, mut
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/interface.md:415-451
fact: 接口实现要求函数名、参数列表、返回类型相同；当接口返回 class 时允许实现返回其子 class；属性类型与 mut 必须匹配。
rule: Java override/implements 签名映射后逐项保持；仅对 class 返回类型使用已文档化的协变返回例外。
valid: interface f(): Base; implementation f(): Sub where Sub <: Base
invalid: implementation changes parameter type; arbitrary struct return covariance
---
id: CJ-EXT-004
tags: override, instance-method, open, dynamic-dispatch
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/class.md:706-738
fact: 非抽象实例方法被覆盖时父方法须 open；子方法 override 可省略；调用按运行时类型动态派发。
rule: Java 可覆盖实例方法需要目标父方法 open；保留动态派发，不改成 static/redef。
valid: public open func f(); public override func f()
invalid: 用 redef 覆盖实例方法；覆盖非 open 父实例方法
---
id: CJ-EXT-005
tags: redef, static-method, hiding, static-dispatch
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/class.md:740-768
fact: 子类重定义父类静态函数使用 redef（可省略）；调用版本由 class 类型决定，不动态派发。
rule: Java static method hiding 映射为目标静态重定义语义；不得使用 override。
valid: public redef static func foo()
invalid: public override static func foo()
---
id: CJ-EXT-006
tags: override, named-parameter, generic-constraint
source: CangjieCorpus@3573e3d manual/source_zh_cn/class_and_interface/class.md:770-834
fact: 被覆盖函数有命名形参时实现必须保留同名命名形参；泛型 override/redef 的类型变元约束必须相同或更宽松。
rule: Java 签名转为命名参数后，整个继承链使用同一名字；不得在子方法收紧 generic bound。
valid: parent f(a!:Int32); child f(a!:Int32)
invalid: child f(b!:Int32); child where T <: Sub when parent where T <: Base
---
id: CJ-EXT-007
tags: extend, direct-extension, interface-extension, restrictions
source: CangjieCorpus@3573e3d manual/source_zh_cn/extension/extend_overview.md:3-21
fact: extend 可为可见的非函数/非元组/非接口类型添加函数、属性或实现接口；不能增加成员变量；成员必须有实现；不能 open/override/redef；不能访问 private。
rule: Java 静态辅助/扩展式 API 可考虑 extend；需要新增状态字段或虚方法时不能用 extend。
valid: extend String { public func helper():Unit {} }
invalid: extend String { var state:Int64 }; override member in extension
---
id: CJ-EXT-008
tags: generic-extension, constraint, specialized-extension
source: CangjieCorpus@3573e3d manual/source_zh_cn/extension/direct_extension.md:36-96
fact: 可扩展完全实例化泛型类型，也可用 extend<T> 扩展未完全实例化类型；扩展类型与约束完全匹配时成员才可用。
rule: Java 泛型 utility 迁移到扩展时显式声明所有被使用类型参数与 where 约束。
valid: extend<T> MyList<T> where T <: ToString { ... }
invalid: extend MyList {}; 声明未用于被扩展类型的多余类型参数
---
id: CJ-EXT-009
tags: orphan-rule, interface-extension, package
source: CangjieCorpus@3573e3d manual/source_zh_cn/extension/access_rules.md:62-84
fact: 禁止孤儿接口扩展：接口扩展必须与被扩展类型或接口继承链中的接口至少一方同包。
rule: 为第三方 Java 类型实现第三方接口前检查 Cangjie package 所有权；不满足时使用适配器/包装类型。
valid: extension located with local type or local interface
invalid: package c extends package-a Foo <: package-b Bar
---
id: CJ-EXT-010
tags: extension-shadowing, this, super, member-conflict
source: CangjieCorpus@3573e3d manual/source_zh_cn/extension/access_rules.md:87-150
fact: 扩展实例成员可用 this、不能用 super；不能遮盖原类型成员或其他扩展成员；同包可多次扩展。
rule: 生成扩展前做成员名冲突检查；需要 super 调用的 Java override 不能迁移为扩展。
valid: unique extension member using this
invalid: extension member shadows existing member; super.foo() in extension
