# 泛型映射规则库 

## 概述

本规则库是 x2cangjie 项目中 **Java 泛型机制 → 仓颉代码** 翻译的系统化、可执行提示规则集合。覆盖泛型声明、约束转换、通配符处理、型变映射、原始类型恢复、数组/实例化、递归边界、语义差异、需要代码重构的容器/API 模式共 **9 大类 42 条规则**。纯类型表达式映射不再交给 LLM 规则库，而由 `java_base_type_map.json` 与 `type_expression.py` 确定性完成。

---

## 数据结构

### 规则条目格式

每条规则包含以下字段：

```json
{
  "id": "C01",
  "category": "declaration",
  "subcategory": "generic_class",
  "name": "无界泛型类",
  "java_ast_pattern": {
    "node_type": "ClassDeclaration",
    "has_type_parameters": true,
    "constraint_type": "unbounded"
  },
  "java_regex_fallback": "class\\s+(\\w+)\\s*<\\s*([A-Z]\\w*(?:\\s*,\\s*[A-Z]\\w*)*)\\s*>",
  "cangjie_template": "class $1<$2>",
  "transforms": [
    {"from": "...", "to": "...", "scope": "...", "comment": "..."}
  ],
  "constraints": {
    "cangjie_semantics": "仓颉泛型无类型擦除...",
    "requires": ["C07"],
    "conflicts": [],
    "action": "需执行的动作（可选）"
  },
  "priority": 10,
  "example": {
    "java": "class Box<T>",
    "cangjie": "class Box<T>",
    "note": "直接迁移"
  },
  "validation_probes": ["cjpm build 是否通过"]
}
```

**关键字段说明**：

| 字段 | 说明 |
|---|---|
| `id` | 规则唯一标识，格式 `C{NN}` |
| `category` | 大类：declaration / constraint / wildcard / variance / raw_type / array_instantiation / advanced / semantic_gap / container_smart |
| `subcategory` | 子类，如 generic_class, upper_bound, unbounded_wildcard |
| `java_ast_pattern` | tree-sitter AST 节点匹配模式 |
| `java_regex_fallback` | 正则后备匹配（当前主要使用此字段） |
| `cangjie_template` | 仓颉输出模板，`$1`, `$2` 为捕获组引用 |
| `transforms` | 结构化转换列表，指明每步 from→to 和作用域 |
| `constraints` | 仓颉语义说明、前置规则、冲突规则、需执行动作 |
| `priority` | 匹配优先级，数字越大越优先 |
| `validation_probes` | 编译验证检查项列表 |

### 确定性类型表达式映射

主流程使用 `java_base_type_map.json` 记录 raw type 映射，用 `type_expression.py` 在使用点组合泛型参数，例如 `List<String>` → `ArrayList<String>`、`HashMap<Object, Integer>` → `HashMap<AnyHashable, Int64>`。`type_container_map.json` 仅保留为历史参考/兼容数据，不再作为 LLM prompt 的类型翻译来源。历史容器映射格式如下：

```json
{
  "HashMap": {
    "cangjie": "HashMap",
    "type_args": 2,
    "key_constraints": ["K <: Hashable & Equatable<K>"],
    "notes": "键类型必须满足 Hashable & Equatable<K>",
    "any_key_replacement": "AnyHashable"
  }
}
```

从原来的硬编码 `_HASH_KEY_CONTAINERS `集合(`_HASH_KEY_CONTAINERS = *frozenset*({'HashMap', 'LinkedHashMap', 'TreeMap', 'ConcurrentHashMap'})`)，改为从 `type_container_map.json` 读取配置。

当翻译引擎遇到 `HashMap<Any, V>` 或 `HashSet<Any>` 时，自动将键/元素位的 `Any` 替换为 `AnyHashable`。

**特殊字段**：

| 字段 | 说明 |
|---|---|
| `type_args` | 泛型参数个数（0 表示需重构为非泛型形式） |
| `key_constraints` | 自动推导的约束列表 |
| `any_key_replacement` | 当键/元素类型为 `Any` 时的替换类型 |
| `any_element_replacement` | 同上，用于 Set 容器 |
| `api_transforms` | API 方法映射（如 `isPresent()` → `!= None`） |

