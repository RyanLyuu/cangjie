---
id: CJ-FUN-001
tags: function-type, syntax, arrow, first-class
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/first_class_citizen.md:1-49
fact: 函数是一等公民；函数类型写作 (T1,T2)->R；零参数写作 ()->R。
rule: Java SAM 仅在无需保留 nominal interface 身份时映射为相同参数/返回形状的 Cangjie 函数类型。
valid: Runnable.run():void => ()->Unit; Function<T,R>.apply(T):R => (T)->R
invalid: 保留 Java Function<T,R> 名称作为 Cangjie 标准函数类型
---
id: CJ-FUN-002
tags: function-type, associativity, higher-order
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/first_class_citizen.md:75-102
fact: 函数类型可作为参数和返回类型；-> 右结合。
rule: 高阶函数映射时按右结合解析，必要时用括号明确参数位置的函数类型。
valid: () -> (Int64,Int64) -> Int64
invalid: 把返回函数误解析为具有额外参数的单个函数
---
id: CJ-FUN-003
tags: function-variance, contravariance, covariance, subtype
source: CangjieCorpus@3573e3d manual/source_zh_cn/generic/generic_subtype.md:28-38
fact: 内建函数类型对入参逆变、对返回值协变。
rule: 判断 Java callback 赋值兼容性时按目标函数型变，不按用户泛型不型变处理。
valid: broader parameter / narrower class return where subtype relation holds
invalid: 假定函数参数协变
---
id: CJ-FUN-004
tags: lambda, syntax, inference, return-type
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/lambda.md:3-20,31-88
fact: Lambda 写作 { p:T => body }；=> 通常不可省略；参数可从变量/调用上下文推断；Lambda 不能声明返回类型，返回类型由上下文/主体推断。
rule: Java lambda 移除显式返回类型声明；在重载或上下文不足时保留参数类型标注。
valid: {x:Int64 => x+1}
invalid: (x:Int64):Int64 => x+1; {x} without => outside trailing lambda
---
id: CJ-FUN-005
tags: trailing-lambda, call-syntax, last-parameter
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/function_call_desugar.md:3-39
fact: 最后一个形参为函数类型且对应实参为 lambda 时可使用尾随 lambda；唯一 lambda 实参时可省略圆括号。
rule: 尾随 lambda 仅作为调用语法改写，不改变函数签名或重载身份。
valid: f(arg) {x => body}; f {x => body}
invalid: 非最后一个 callback 实参移到括号外
---
id: CJ-FUN-006
tags: closure, capture, initialization, scope
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/closure.md:1-28
fact: 函数/lambda 捕获外部局部变量形成闭包；被捕获变量在闭包定义时必须可见且已初始化。
rule: Java lambda 捕获迁移时保证目标变量声明和初始化位于闭包定义之前。
valid: let n=1; let f={=>n}
invalid: let f={=>n}; let n=1
---
id: CJ-FUN-007
tags: closure, var-capture, escape, first-class
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/closure.md:85-129
fact: 捕获 var 局部变量的闭包只能被调用，不能赋值、作为实参、返回值或普通表达式；捕获限制具有传递性。
rule: Java 可逃逸的 mutable-local closure 不能机械映射；改用引用对象字段、显式状态对象或重构。
valid: immediately invoke closure capturing var
invalid: return/assign/pass closure capturing local var
---
id: CJ-FUN-008
tags: functional-interface, nominal-identity, default-method, SAM
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/first_class_citizen.md:1-5; manual/source_zh_cn/class_and_interface/interface.md:415-499
fact: Cangjie 函数类型与 interface 是不同类型机制；interface 可有成员与默认实现。
rule: Java functional interface 有额外成员、默认方法、类型测试或 nominal API 身份时保留/重建 interface，不降为裸函数类型。
valid: pure SAM usage => function type
invalid: Comparator object with default/identity semantics => bare function without review
---
id: CJ-FUN-009
tags: Consumer, Predicate, Supplier, BiFunction, callable-shape
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/first_class_citizen.md:1-49
fact: Cangjie 函数类型可精确表达零/一/多参数和 Unit/Bool/任意返回类型。
rule: 已验证纯 SAM 时：Supplier<T>=()->T；Consumer<T>=(T)->Unit；Predicate<T>=(T)->Bool；BiFunction<T,U,R>=(T,U)->R。
valid: Callable<V> pure SAM => ()->V
invalid: 只凭简单类名把项目自定义 Consumer 映射为函数
---
id: CJ-FUN-010
tags: function-parameter-names, named-parameters, signature
source: CangjieCorpus@3573e3d manual/source_zh_cn/function/first_class_citizen.md:51-72
fact: 函数类型可统一写所有参数名或统一省略；不能部分命名。
rule: Java callback 参数名通常不属于函数类型身份；若保留名称则全部参数统一保留。
valid: (name:String,price:Int64)->Unit; (String,Int64)->Unit
invalid: (name:String,Int64)->Unit
