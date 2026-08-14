# 规则库提升实施文档


## 具体实施思路

### 1. `fallback_type_for()` 重构

**文件**：`src/java/type_resolution/translate_type_rag.py`

**修改**：将原来的简单函数：
```python
def fallback_type_for(source_type):
    if source_type and source_type.endswith('[]'):
        return 'Array<Any>'
    return 'Any'
```
改为 8 级优先级查表：
1. 类型参数检测（`T`, `E`, `K`, `V` 等 → 保留原样）
2. 数组类型（`T[]` → `Array<Any>`）
3. 嵌套类查表（`Map.Entry` → `MapEntry`）
4. primitive_map 静态查表（`ThreadFactory` → `() -> Thread`）
5. 函数式接口查表（`Function<String, Integer>` → `(String) -> Int32`）
6. 容器裸名查表（`Deque` → `ArrayDeque`）
7. 容器泛型查表（`HashMap<String, Object>` → 解析）
8. 默认 → `Any`

**新增辅助函数** `_is_type_parameter(source_type)` 检测 Java 类型参数标识符。

### 2. 类型参数保留

**问题**：`T → Any | cached` 导致泛型类型参数在仓颉代码中丢失。

**解决**：`_is_type_parameter()` 识别以下模式为类型参数（保留原样，不映射为 Any）：
- 单个大写字母：`T`, `E`, `K`, `V`, `U`, `R`
- 全大写短标识符（≤3 字符）：`ABC`, `XY`（常见类型参数命名）
- 带尖括号的模式：`<K, V>`（类型参数声明）

### 3. `primitive_map.json` 扩展

**文件**：`generics_rule_lib/primitive_map.json`

**修改**：从 44 条扩展，新增覆盖：

- **容器接口→实现映射**：`Deque → ArrayDeque`, `SortedSet → TreeSet`, `SortedMap → TreeMap`, `NavigableSet → TreeSet`, `NavigableMap → TreeMap`, `Queue → ArrayQueue`
- **遗留容器映射**：`Vector → ArrayList`, `Stack → ArrayList`, `Hashtable → HashMap`, `Dictionary → HashMap`
- **并发容器**：`ConcurrentMap → ConcurrentHashMap`, `BlockingQueue → ArrayBlockingQueue`, `CopyOnWriteArrayList → ArrayList`
- **IO 流**：`InputStream`, `OutputStream`, `Reader`, `Writer`, `BufferedReader`, `BufferedWriter` 等
- **时间类型**：`Instant → Instant`, `LocalDate → DateTime`, `Duration → Duration` 等
- **函数式接口（裸名/无泛型）**：`Runnable → () -> Unit`, `Callable → () -> V`
- **并发工具**：`Future`, `ExecutorService`, `CountDownLatch`, `Semaphore` 等
- **其他 JDK 类型**：`StringTokenizer → Iterable<String>`, `Scanner → Iterator<String>`, `Void → Unit` 等

### 4. `functional_interface_map.json` 新建

**文件**：`generics_rule_lib/functional_interface_map.json`（新建）

**内容**：33 条 Java 函数式接口 → 仓颉函数类型的映射，支持泛型参数替换：

- `Function<T, R>` → `(T) -> R`
- `Consumer<T>` → `(T) -> Unit`
- `Supplier<T>` → `() -> T`
- `Predicate<T>` → `(T) -> Bool`
- `BiFunction<T, U, R>` → `(T, U) -> R`
- 原始类型特化：`IntFunction<R>` → `(Int64) -> R`, `DoubleConsumer` → `(Float64) -> Unit` 等
- `Comparator<T>` → `(T, T) -> Int64`
- `ThreadFactory` → `() -> Thread`

**实现**：`GenericsRuleLib.translate_functional_interface()` 方法处理泛型参数替换，将 Java 类型参数位置替换到仓颉函数类型模板中。

eg:

```java
// Function
Function<String, Integer> func = s -> s.length();
Integer len = func.apply("hello");

// Predicate
Predicate<Integer> pred = n -> n > 0;
boolean pos = pred.test(5);

// Supplier
Supplier<Double> sup = () -> Math.random();
Double rand = sup.get();

// Consumer
Consumer<String> cons = s -> System.out.println(s);
cons.accept("Hello");
```

 to cangjie:

```
// 函数类型变量
let func: (String) -> Int = { s => s.size }
let len = func("hello")

let pred: (Int) -> Bool = { n => n > 0 }
let pos = pred(5)

let sup: () -> Float64 = { => Random.nextFloat64() }
let rand = sup()

let cons: (String) -> Unit = { s => print(s) }
cons("Hello")
```



### 5. `nested_class_map.json` 新建

**文件**：`generics_rule_lib/nested_class_map.json`（新建）

**内容**：31 条 Java 嵌套类 → 仓颉扁平名称映射，解决仓颉不支持 `Outer.Inner` 语法的问题：

