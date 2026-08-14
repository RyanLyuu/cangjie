---
id: CJ-OVL-001
tags: overload, function, parameter-count, parameter-type
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_overloading.md:3-21
fact: 同名函数仅在参数个数不同或同个数但参数类型不同时构成重载。
rule: Java 方法重载按映射后的 Cangjie 参数序列重新检查；仅返回类型不同不能区分重载。
valid: f(Int64); f(Float64); f(Int64,Float64)
invalid: f():Int64 and f():String
---
id: CJ-OVL-002
tags: generic-overload, constraints, duplicate-definition
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_overloading.md:23-34
fact: 泛型函数重载判断会统一重命名类型形参；类型变元约束不参与是否重载判断。
rule: Java 泛型方法仅 bound 不同而参数结构相同，目标中是重复定义，不得保留为重载。
valid: f<X,Y>(a:X,b:Y) and f<Y,X>(a:X,b:Y) when normalized parameter structures differ
invalid: f<T>(a:T) where T<:I1 and f<T>(a:T) where T<:I2
---
id: CJ-OVL-003
tags: constructor, overload, primary-constructor, init
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_overloading.md:36-75
fact: 同一类型内参数不同的 init 构造函数重载；主构造函数与 init 视为同名并可按参数区分。
rule: Java constructor overload 保留为不同参数列表的 init/主构造；映射后冲突时必须重构。
valid: init(Int64); init(Int64,Float64)
invalid: two init with identical mapped parameter types
---
id: CJ-OVL-004
tags: static, instance, overload, forbidden
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_overloading.md:109-143
fact: class/interface/struct 内 static 与 instance 函数之间不能重载；enum constructor/static/instance 之间不能重载。
rule: Java static/instance 同名集合映射后若仅靠参数形成重载，目标需重命名或重新组织。
valid: distinct names for static and instance members
invalid: static f(Int64) plus instance f(Float64) in same type
---
id: CJ-OVL-005
tags: function-variable, overload, declaration
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_overloading.md:109-132
fact: 只有函数声明引入重载；函数类型变量之间不构成重载；变量与函数不能同名。
rule: Java field/callable object与方法同名时不能依赖目标函数重载机制消歧。
valid: function declarations with overloadable signatures
invalid: var f:(Int64)->Unit plus func f(Float64)
---
id: CJ-OVL-006
tags: overload-resolution, scope, shadowing
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_overloading.md:145-174
fact: 重载决议先选择最高作用域级别；内层作用域优先于外层，即使外层参数更具体。
rule: Java 名称解析迁移后检查嵌套函数/局部声明是否改变候选集优先级。
valid: inner overload selected before outer overload
invalid: 只按参数最具体选择，忽略作用域级别
---
id: CJ-OVL-007
tags: overload-resolution, most-specific, ambiguity
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_overloading.md:174-197
fact: 最高作用域仍有多个候选时选择唯一最匹配函数；无唯一最匹配则报错。
rule: 映射后的实参/形参子类型变化可能改变 Java 重载选择；生成调用前重算 Cangjie 候选。
valid: g(Sub) selected over g(Base) for Sub argument in same scope
invalid: ambiguous candidates resolved arbitrarily
---
id: CJ-OVL-008
tags: named-parameter, default-parameter, call-signature
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/define_functions.md:19-57; manual/source_zh_cn/function/call_functions.md:53-98
fact: 命名参数写 p!:T，可有默认值且调用顺序可变；只有命名参数可有默认值；非命名参数必须排在命名参数前。
rule: Java overload 合并为默认参数仅在调用集合与二义性保持时进行；调用命名参数必须使用 p:value。
valid: func f(a:Int64,b!:Int64=2); f(1); f(1,b:3)
invalid: default on unnamed parameter; named parameter before unnamed declaration
---
id: CJ-OVL-009
tags: enum-constructor, call-operator, priority
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/operator_overloading.md:152-171
fact: enum 构造器形式与 () 操作符重载形式都满足时，优先匹配构造器。
rule: enum 名称调用冲突不能按普通函数重载直觉处理；必要时使用类型限定构造器。
valid: EnumType.Constructor(args)
invalid: 假定 enum call operator 优先于同形构造器