---

## 规则分类详解

### 01 — 泛型声明转换（C01-C06）

Java 和仓颉的泛型声明语法高度相似，核心差异在于**约束从句的位置**：

| Java | 仓颉 | 规则 |
|---|---|---|
| `class Box<T>` | `class Box<T>` | C01 直迁 |
| `class Box<T extends Number>` | `class Box<T> where T <: Number` | C02 `extends` → `where <:`
| `class Box<T extends A & B>` | `class Box<T> where T <: A & B` | C03 多约束用 `&` 连接 |
| `interface Transformer<I, O>` | `interface Transformer<I, O>` | C05 直迁 |
| `<T> T get(T t)` | `func get<T>(t: T): T` | C06 类型参数位置迁移 |

**关键点**：仓颉泛型方法的类型参数放在函数名后，参数使用 `name: type` 格式。

### 02 — 约束转换（C07-C11）

Java 使用 `extends` 关键字声明类型参数约束，仓颉使用 `where` 子句和 `<:` 运算符：

```
Java:   <T extends Comparable<T>>
仓颉:   where T <: Comparable<T>
```

**多约束连写**：Java 和仓颉都用 `&` 连接同一类型参数的多个上界：

```
Java:   <T extends Number & Serializable>
仓颉:   where T <: Number & Serializable
```

**仓颉约束的重要限制**：
1. 多个 class 上界必须在同一继承链上
2. F-bound（递归约束）合法：`where T <: Comparable<T>`
3. 多类型参数的约束用 `,` 分隔：`where T <: Number, V <: Serializable`

### 03 — 通配符转换（C12-C17）

**这是翻译中最复杂的区域**。仓颉没有通配符，有三种策略：

| Java 通配符 | 仓颉策略 | 规则 |
|---|---|---|
| `<?>` | 提升为泛型方法参数 `<T>` | C12 |
| `<? extends Upper>` | 泛型方法 `<T> where T <: Upper` | C13 |
| `<? super Lower>` | 逆变投影 `<~Lower>` | C14 |
| 嵌套通配符 | 递归提升泛型参数 | C15 |
| 通配符捕获 | 合并为单个泛型方法 | C16 |
| 返回值通配符 | 提升为泛型方法 | C17 |

**核心策略**：**方法级通配符 → 整体提升为泛型方法**。这是最重要的模式。

```
Java:   void print(List<?> list)
仓颉:   func print<T>(list: List<T>)
```

```
Java:   double sum(List<? extends Number> list)
仓颉:   func sum<T>(list: List<T>): Float64 where T <: Number
```

```
Java:   void addNumbers(List<? super Integer> list)
仓颉:   func addNumbers(list: List<~Integer>)
```

### 04 — 型变映射（C18-C21）

Java 使用**使用处型变**（通配符），仓颉支持**声明处型变**（in/out）和使用处投影（~）：

| 场景 | Java | 仓颉推荐 | 规则 |
|---|---|---|---|
| 生产者 | `? extends T` | 泛型参数 `<U> where U <: T` | C18 |
| 消费者 | `? super T` | `~T` 投影 | C19 |
| 多处生产者 | 反复 `? extends` | 声明 `<out T>`（重构建议） | C20 |
| 多处消费者 | 反复 `? super` | 声明 `<in T>`（重构建议） | C21 |

**重要**：仓颉用户自定义泛型类型**默认不变**。`out`/`in` 是 C20/C21 的重构建议，不是自动转换。

### 05 — 原始类型恢复（C22-C24）

仓颉**不允许省略类型参数**。所有 Java 的原始类型（Raw Type）都需要补上 `<Any>`：

```
Java:   List list = new ArrayList();
仓颉:   let list: List<Any> = ArrayList<Any>()
```

对于 Hash 容器的 `<Any>` 键类型，需要替换为 `<AnyHashable>`（见 C42/C43）。

### 06 — 数组与实例化（C25-C28）