- `Map.Entry` → `MapEntry`
- `AbstractMap.SimpleEntry` → `MapEntry`
- `AbstractMap.SimpleImmutableEntry` → `MapEntry`
- `Base64.Decoder` → `Any`
- `ForkJoinPool.ForkJoinWorkerThreadFactory` → `() -> Thread`
- `ConcurrentHashMap.KeySetView` → `HashSet`
- `Flow.Publisher/Subscriber/Subscription/Processor` → `Any`

**实现**：`GenericsRuleLib.translate_nested_class()` 方法，支持精确匹配和短名模糊匹配。

### 6. `GenericsRuleLib` 类扩展

**文件**：`src/java/generics_rule_lib/__init__.py`

**修改**：
- 新增 `functional_interface_map` 和 `nested_class_map` 属性及加载逻辑
- 新增 `translate_functional_interface()` 方法：处理带泛型参数的函数式接口解析
- 新增 `translate_nested_class()` 方法：嵌套类名称查表
- 更新 `_load_all()` 加载新数据文件
- 更新文档字符串（4 个集成点 → 明确列出）

### 7. 状态报告改进（budget_exhausted 分支）

**文件**：`src/java/type_resolution/translate_type_rag.py`

**问题**：修改前，所有 `budget_exhausted` 类型都被标记为 `❌ fallback:budget_exhausted`，即使 `fallback_type_for()` 现在通过静态查表返回了有意义的映射（如 `ThreadFactory → () -> Thread`）。

**修改**：在 3 个 fallback 分支（budget\==0、use_llm==false、model_error）中增加判断：

- 如果 `fallback_type != 'Any'`，标记为 `✅ rule_lib:static_map`（有意义映射）
- 否则保持 `❌ fallback:budget_exhausted` / `❌ fallback:model_error` / `❌ fallback:llm_disabled`

**效果**：

```
修改前: [type 076/715] ❌ ThreadFactory -> () -> Thread | fallback:budget_exhausted
修改后: [type 076/715] ✅ ThreadFactory -> () -> Thread | rule_lib:static_map
```

---

## 修改的文件列表

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/java/type_resolution/translate_type_rag.py` | **修改** | 重构 `fallback_type_for()` 增加 7 级优先级查表；新增 `_is_type_parameter()` 类型参数检测 |
| `src/java/generics_rule_lib/__init__.py` | **修改** | 新增 `functional_interface_map`/`nested_class_map` 属性；新增 `translate_functional_interface()`/`translate_nested_class()` 方法；更新 `_load_all()` |
| `generics_rule_lib/primitive_map.json` | **修改** | 从 44 条扩展到 226 条，版本 2.0 → 3.0 |
| `generics_rule_lib/functional_interface_map.json` | **新建** | 33 条函数式接口 → 仓颉函数类型映射 |
| `generics_rule_lib/nested_class_map.json` | **新建** | 31 条嵌套类 → 扁平名称映射 |
| `generics_rule_lib/schema.json` | **修改** | 新增 `functional_interface_map`/`nested_class_map` 文件引用；版本 2.0 → 3.0；更新集成优先级说明 |
| `src/java/type_resolution/translate_type_rag.py` | **修改** | 3 个 fallback 分支增加有意义映射状态判断：`fallback_type != 'Any'` 时标记 `✅ rule_lib:static_map`，否则保持 `❌ fallback:budget_exhausted` |

---

## 类型解析优先级（修改后）

```
1. Custom types (custom_types.json)          ← 项目特定类型
2. Fixed Type Map (fixed_type_map.json)      ← 异常类等确定性映射
3. Java Base Type Map                         ← 版本控制下的规范基础映射
4. Progressive KB (类型映射缓存)              ← RAG 验证过的映射
5. [NEW] Type Parameter Detection             ← T/E/K/V 保留原样
6. [NEW] Nested Class Map                     ← Map.Entry → MapEntry
7. [NEW] Primitive Map (226 entries)          ← JDK 类型静态查表
8. [NEW] Functional Interface Map             ← Function<T,R> → (T) -> R
9. Container Smart Map                        ← HashMap<K,V> 约束推导
10. Generics Rule Lib (45 rules)              ← 规则提示注入
11. Progressive KB Few-Shot                    ← LLM 上下文补充
12. LLM 推理                                   ← 最终 LLM 调用
13. [CHANGED] fallback_type_for()              ← budget_exhausted 时的查表
```

---

## 预期效果

### 场景对比

| Java 类型 | 修改前 `fallback_type_for()` | 修改后 `fallback_type_for()` |
|-----------|-----------------------------|------------------------------|
| `T` | `Any` | `T`（类型参数保留） |
| `ThreadFactory` | `Any` | `() -> Thread`（函数式接口） |
| `Instant` | `Any` | `Instant`（primitive_map） |
| `Vector` | `Any` | `ArrayList`（primitive_map） |
| `BufferedReader` | `Any` | `BufferedReader`（primitive_map） |
| `Map.Entry` | `Any` | `MapEntry`（嵌套类映射） |
| `Deque` | `Any` | `ArrayDeque`（接口→实现） |
| `Function<String, Integer>` | `Any` | `(String) -> Int32`（函数式接口） |
| `HashMap<String, Object>` | `Any` | `HashMap<String, Any>`（容器映射） |

---

