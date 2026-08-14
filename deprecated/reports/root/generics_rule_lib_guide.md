# 泛型映射规则库 

## 概述

本文档说明 x2cangjie 项目中新增的泛型映射规则库 (Generics Rule Library)，为 Java 泛型结构到仓颉代码的翻译提供**系统化、可执行、可参考的映射规则**。

**核心思想**：Java 泛型与仓颉泛型存在大量语义差异（通配符 vs 类型参数、类型擦除 vs 具化、`extends` vs `where <:`、`? super` vs `~T` 投影等）。这些差异无法通过简单的字符串替换解决，需要结构化的规则映射。规则库覆盖 9 大类 45 条映射规则，并在类型翻译、骨架生成、prompt 注入三个环节自动介入。

**与现有管线的关系**：泛型规则库不是独立模块，而是嵌入在已有管线的三个关键环节，作为现有映射机制的**补充和增强层**：

```
Primitive/Java Base/Generic Map → Custom Types
→ Container Smart Map (type_container_map.json)  ← 集成点1: create_skeleton.py
→ Generics Rule Lib (C01-C45)                   ← 集成点2: translate_type_rag.py
→ Progressive KB 缓存
→ Progressive KB Few-Shot
→ Generics Context (规则 few-shot)              ← 集成点3: prompt_generator.py
→ RAG 文档检索
→ LLM 推理
```

---

## 设计参考

**仓颉泛型官方规范**：
- 仓颉使用 `where T <: UpperBound` 声明泛型约束（对应 Java 的 `extends`）
- 仓颉泛型无类型擦除，类型参数在运行时保留
- 仓颉不支持通配符，使用泛型方法参数提升或类型投影 `~T` 替代
- 仓颉用户自定义泛型类型默认不变（invariant），支持 `out`/`in` 声明处型变
- 仓颉 Hash 容器要求键/元素类型满足 `Hashable & Equatable<T>`，`Any` 不满足此约束需替换为 `AnyHashable`
- 仓颉泛型异常不支持，静态成员不可引用类类型参数

---

