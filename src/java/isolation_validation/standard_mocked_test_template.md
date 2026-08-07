# Standard Mocked Test Template

这份模板对应当前 `isolation_validation` 流程生成的标准 Cangjie mocked test 结构。

适用场景：

- 有一个 focal method 需要验证
- 可选地包含若干 callee / dependency stub
- 对复杂对象使用 IoC 反射创建实例
- 对 private/protected 状态通过测试专用 getter / setter 访问

约定前提：

- 目标类型在测试侧提供 public 测试构造入口
- 目标类型按字段提供测试专用访问器：
  - 实例字段：`__mockSet<Field>()` / `__mockGet<Field>()`
  - 静态字段：`__mockSetStatic<Field>()` / `__mockGetStatic<Field>()`

---

## 1. 一屏版标准模板

适合直接放进 PPT，一屏展示 mocked test 的主干结构。

```typescript
package <project>.test

import <project>.*
import std.unittest.*
import std.unittest.mock.*
import std.unittest.mock.mockmacro.*
import std.unittest.testmacro.*
import <project>.runtime.*
import std.reflect.*

// runtime support 由生成器注入：
__mockCreateViaIoc<T>()
__mockArrayListOf<T>(), __mockHashMapOf<K, V>(), ...
__mockStringEqual(...), __mockByteStreamEquals(...), ...

@Test
class <MockedTestClassName> {
    @TestCase
    func <mocked_test_case_name>() {
        // 1) stub callee / dependency
        @On(<dependency_signature>).returns(<dependency_return>).once()

        // 2) restore focal receiver
        var instance_initial = __mockCreateViaIoc<<FocalOwnerType>>()
        instance_initial.__mockSet<FieldA>(<field_a_value>)
        instance_initial.__mockSet<FieldB>(<field_b_value>)

        // 3) restore args
        var arg_0 = <arg0_expr>
        var arg_1 = <arg1_expr>

        // 4) invoke focal call
        let method_ret = instance_initial.<focalMethod>(arg_0, arg_1)

        // 5) assert return / receiver / args / static side effect
        @Assert(<return_assertion>)
        @Assert(<receiver_assertion>)
        @Assert(<arg_assertion>)
        @Assert(<static_assertion>)
    }
}
```

---

## 2. 标准模板代码

如果需要展开解释，再展示下面这版“半展开模板”。

```cangjie
package <project>.test

import <project>.*
import std.io.*
import std.collection.*
import std.unittest.*
import std.unittest.mock.*
import std.unittest.mock.mockmacro.*
import std.unittest.testmacro.*
import <project>.runtime.*
import std.reflect.*

// runtime support 由生成器自动注入：
// - __mockCreateViaIoc<T>()
// - __mockArrayListOf<T>(), __mockResetArrayList<T>()
// - __mockHashMapOf<K, V>(), __mockResetHashMap<K, V>()
// - __mockStringEqual(...), __mockByteStreamEquals(...), ...

@Test
class <MockedTestClassName> {
    @TestCase
    func <mocked_test_case_name>() {
        // Step 1: dependency stubs
        @On(<DependencyType>.<dependencyMethod>(<matcher1>, <matcher2>))
            .returns(<dependency_return_expr>)
            .once()

        // Step 2: restore focal receiver
        var instance_initial = __mockCreateViaIoc<<FocalOwnerType>>()
        instance_initial.__mockSet<FieldA>(<field_a_value>)
        instance_initial.__mockSet<FieldB>(<field_b_value>)

        // Step 3: restore arguments
        var arg_0 = <arg0_expr>
        var arg_1 = <arg1_expr>

        // Step 4: invoke focal method
        let method_ret = instance_initial.<focalMethod>(arg_0, arg_1)

        // Step 5: assert return value
        @Assert(method_ret.<or_getter_expr> == <expected_return>)

        // Step 6: assert receiver final state
        @Assert(instance_initial.__mockGet<FieldA>() == <expected_field_a>)
        @Assert(instance_initial.__mockGet<FieldB>() == <expected_field_b>)

        // Step 7: assert argument side effects
        @Assert(arg_0 == <expected_arg0>)
        @Assert(arg_1 == <expected_arg1>)

        // Step 8: assert static side effects if needed
        @Assert(<FocalOwnerType>.__mockGetStatic<StaticField>() == <expected_static_value>)
    }
}
```

---

## 3. 每一段的职责

### 2.1 import block

负责引入：

- 目标项目类型
- 集合 / IO 支持
- unittest / mock 宏
- `<project>.runtime.*`
- `std.reflect`