| Java | 仓颉 | 规则 | 难度 |
|---|---|---|---|
| `T[] arr = (T[]) new Object[10]` | `let arr = ArrayList<T>()` | C25 | ⚠️ 自动 |
| `new String[5]` | `Array<String>(5, item: "")` | C26 | ⚠️ 需初始值 |
| `new T()` | 工厂闭包 `() -> T` | C27 | 🔴 需手动 |
| `Class<T>` | `GenericType<T>` 或 `() -> T` | C28 | 🔴 需确认 |

仓颉**禁止泛型实例化**和**泛型数组创建**，这是与 Java 的根本差异。

### 07 — 递归边界与高级模式（C29-C32）

- **递归约束** `T extends Comparable<T>` → `where T <: Comparable<T>`：直迁（C29）
- **Enum 泛型参数**：仓颉 enum 不支持泛型参数，必须重构（C30）
- **自引用泛型** `Node<T extends Node<T>>`：仓颉支持但需编译验证（C31）
- **Class<T> 类型令牌**：需重构为 GenericType 或工厂闭包（C32）

### 08 — 语义差异（C33-C40）

这是最易出错的区域，因为涉及 Java 和仓颉的**根本性语义差异**：

| 差异点 | 说明 | 规则 |
|---|---|---|
| 无类型擦除 | 仓颉泛型具化，`List<String>` 和 `List<Int64>` 是不同类型 | C33 |
| instanceof 泛型 | 仓颉可精确检查，用 `match` 替代 | C34 |
| 泛型异常 | 仓颉异常类不能有泛型参数 | C35 🔴 |
| 静态字段用类型参数 | Java 和仓颉都禁止 | C36 |
| 数组协变 | Java 允许 `String[]` → `Object[]`，仓颉禁止 | C37 |
| 桥方法 | Java 编译器生成，仓颉不需要 | C38 |
| 类型强转 | `(T) obj` → `obj as T` 或 `obj as? T` | C39 |
| 泛型重载 | Java 因擦除冲突，仓颉合法 | C40 ✅ |

### 09 — 容器/API 语义重构（C44-C45）

| Java | 仓颉 | 规则 | 注意事项 |
|---|---|---|---|
| `Stream<T>` | 重构为迭代器 | C44 | 仓颉无 Stream API |
| `CompletableFuture<T>` | `Future<T>` / async | C45 | 并发模型不同 |

`Optional<T>`、`HashMap<K,V>`、`HashSet<T>` 这类类型表达式不再作为 LLM 规则：

- `Optional<T>` → `Option<T>` 由类型映射表和表达式解析完成
- `HashMap<Any, V>` → `HashMap<AnyHashable, V>` 由确定性约束处理完成
- `HashSet<Any>` → `HashSet<AnyHashable>` 由确定性约束处理完成

## 规则优先级规则

匹配时按以下优先级排序：

1. **Priority 10**：声明级规则（C01-C04），最精确
2. **Priority 9**：接口/方法级约束（C05-C08）
3. **Priority 8**：通配符和型变规则（C12-C14, C18-C19, C29）
4. **Priority 7**：原始类型和嵌套（C22-C24, C15, C17, C31, C44）
5. **Priority 6**：数组/实例化和语义优势（C25-C26, C33-C34, C38, C40, C45）
6. **Priority 5**：手动迁移规则和重构建议（C20-C21, C27-C28, C36-C37）
7. **Priority 4**：不支持的特性（C30, C35）

当多条规则同时匹配时，取 priority 最高的。相同 priority 以规则 ID 小的优先。

---

## 文件清单

| 文件 | 说明 |
|---|---|
| `schema.json` | 规则库元数据与版本控制 |
| `primitive_map.json` | Java 原始类型 → 仓颉类型映射 |
| `type_container_map.json` | 容器类型映射 + 约束推导 + API 变换表 |
| `rules/01_declaration.json` | 泛型声明转换（C01-C06） |
| `rules/02_constraint.json` | 约束转换（C07-C11） |
| `rules/03_wildcard.json` | 通配符转换（C12-C17） |
| `rules/04_variance.json` | 型变映射（C18-C21） |
| `rules/05_raw_type.json` | 原始类型恢复（C22-C24） |
| `rules/06_array_instantiation.json` | 数组与实例化（C25-C28） |
| `rules/07_advanced.json` | 递归边界与高级模式（C29-C32） |
| `rules/08_semantic_gap.json` | 语义差异（C33-C40） |
| `rules/09_container_smart.json` | 容器/API 语义重构（C44-C45） |
| `generics_rule_guide.md` | 本文档 |