## 修改清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `generics_rule_lib/schema.json` | 规则库元数据：版本号、规则结构定义、文件清单、查找优先级定义 |
| `generics_rule_lib/primitive_map.json` | Java 原始/包装类型 → 仓颉类型映射（44 条） |
| `generics_rule_lib/type_container_map.json` | 容器类型映射 + 约束推导规则 + API 变换表（30 条） |
| `generics_rule_lib/rules/01_declaration.json` | 泛型声明转换规则（C01-C06，6 条） |
| `generics_rule_lib/rules/02_constraint.json` | 约束转换规则（C07-C11，5 条） |
| `generics_rule_lib/rules/03_wildcard.json` | 通配符转换规则（C12-C17，6 条） |
| `generics_rule_lib/rules/04_variance.json` | 型变映射规则（C18-C21，4 条） |
| `generics_rule_lib/rules/05_raw_type.json` | 原始类型恢复规则（C22-C24，3 条） |
| `generics_rule_lib/rules/06_array_instantiation.json` | 数组与实例化规则（C25-C28，4 条） |
| `generics_rule_lib/rules/07_advanced.json` | 递归边界与高级模式（C29-C32，4 条） |
| `generics_rule_lib/rules/08_semantic_gap.json` | 语义差异规则（C33-C40，8 条） |
| `generics_rule_lib/rules/09_container_smart.json` | 智能容器转换规则（C41-C45，5 条） |
| `generics_rule_lib/generics_rule_guide.md` | 规则库设计文档（本文档的配套详情文档） |
| `src/java/generics_rule_lib/__init__.py` | 规则加载引擎：单例加载、容器映射、规则匹配、prompt 生成 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/java/translation/create_skeleton.py` | 1) 导入 `get_generics_rule_lib`<br>2) 新增 `_get_rule_lib()` 懒加载函数（线程安全单例，加载失败时 fallback 到硬编码）<br>3) `get_cangjie_type()` 开头新增规则库容器映射优先路径：`type_map` 精确匹配 → `rule_lib.translate_container_type()` → 原有泛型分解逻辑<br>4) 原有 `_HASH_KEY_CONTAINERS` / `_HASH_ELEMENT_CONTAINERS` 硬编码逻辑改为：优先查规则库 `is_hash_key_container()` / `is_hash_element_container()`，fallback 到原硬编码集合 |
| `src/java/type_resolution/translate_type_rag.py` | 1) 导入 `get_generics_rule_lib`<br>2) `main()` 中 `Progressive KB` 初始化后新增 `Generics Rule Lib` 初始化（无条件加载，轻量级）<br>3) 类型翻译循环中，KB 缓存查询后、LLM 调用前：对含 `<` 的类型匹配泛型规则，将匹配规则的 few-shot 示例注入 prompt 上下文 |
| `src/java/translation/prompt_generator.py` | 1) 导入 `get_generics_rule_lib`<br>2) `PromptGenerator.__init__` 新增 `self.generics_context: str = ""`<br>3) `__init__` 中：当片段代码含 `<` 时，自动匹配泛型规则并格式化为 few-shot<br>4) `build_base_prompt` 中：在 KB few-shot 之前、RAG 文档之前注入 `self.generics_context` |

---

## 数据结构

### 规则条目 (Rule Entry)

```json
{
  "id": "C13",
  "category": "wildcard",
  "subcategory": "upper_bounded_wildcard",
  "name": "上界通配符 <? extends>",
  "java_ast_pattern": {
    "node_type": "WildcardType",
    "bound_type": "extends"
  },
  "java_regex_fallback": "(\\w+)<\\s*\\?\\s+extends\\s+(\\w+)\\s*>",
  "cangjie_template": "将方法提升为泛型方法，<? extends $2> → <T> where T <: $2",
  "transforms": [
    { "from": "? extends UpperBound", "to": "类型参数 T + where T <: UpperBound", "scope": "parameter" }
  ],
  "constraints": {
    "cangjie_semantics": "仓颉无通配符，上界通配符映射为泛型参数 + 约束",
    "requires": ["C07"],
    "conflicts": [],
    "action": "提升为泛型方法并添加上界约束"
  },
  "priority": 8,
  "example": {
    "java": "double sum(List<? extends Number> list)",
    "cangjie": "func sum<T>(list: List<T>): Float64 where T <: Number",
    "note": "引入 T 并约束 T <: Number"
  },
  "validation_probes": ["cjpm build 是否通过"]
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 规则唯一标识，格式 `C{NN}` |
| `category` | string | 大类：declaration / constraint / wildcard / variance / raw_type / array_instantiation / advanced / semantic_gap / container_smart |
| `subcategory` | string | 子类，如 generic_class, upper_bound, unbounded_wildcard |
| `name` | string | 规则中文名称 |
| `java_ast_pattern` | object | tree-sitter AST 节点匹配模式（为 AST 引擎预留） |
| `java_regex_fallback` | string | 正则后备匹配（当前主要匹配方式） |
| `cangjie_template` | string | 仓颉输出模板，`$1`, `$2` 为捕获组引用 |
| `transforms` | array | 结构化转换列表，每步指明 from→to 和作用域 |
| `constraints` | object | 仓颉语义说明、前置规则 requires、冲突规则 conflicts、需执行动作 action |
| `priority` | number | 匹配优先级，数字越大越优先 |
| `example` | object | Java 示例、仓颉示例、说明 |
| `validation_probes` | array | 编译验证检查项 |

### 容器类型映射 (Container Type Mapping)

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

**关键字段**：

| 字段 | 说明 |
|------|------|
| `cangjie` | 仓颉容器名 |
| `type_args` | 泛型参数个数（0 表示需重构为非泛型形式） |
| `key_constraints` | 自动推导的约束列表 |
| `any_key_replacement` | 键位置 `Any` → `AnyHashable` |
| `any_element_replacement` | 元素位置 `Any` → `AnyHashable` |
| `api_transforms` | API 方法级映射（如 Optional → Option） |

### 约束推导配置 (Constraint Inference)

```json
{
  "constraint_inference_rules": {
    "hash_key_containers": ["HashMap", "LinkedHashMap", "ConcurrentHashMap"],
    "hash_element_containers": ["HashSet", "LinkedHashSet"],
    "comparable_element_containers": ["TreeSet", "TreeMap"],
    "replacement": {
      "Any_in_key_position": "AnyHashable",
      "Any_in_hash_element_position": "AnyHashable"
    }
  }
}
```

当翻译引擎遇到 `HashMap<Any, V>` 或 `HashSet<Any>` 时，自动将键/元素位的 `Any` 替换为 `AnyHashable`。

---

## 存储布局

```
generics_rule_lib/
├── schema.json                  # 规则库元数据与版本控制
├── primitive_map.json           # Java 原始类型 → 仓颉类型映射（44 条）
├── type_container_map.json      # 容器类型映射 + 约束推导 + API 变换表（30 条）
├── generics_rule_guide.md       # 规则库设计文档
└── rules/
    ├── 01_declaration.json      # 泛型声明转换（C01-C06，6 条）
    ├── 02_constraint.json       # 约束转换（C07-C11，5 条）
    ├── 03_wildcard.json         # 通配符转换（C12-C17，6 条）
    ├── 04_variance.json         # 型变映射（C18-C21，4 条）
    ├── 05_raw_type.json         # 原始类型恢复（C22-C24，3 条）
    ├── 06_array_instantiation.json  # 数组与实例化（C25-C28，4 条）
    ├── 07_advanced.json          # 递归边界与高级模式（C29-C32，4 条）
    ├── 08_semantic_gap.json     # 语义差异（C33-C40，8 条）
    └── 09_container_smart.json  # 智能容器转换（C41-C45，5 条）
```

所有 JSON 文件使用 UTF-8 编码，规则按文件分类存储，加载时合并并按 priority 降序、id 升序排列。

---

## API 参考

### `get_generics_rule_lib()`

```python
from src.java.generics_rule_lib import get_generics_rule_lib

lib = get_generics_rule_lib()  # 单例，线程安全，懒加载
```

返回 `GenericsRuleLib` 单例实例。首次调用时从 `generics_rule_lib/` 目录加载所有 JSON 数据。

### `GenericsRuleLib` 核心方法

#### 容器映射接口（集成点 1: create_skeleton.py）

```python
# 查询容器类型映射
mapping = lib.get_container_cangjie("HashMap")
# → {"cangjie": "HashMap", "type_args": 2, "key_constraints": [...], "any_key_replacement": "AnyHashable"}

# 判断是否为 Hash 容器
lib.is_hash_key_container("HashMap")    # → True
lib.is_hash_element_container("HashSet")  # → True
lib.is_comparable_container("TreeSet")    # → True

# 获取 Any 的替换类型
lib.any_replacement_for("HashMap", "key")     # → "AnyHashable"
lib.any_replacement_for("HashSet", "element") # → "AnyHashable"

# 完整的容器类型翻译（递归分解嵌套泛型）
lib.translate_container_type("HashMap<String, Object>", type_map)
# → "HashMap<String, Any>"
lib.translate_container_type("HashMap<Object, String>", type_map)
# → "HashMap<AnyHashable, String>"

# 推导约束
lib.infer_constraints("HashMap")
# → ["K <: Hashable & Equatable<K>"]
```

#### 规则匹配接口（集成点 2: translate_type_rag.py）

```python
# 根据 Java 代码片段匹配泛型规则
rules = lib.match_rules("class Box<T extends Number>", top_k=5)
# → [C02, C03, C07, ...]

# 根据 Java 类型字符串匹配规则（快捷方式）
rules = lib.match_rules_for_type("List<? extends Number>", top_k=3)
# → [C13, C18, ...]

# 按类别筛选
rules = lib.match_rules("void print(List<?> list)", category="wildcard", top_k=5)
# → [C12, ...]
```

#### Prompt 注入接口（集成点 3: prompt_generator.py）

```python
# 格式化匹配到的规则为 few-shot prompt
prompt_text = lib.format_rule_prompt(rules, max_rules=3)
# → 规则 ID + 名称 + Java/仓颉示例 + 语义说明 + 动作

# 一步式：匹配 + 格式化
prompt_text = lib.build_generics_context("void print(List<?> list)", max_rules=3)
# → 完整的泛型规则 few-shot section
```

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
├── PRIMITIVE/JAVA_BASE/GENERIC_MAP 命中？ → 直接返回
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
└── LLM 翻译 → 结果写入 schema type_translations + Progressive KB
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

## 规则优先级

匹配时按以下优先级排序（数字越大越优先，同优先级按 ID 升序）：

| Priority | 类别 | 说明 |
|----------|------|------|
| 10 | 泛型声明 | 类/接口/方法声明级转换，最精确 |
| 9 | 接口/方法约束 + 容器智能映射 | 精确的类型级匹配 |
| 8 | 通配符 + 型变 + 递归约束 | `?` 通配符提升、`~T` 投影 |
| 7 | 原始类型 + 嵌套通配符 + Stream | 中等精度模式匹配 |
| 6 | 数组/实例化 + 语义优势 | `T[]` → ArrayList、泛型重载 |
| 5 | 手动迁移 + 重构建议 | `new T()`、`Class<T>`、声明处型变 |
| 4 | 不支持的特性 | 泛型异常、Enum 泛型 |

---

## JSON 数据格式

### schema.json

```json
{
  "version": "2.0",
  "name": "Java Generics → Cangjie Mapping Rule Library",
  "description": "系统化的、可执行的 Java 泛型结构到仓颉代码的映射规则库",
  "rule_schema_version": "2.0",
  "rule_schema": { ... },   // 规则条目结构定义
  "files": { ... },         // 文件清单
  "integration_priority": [  // 查找优先级
    "Primitive/Java Base/Generic Map", "Custom Types",
    "Container Smart Map", "Generics Rule Lib",
    "Progressive KB 缓存", "Progressive KB Few-Shot",
    "RAG 文档检索", "LLM 推理"
  ]
}
```

### primitive_map.json

```json
{
  "version": "2.0",
  "description": "Java 原始类型与包装类型到仓颉类型的映射",
  "mappings": {
    "int": "Int32",
    "long": "Int64",
    "boolean": "Bool",
    "String": "String",
    "Object": "Any",
    "Optional": "Option",
    "List": "ArrayList",
    "HashMap": "HashMap",
    ...
  }
}
```

### rule 文件 (01-09)

```json
{
  "category": "wildcard",
  "description": "通配符转换规则...",
  "rules": [
    {
      "id": "C12",
      "subcategory": "unbounded_wildcard",
      "name": "无界通配符 <? >",
      "java_ast_pattern": { ... },
      "java_regex_fallback": "(\\w+)<\\s*\\?\\s*>",
      "cangjie_template": "将整个方法提升为泛型方法，用类型参数 T 代替 ?",
      "transforms": [ ... ],
      "constraints": { ... },
      "priority": 8,
      "example": { "java": "...", "cangjie": "...", "note": "..." },
      "validation_probes": [ ... ]
    },
    ...
  ]
}
```

---

## 使用示例

### 示例 1：骨架生成中的 HashMap 翻译

```
输入:  get_cangjie_type("HashMap<Object, String>", type_map)
                ↓ type_map 无 HashMap<Object, String> 的精确映射
                ↓ 规则库 translate_container_type 被调用
                ↓ HashMap → HashMap (cangjie: "HashMap")
                ↓ 查 constraint_config: HashMap 是 hash_key_container
                ↓ Object → Any → AnyHashable (key 位置替换)
输出:  "HashMap<AnyHashable, String>"
```

### 示例 2：类型翻译中注入泛型规则

```
输入类型:  "List<? extends Number>"
                ↓ PRIMITIVE/JAVA_BASE/GENERIC_MAP 无匹配
                ↓ KB 缓存无匹配
                ↓ 含 '<'，触发规则匹配
                ↓ match_rules_for_type → [C13: 上界通配符]
                ↓ format_rule_prompt → 生成 few-shot:
                   "Rule C13 (上界通配符 <? extends>):
                     Java:   double sum(List<? extends Number> list)
                     仓颉:  func sum<T>(list: List<T>): Float64 where T <: Number
                     Note:  引入 T 并约束 T <: Number"
                ↓ 注入 prompt → LLM 翻译
输出:  "ArrayList<Number>"  (或带约束的更精确翻译)
```

### 示例 3：片段翻译中注入上下文

```
输入片段:
  "public void processData(List<? extends Comparable> items) { ... }"
                ↓ 检测到 '<' → 触发规则匹配
                ↓ match_rules → [C13: 上界通配符, C12: 无界通配符(泛化)]
                ↓ 格式化为 few-shot 并注入 prompt
                ↓ LLM 翻译时参考规则模板
输出:
  "public func processData<T>(items: ArrayList<T>) where T <: Comparable { ... }"
```

---

## 扩展指南

### 添加新规则

1. 在 `generics_rule_lib/rules/` 对应的 `NN_category.json` 中追加规则条目
2. `id` 使用 `C{NN}` 格式，递增编号
3. 填写所有必填字段：`id`, `category`, `name`, `java_regex_fallback`, `cangjie_template`, `priority`, `example`
4. 可选填写：`java_ast_pattern`, `transforms`, `constraints`, `validation_probes`
5. 运行 `python -c "import json; json.load(open('generics_rule_lib/rules/NN_category.json'))"` 验证 JSON 格式

### 添加新容器映射

1. 在 `generics_rule_lib/type_container_map.json` 的 `mappings` 中添加新条目
2. 如果容器需要 Hash 约束，同时更新 `constraint_inference_rules` 中的对应列表
3. 如果容器需要 `Any → AnyHashable` 替换，添加 `any_key_replacement` 或 `any_element_replacement`

### 更新原始类型映射

1. 在 `generics_rule_lib/primitive_map.json` 的 `mappings` 中添加或修改条目

---

## 参考资源

- **仓颉官方文档**：
  - [泛型概述](https://docs.cangjie-lang.cn/docs/0.53.18/user_manual/source_zh_cn/generic/generic_overview.html)
  - [泛型约束](https://docs.cangjie-lang.cn/docs/0.53.18/user_manual/source_zh_cn/generic/generic_constraint.html)
  - [泛型函数](https://docs.cangjie-lang.cn/docs/0.53.18/user_manual/source_zh_cn/generic/generic_function.html)
  - [泛型类型子类型关系](https://docs.cangjie-lang.cn/docs/0.53.13/Spec/source_zh_cn/Chapter_09_Generics(zh).html)
- **项目内文档**：
  - `docs/progressive_kb_guide.md` — 渐进知识库集成文档
  - `generics_rule_lib/generics_rule_guide.md` — 规则库设计详情文档
- **ArkAdapter 论文**：ACM ISSTA 2025 — Adaptation Knowledge Repository 技术来源