### 2.2 runtime support

这部分一般由生成器自动注入，包含：

- `__mockCreateViaIoc<T>()`
- 集合构造辅助函数
- 字符串 / 流比较辅助函数

### 2.3 dependency stubs

如果 workflow 含 callee 调用链，则生成：

```cangjie
@On(<signature>).returns(<value>).once()
```

或者多次调用时：

```cangjie
@On(<signature>).returnsConsecutively(v1, v2, v3)
```

### 2.4 focal receiver restore

对复杂对象不直接写构造表达式，而是：

1. 先通过 IoC 创建实例
2. 再通过测试 setter 回放字段状态

示例：

```cangjie
var instance_initial = __mockCreateViaIoc<Ansi>()
instance_initial.__mockSetBuilder("")
instance_initial.__mockSetAttributeOptions(__mockArrayListOf<Any>([]))
```

### 2.5 assertions

断言分三类：

- return value assertion
- receiver final snapshot assertion
- arg final snapshot assertion

如果目标字段是 private，则优先调用：

```cangjie
instance_initial.__mockGetBuilder()
Ansi.__mockGetStaticDetector()
```

---

## 4. 最小可执行模板

适合“无 callee 链”的 mocked test：

```cangjie
package demo.test

import demo.*
import demo.runtime.*
import std.unittest.*
import std.unittest.testmacro.*

private func __mockCreateViaIoc<T>(): T where T <: Object {
    SimpleIoc.default.unregister<T>()
    let instance = SimpleIoc.default.construct<T>()
    SimpleIoc.default.unregister<T>()
    instance
}

@Test
class DemoMockedTest {
    @TestCase
    func test_demo_mocked() {
        let method_ret = DemoService.isDetected()
        @Assert(method_ret == true)
    }
}
```

---

## 5. 标准“有 callee 链”模板

适合“有 dependency stub + 对象状态回放”的 mocked test：

```cangjie
package demo.test

import demo.*
import std.collection.*
import std.unittest.*
import std.unittest.mock.*
import std.unittest.mock.mockmacro.*
import std.unittest.testmacro.*
import demo.runtime.*

private func __mockCreateViaIoc<T>(): T where T <: Object {
    SimpleIoc.default.unregister<T>()
    let instance = SimpleIoc.default.construct<T>()
    SimpleIoc.default.unregister<T>()
    instance
}

private func __mockArrayListOf<T>(items: Array<T>): ArrayList<T> {
    let list = ArrayList<T>(items.size)
    list.add(all: items)
    list
}

@Test
class DemoMockedTest {
    @TestCase
    func test_demo_mocked() {
        @On(DependencyService.isEnabled()).returns(true).once()

        var instance_initial = __mockCreateViaIoc<DemoService>()
        instance_initial.__mockSetBuilder("")
        instance_initial.__mockSetOptions(__mockArrayListOf<Any>([]))

        var arg_0 = "hello"
        let method_ret = instance_initial.render(arg_0)

        @Assert(method_ret.__mockGetBuilder() == "hello")
        @Assert(instance_initial.__mockGetBuilder() == "hello")
    }
}
```

---

## 6. 目标类需要配合提供的测试接口

如果生成器希望完全落到真实实现，目标类建议提供：

```cangjie
public class DemoService {
    private var builder: String = ""
    private static var detector: String = ""

    public init() {}

    public func __mockSetBuilder(value: String) {
        builder = value
    }

    public func __mockGetBuilder(): String {
        builder
    }

    public static func __mockSetStaticDetector(value: String) {
        detector = value
    }

    public static func __mockGetStaticDetector(): String {
        detector
    }
}
```

如果目标类还没有这些接口，可以在测试前临时执行：

```bash
python3 src/java/isolation_validation/add_macro.py apply <target.cj> --class <ClassName>
```

测试结束后再移除：

```bash
python3 src/java/isolation_validation/add_macro.py remove <target.cj> --class <ClassName>
```

这版脚本会在目标目录下安装一个极简 `mockable` 宏包，并通过 `@mockable(...)` 在编译期展开：

- `__mockGet* / __mockSet*`
- `__mockGetStatic* / __mockSetStatic*`

constructor 的策略是：

1. 先让 IoC 使用目标类原本可见的 public/pub 构造器
2. 如果没有可用构造器，再尝试把已有 private/protected 无参构造器改写为 `@mockable(public init() {})`
3. 如果仍然没有入口，则判定该类型当前无法自动测试

---