---

## 运行流程

### 1. 骨架生成阶段 (`create_skeleton.py`)

```
get_cangjie_type("HashMap<String, Object>", type_map)
│
├── type_map 精确匹配？ → 返回
│
├── 含 < 和 > ？ → 尝试规则库容器映射
│   └── lib.translate_container_type("HashMap<String, Object>", type_map)
│       ├── 查找 HashMap → {"cangjie": "HashMap", "any_key_replacement": "AnyHashable"}
│       ├── 递归解析泛型参数: ["String", "Object"] → ["String", "Any"]
│       ├── 检测 Hash 容器: Object 在 key 位置 → 替换为 AnyHashable
│       └── 返回 "HashMap<String, Any>"
│
├── 含 < 和 > ？ → 规则库无匹配 → 原有泛型分解逻辑
│   ├── 基础类型映射
│   ├── Hash 容器 AnyHashable 替换（优先查规则库，fallback 硬编码集合）
│   └── 递归解析子类型
│
├── 以 [] 结尾 → Array<T> 处理
│
└── 未知类型 → "Any"
```

### 2. 类型翻译阶段 (`translate_type_rag.py`)

```
处理每个类型 source_type:
│
├── fixed/custom/java_base 精确命中？ → 直接返回
│
├── type_expression 可确定性解析？ → 直接返回
│
├── Progressive KB 缓存命中？ → 直接返回
│
├── 含 < ？ → Generics Rule Lib 匹配
│   rules = lib.match_rules_for_type(source_type, top_k=2)
│   if rules:
│       generics_context = lib.format_rule_prompt(rules, max_rules=2)
│       log_detail("GENERICS RULE {source_type}", ...)
│
├── 构建 prompt：
│   context_parts = []
│   context_parts.append(generics_context)   ← 新增
│   context_parts.append(kb_context)
│   context_parts.append(rag_context)
│   prompt = "\n\n".join(context_parts) + "\n\n" + prompt
│
└── LLM 翻译 → 结果写入当前 schema + Progressive KB
```

### 3. 片段翻译阶段 (`prompt_generator.py`)

```
PromptGenerator.__init__:
│
├── 加载片段详情
├── RAG 上下文注入
├── Progressive KB 上下文注入
│
├── 片段代码含 '<' ？ → Generics Rule Lib 匹配
│   rules = lib.match_rules(source_fragment_body, top_k=3)
│   self.generics_context = lib.format_rule_prompt(rules, max_rules=3)
│
└── build_base_prompt():
    │
    ├── persona
    ├── instruction
    ├── Java source code
    ├── partial Cangjie translation
    ├── Generics Rule Context              ← 新增（在 KB 之前）
    ├── Progressive KB few-shot
    ├── RAG documentation
    ├── ICL examples
    ├── error feedback (if applicable)
    └── target translation
```

---

## 参考资源

- **仓颉官方文档**：
  - [泛型概述](https://docs.cangjie-lang.cn/docs/0.53.18/user_manual/source_zh_cn/generic/generic_overview.html)
  - [泛型约束](https://docs.cangjie-lang.cn/docs/0.53.18/user_manual/source_zh_cn/generic/generic_constraint.html)
  - [泛型函数](https://docs.cangjie-lang.cn/docs/0.53.18/user_manual/source_zh_cn/generic/generic_function.html)
  - [泛型类型子类型关系](https://docs.cangjie-lang.cn/docs/0.53.13/Spec/source_zh_cn/Chapter_09_Generics(zh).html)
- **ArkAdapter 论文**：ACM ISSTA 2025 — Adaptation Knowledge Repository 技术来源
