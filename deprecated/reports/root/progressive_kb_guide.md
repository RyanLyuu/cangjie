# 渐进知识库 (Progressive Knowledge Base) 集成文档

## 概述

本文档说明 x2cangjie 项目中新增的渐进知识库 (Progressive KB) 模块，基于 ArkAdapter 论文 (ACM ISSTA 2025) 中的 **Adaptation Knowledge Repository** 技术。

**核心思想**：不依赖静态文档 RAG 检索，而是在翻译过程中渐进累积 "Java → 仓颉" 的真实翻译对照例子 (Translation Pair)，按场景分类，在后续翻译中作为 few-shot 示例注入 prompt。让 LLM 从"看文档"变成"看例子"。

**与现有 RAG 的关系**：渐进知识库不是替代 RAG，而是在 RAG 之前的上层补充。查找优先级：

```
Primitive/Java Base/Generic Map → Custom Types → Interface Shim → Progressive KB 缓存 → Progressive KB Few-Shot → RAG 文档检索 → LLM 推理
```

---

## 论文参考

**论文**：Porting Software Libraries to OpenHarmony: Transitioning from TypeScript or JavaScript to ArkTS (ACM ISSTA 2025)

**ArkAdapter 的两大核心机制**：

1. **Adaptation Knowledge Repository** — 场景化的真实迁移例子库，按场景 (scenario) 分类存储，检索时作为 few-shot 注入 prompt
2. **Adaptation Priority Strategy** — 基于依赖结构和语法差异粒度的翻译优先级策略，解决项目级多差异互相干扰的问题

**为什么适用于 x2cangjie**：

| 论文挑战 | x2cangjie 对应 | 适用性 |
|----------|---------------|--------|
| LLM 对 ArkTS 不熟悉 | LLM 对 Cangjie 不熟悉 | ✅ 同构问题 |
| 项目级代码适配有大量语法差异 | Java→Cangjie 存在大量类型/语法差异 | ✅ 同构问题 |
| 需要场景化的 few-shot 示例 | 类型映射和片段翻译都是高度重复的模式 | ✅ 翻译对可复用 |
| 编译验证闭环 | x2cangjie 已有 `cjpm build` 验证循环 | ✅ 天然数据来源 |

---

## 修改清单

### 新增文件

| 文件 | 说明 |
|------|------|
| `src/java/progressive_kb/__init__.py` | 模块入口，导出 `get_progressive_kb`, `ProgressiveKB`, `TranslationPair`, `TypeMapping`, `ScenarioClassifier` |
| `src/java/progressive_kb/progressive_kb.py` | 渐进知识库核心实现：增删改查、few-shot 格式化、场景自动分类 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `src/java/type_resolution/translate_type_rag.py` | 1) 导入 `get_progressive_kb`<br>2) 新增 `--use_progressive_kb` CLI 参数<br>3) main() 中初始化 KB 实例<br>4) 类型翻译前：先查 KB 缓存 (命中则跳过 LLM)，再检索 few-shot 示例注入 prompt<br>5) 翻译验证通过后：存储类型映射到 KB |
| `src/java/translation/prompt_generator.py` | 1) 导入 `get_progressive_kb`<br>2) 新增 `self.kb_context` 字段<br>3) `__init__` 中检索翻译对照例子<br>4) `build_base_prompt` 中注入 KB few-shot (在 RAG 文档之前) |
| `src/java/translation/compositional_translation_validation.py` | 1) 导入 `get_progressive_kb`<br>2) 新增 `_store_translation_pair_to_kb()` 辅助函数<br>3) 在3处翻译成功路径 (非 normal method / not-independent / no-tests-success) 中调用存储函数<br>4) 新增 `--use_progressive_kb` CLI 参数 |
| `scripts/java/translate_types.sh` | 新增第8个参数 `use_progressive_kb` (默认: true) |
| `scripts/java/translate_fragment.sh` | 新增第8个参数 `use_progressive_kb` (默认: true) |

---

## 数据结构

### TranslationPair (翻译对照例子)

```python
@dataclass
class TranslationPair:
    pair_id: str          # 内容 hash, 自动去重
    java_code: str        # Java 源代码片段
    cangjie_code: str     # 对应的仓颉代码片段
    signature: str        # 方法/类的完整签名 (如 "User.getName")
    scenario: str          # 场景标签 (自动分类或手动指定)
    java_types: list      # 涉及的 Java 类型列表
    cangjie_types: list   # 对应的仓颉类型列表
    compile_pass: bool     # 是否经过编译验证
    source_project: str   # 来源项目名
```



### TypeMapping (类型映射缓存)

```python
@dataclass
class TypeMapping:
    java_type: str        # Java 类型 (如 "Optional<T>")
    cangjie_type: str     # 对应仓颉类型 (如 "Option<T>")
    imports: list         # 需要的 import 语句
    source: str           # 来源: "fixed_map" | "custom_type" | "llm" | "kb"
    verified: bool        # 是否经过编译验证
```

821

![image-20260602115513700](C:\Users\Lenovo\AppData\Roaming\Typora\typora-user-images\image-20260602115513700.png)

![image-20260602115835187](C:\Users\Lenovo\AppData\Roaming\Typora\typora-user-images\image-20260602115835187.png)

![image-20260602115529069](C:\Users\Lenovo\AppData\Roaming\Typora\typora-user-images\image-20260602115529069.png)

### ScenarioClassifier (场景自动分类)

自动将 Java 代码分类到翻译场景：

| 场景 | 触发模式 | 说明 |
|------|----------|------|
| `enum` | `enum Xxx` | 枚举翻译 |
| `stream_api` | `.stream()`, `.collect()`, `.map()` 等 | Stream API 翻译 |
| `lambda` | `->`, `::new`, 方法引用 | Lambda/函数式翻译 |
| `concurrency` | `synchronized`, `ConcurrentHashMap` 等 | 并发翻译 |
| `generics` | `<T>`, `Optional<`, `List<` 等 | 泛型翻译 |
| `exception` | `throws`, `try`, `catch` 等 | 异常翻译 |
| `getter_setter` | `getXxx()`, `setXxx()` 属性翻译 | Getter/Setter 翻译 |
| `annotation` | `@Override`, `@Deprecated` 等 | 注解翻译 |
| `method_body` | 方法定义体 | 通用方法体翻译 |
| `general` | 以上都不匹配 | 默认分类 |

![image-20260602121704192](C:\Users\Lenovo\AppData\Roaming\Typora\typora-user-images\image-20260602121704192.png)

---

## 存储布局

```
data/java/progressive_kb/
    type_mappings.json      # 类型映射缓存 (增量累积)
    translation_pool.json   # 翻译对照例子库 (增量累积)
    scenarios.json          # 场景分类索引 (自动重建)
```

数据在每次 `add_example()` 或 `add_type_mapping()` 调用时自动持久化到磁盘。首次运行时自动创建目录。

---

## 运行流程

### 1. 类型翻译阶段 (`translate_types.sh`)

<img src="C:\Users\Lenovo\AppData\Roaming\Typora\typora-user-images\image-20260601191955836.png" alt="image-20260601191955836" style="zoom:50%;" />

```
                                         ┌──────────────────────┐
                                         │ Fixed Type Map       │
                                         │ (fixed_type_map.json)│
                                         └──────────┬───────────┘
                                                    │ 未命中
                                         ┌──────────▼───────────┐
                                         │ Custom Types         │
                                         │ (from schema)        │
                                         └──────────┬───────────┘
                                                    │ 未命中
                               ┌─────────────────────▼─────────────────────┐
                               │ Java Base Type Map                        │
                               │ (java_base_type_map.json)                 │
                               └─────────────────────┬─────────────────────┘
                                                    │ 未命中
                         ┌───────────────────────────▼──────────────────────────┐
                         │ Progressive KB: Type Mapping Cache                   │
                         │ (progressive_kb/type_mappings.json)                  │
                         │ 命中 verified √ → 直接返回, 跳过 LLM                    │
                         └───────────────────────────┬──────────────────────────┘
                                                    │ 未命中
                         ┌───────────────────────────▼──────────────────────────┐
                         │ Prompt 组装:                                         │
                         │ 1. Progressive KB few-shot (翻译对照例子)              │
                         │ 2. Progressive KB type context (相关类型映射)          │
                         │ 3. RAG 文档 (仓颉官方文档)                              │
                         │ 4. 类型翻译 prompt 模板                                │
                         └───────────────────────────┬──────────────────────────┘
                                                    │
                                         ┌──────────▼───────────┐
                                         │ LLM 推理翻译          │
                                         └──────────┬───────────┘
                                                    │
                                         ┌──────────▼───────────┐
                                         │ CJC 编译验证          │
                                         └──────────┬───────────┘
                                                    │ 通过
                         ┌───────────────────────────▼─────────────────────────-─┐
                         │ 存储到 Progressive KB:                                 │
                         │ - add_type_mapping(java_type, cangjie_type, verified) │
                         │ - verified 映射仅写入 Progressive KB                    │
                         └───────────────────────────────────────────────────────┘
```

### 2. 片段翻译阶段 (`translate_fragment.sh`)

```
                         ┌───────────────────────────────────────────────────┐
                         │ PromptGenerator.__init__()                        │
                         │                                                   │
                         │ 1. 加载 fragment 详情                               │
                         │ 2. 加载 adaptive ICL 示例                           │
                         │ 3. [新增] KB.retrieve(java_code, top_k=3)          │
                         │    → format_few_shot_prompt() → self.kb_context   │
                         │ 4. [原有] RAG retrieve → self.rag_context          │
                         └───────────────────────┬───────────────────────────┘
                                                 │
                         ┌───────────────────────▼──────────────────────────┐
                         │ build_base_prompt()                              │
                         │                                                  │
                         │ Prompt 顺序:                                      │
                         │ 1. Persona                                       │
                         │ 2. Instruction                                   │
                         │ 3. Java source code                              │
                         │ 4. Partial Cangjie translation                   │
                         │ 5. [新增] KB few-shot (真实翻译对照例子)             │
                         │ 6. RAG documentation (仓颉官方文档)                │
                         │ 7. ICL examples                                  │
                         │ 8. Error feedback (if any)                       │
                         └───────────────────────┬──────────────────────────┘
                                                 │
                         ┌───────────────────────▼──────────────────────────┐
                         │ LLM 翻译 → 仓颉编译验证                             │
                         └───────────────────────┬──────────────────────────┘
                                                 │ 通过
                         ┌───────────────────────▼──────────────────────────┐
                         │ [新增] _store_translation_pair_to_kb()            │
                         │                                                  │
                         │ kb.add_example(                                  │
                         │   java_code=fragment.source_body,                │
                         │   cangjie_code=generation,                       │
                         │   signature="ClassName.methodName",              │
                         │   scenario="auto",                               │
                         │   compile_pass=True,                             │
                         │   source_project=args.project,                   │
                         │ )                                                │
                         └──────────────────────────────────────────────────┘
```

### 3. 渐进学习效果

```
第 1 次运行: KB 为空 → 全部回退到 RAG/LLM → 翻译较慢, 准确率一般
     ↓ (翻译过程中自动累积验证通过的翻译对)

第 2 次运行: KB 有部分例子 → 常见模式 (getter/setter, 基础泛型) 可命中 few-shot
     ↓

第 N 次运行: KB 覆盖常见场景 → 大多数翻译有参考例子 → 准确率显著提升
     ↓

跨项目复用: 同一个 KB 可用于不同 Java 项目
     (HashMap → HashMap 的映射在任何项目中都一样)
```

---

## 使用方式

### 启用渐进知识库

类型翻译:
```bash
bash scripts/java/translate_types.sh <project> <model> <temp> <suffix> true true false true
#                                                              use_llm  use_rag translate_tests  use_progressive_kb
```

片段翻译:
```bash
bash scripts/java/translate_fragment.sh <project> <model> <suffix> <temp> true false false true
#                                                                    use_rag skip_mock translate_tests  use_progressive_kb
```

默认值：`use_progressive_kb` 默认为 `true`。

### 禁用渐进知识库

如果不想使用渐进知识库（例如调试或对比实验）：
```bash
bash scripts/java/translate_types.sh <project> <model> <temp> <suffix> true true false false
#                                                              最后一个参数设为 false
```



---

## 知识库详细作用

### 1. 类型映射缓存 (Type Mapping Cache)

**作用**：缓存已验证的 Java→Cangjie 类型映射，避免对同一类型发起重复 LLM 调用。

**与 java_base_type_map 的区别**：

| 特性 | java_base_type_map | Progressive KB Type Mapping |
|------|-------------------|----------------------------|
| 存储内容 | Java 基础类型的规范映射和分类元数据 | `TypeMapping` 对象，包含 imports, source, verified |
| 信息丰富度 | mapping、category、reasoning | 包含 import 语句、来源标记、验证状态 |
| 检索能力 | 精确匹配 | 精确匹配 (类型缓存的场景不需要模糊搜索) |
| 更新方式 | 版本控制下人工维护 | 运行时累积，`verified=True/False` 区分 |

**查找优先级**：
```
Primitive/Java Base/Generic Map → Custom Types → Interface Shim → Progressive KB Type Cache → Any fallback
```

### 2. Few-Shot 翻译对照库 (Translation Pool)

**作用**：为 LLM 提供场景化的真实翻译例子，让 LLM "看例子模仿" 而非 "看文档猜"。

**检索算法**：

```
输入: java_code, java_types, scenario (可选)

1. 遍历 translation_pool 中的所有 TranslationPair
2. 计算综合相似度分数:
   - Jaccard 代码 token 相似度 (0-1)
   - 类型集合重叠度 (+0.15 × Jaccard)
   - 编译验证加分 (+0.05 if compile_pass=True)
3. 如果候选不足 top_k 且指定了 scenario → 从同场景补充
4. 如果仍不足 top_k → 从匹配自动检测场景的例子补充
5. 返回 top_k 个最相似的 TranslationPair
```

**Prompt 注入位置**（在 `build_base_prompt` 中）：
```
Persona
Instruction
Java Source Code
Partial Cangjie Translation
[★ KB Few-Shot Examples]  ← 新增，真实翻译对照
[★ KB Type Context]        ← 新增，相关类型映射
RAG Documentation           ← 原有，仓颉官方文档
ICL Examples               ← 原有
Error Feedback              ← 反馈时
```

**为什么 KB Few-Shot 放在 RAG 文档之前**：
- KB 例子是**真实的、已验证的**翻译对照，信息密度高
- RAG 文档是**描述性的**官方文档，需要 LLM 推导才能映射
- 论文实验证明：真实例子 > 文档描述 > 零样本

### 3. 场景自动分类 (Scenario Classification)

**作用**：自动识别 Java 代码片段的翻译场景，使检索更精准。

**场景层次**：
```
特定场景优先:
  enum > stream_api > lambda > concurrency > generics > exception > getter_setter > annotation
默认场景:
  general (无法匹配任何模式时)
```

**自动分类**：使用 `scenario="auto"` 参数时，`ScenarioClassifier.classify()` 自动检测场景标签。无需手动标注。

### 4. 跨项目复用

**关键特性**：类型映射不因项目而变。`HashMap<K,V>` 在 commons-cli 和 commons-pool 中都映射到 `HashMap<K,V>`。

**数据持久化**：
- `type_mappings.json` — 类型缓存跨项目复用
- `translation_pool.json` — 翻译对照例子跨项目复用
- `scenarios.json` — 场景索引自动重建

---

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--use_progressive_kb` | `true` | 是否启用渐进知识库 |
| `data/java/progressive_kb/` | (自动创建) | 存储目录路径 |
| `top_k` (类型翻译) | 2 | 检索类型翻译的 few-shot 示例数 |
| `top_k` (片段翻译) | 3 | 检索片段翻译的 few-shot 示例数 |
| `max_examples` | 3 | 最多注入的 few-shot 示例数 |

---

## 注意事项

1. **首次运行为空 KB**：第一次运行时知识库为空，不会有 few-shot 注入。所有翻译回退到 RAG/LLM。随着翻译推进，KB 自动累积。

2. **存储开销极小**：每个 TranslationPair 约 200-500 bytes，每个 TypeMapping 约 50-100 bytes。即使翻译 1000+ 类型，总存储不超过 1MB。

3. **自动去重**：`add_example()` 使用内容 hash 自动去重。相同的 Java→Cangjie 翻译对只会保留一个版本，但 verified=True 会覆盖 verified=False。

4. **线程安全**：当前实现使用模块级单例。如果需要并发访问，需要加锁。

5. **与 java_base_type_map 的关系**：`java_base_type_map.json` 是所有阶段共享的规范基础映射；Progressive KB 仅保存运行时验证结果，不反向修改基础映射文件。

6. **不影响原有功能**：`use_progressive_kb=false` 时，所有 KB 相关代码完全跳过，行为与改动前一致。

---

## Bug 修复记录

### Bug 1: `result.imports` 类型不匹配 — list vs string

**症状**：类型翻译命中 Progressive KB 缓存时，`result.imports` 被赋值为 `list`（来自 `TypeMapping.imports`），但下游代码（`create_skeleton.py` 等）期望 `str`，导致 `imports.split('\n')` 在 list 上报 `AttributeError`。

**根因**：`TypeMapping.imports` 在 KB 中存储为 `list[str]`，但 `translate_type_rag.py` 的 `Result.imports` 是 `str`。

**修复**：`translate_type_rag.py` line 491，KB 缓存命中时将 `kb_mapping.imports` 用 `'\n'.join()` 转回字符串：

```python
result.imports = '\n'.join(kb_mapping.imports) if kb_mapping.imports else None
```

---

### Bug 2: `create_skeleton.py` 对 imports 格式不兼容

**症状**：`create_skeleton.py` 中 `imports_val.split('\n')` 在 `imports_val` 为 `list` 时报 `AttributeError`。

**根因**：上游修改后 `imports` 可能为 `list`（KB 返回）或 `str`（LLM 返回），`create_skeleton.py` 只处理了 `str`。

**修复**：`create_skeleton.py` lines 1039-1042，增加 `isinstance` 检查：

```python
if isinstance(imports_val, list):
    imports_str = '\n'.join(imports_val)
else:
    imports_str = imports_val
```

---

### Bug 3: `response_format=json_object` 导致非 OpenAI 模型返回空响应

**症状**：使用 deepseek-chat（经 OpenRouter）或 glm-5.1（经 yunwu.ai）进行类型翻译时，LLM 返回空字符串 `""`。

**根因**：`model.prompt_model()` 传入 `response_format={"type": "json_object"}`, 但 OpenRouter 和 yunwu.ai 等非 OpenAI 代理不一定支持此参数，导致模型返回空响应。

**修复**：`compositional_translation_validation.py` 中添加模型白名单，仅对 gpt-4o 系列传递 `response_format`：

```python
models_supporting_json_mode = {"gpt-4o-2024-11-20", "gpt-4o", "gpt-4"}
```

非白名单模型不再传 `response_format`，改为在 prompt 中用自然语言要求 JSON 格式。

---

### Bug 4: `prompt_generator.py` KeyError — `cangjie_class_declaration`

**症状**：片段翻译启动时 `KeyError: 'cangjie_class_declaration'`。

**根因**：`build_base_prompt()` 通过 `self.class_dict["cangjie_class_declaration"]` 访问字典，但部分 schema 中不存在此键（如接口类型、枚举类型等）。

**修复**：改为 `.get()` 加空字符串默认值：

```python
cangjie_class_declaration=self.class_dict.get('cangjie_class_declaration', ''),
```

---

### Bug 5: `_store_translation_pair_to_kb` 读取不存在的 `body` 键

**症状**：片段翻译成功后存储到 KB 时，`fragment.get("body", [])` 返回空列表，`java_code` 字段为空。

**根因**：`compositional_translation_validation.py` 中的 fragment 变量是进度跟踪用的简略 dict（仅含 `class_name`, `fragment_name` 等），不含 `body`。实际源码需要从 schema JSON 文件读取。

**修复**：重写 `_store_translation_pair_to_kb()`，从 `schema_file` 对应的 JSON 中读取：
- Java 源码：`schema["classes"][class_key]["methods"/"fields"][frag_name]["body"]`
- `java_types` / `cangjie_types`：从 `frag_dict["types"]`, `frag_dict["return_types"]`, `frag_dict["body_types"]` 和 `frag_dict["type_translations"]` 中提取

---

### Bug 6: `translation_pool.json` 中 `java_types` / `cangjie_types` 为空

**症状**：KB 的 `translation_pool.json` 中所有条目的 `java_types` 和 `cangjie_types` 字段为空列表 `[]`。

**根因**：同 Bug 5，`_store_translation_pair_to_kb()` 原来从 fragment dict（不含类型信息）取值。

**修复**：从 schema JSON 的 `frag_dict["types"]` 和 `frag_dict["type_translations"]` 中提取类型列表。具体逻辑：

```python
java_types = list(set(
    frag_dict.get("types", []) +
    frag_dict.get("return_types", []) +
    frag_dict.get("body_types", [])
))
cangjie_types = [
    v["translated_target_type"]
    for v in frag_dict.get("type_translations", {}).values()
    if v.get("translated") and v.get("translated_target_type")
]
```

---

### Bug 7: `model_configs.yaml` 中 glm-5.1 配置缩进错误

**症状**：yaml 解析 glm-5.1 配置时子字段未正确嵌套，导致模型参数丢失。

**根因**：手动添加 yaml 时 `api_key`、`base_url` 等字段缩进层级不对。

**修复**：修正 `model_configs.yaml` 中 glm-5.1 条目的缩进，确保 `model`、`api_key`、`base_url` 均为顶层 key 下的正确子字段。

---

### Bug 8: `prompt_generator.py` 缺少 glm-5.1 的 persona 映射

**症状**：使用 glm-5.1 模型时，`meta_data` 字典中无对应 persona，导致 prompt 中 persona 段为空。

**修复**：在 `prompt_generator.py` 的 `meta_data` 字典中添加：

```python
"glm-5.1-persona": "",
```

与 `deepseek-chat-persona` 同级，空字符串表示不注入额外 persona。

---

### Bug 9: `type_mappings.json` 中 imports 为空列表 ✅ 已修复

**症状**：KB `type_mappings.json` 中许多条目的 `imports` 为 `[]`，导致生成的仓颉代码缺少 import 语句。

**根因链**：
1. LLM 翻译类型时经常省略 `CANGJIE IMPORTS:` 块
2. `Parser.extract_imports()` 用正则匹配 `CANGJIE IMPORTS:` 块，匹配不到时返回 `None`
3. `is_type_loadable(imports or '', translation)` 中 `imports=None` → 传入空字符串 → 对于内置类型（`Int64`, `String`, `Bool` 等）仍能通过编译验证
4. 第 656 行 `imports.split('\n') if imports else []` 将 `None` 转为 `[]` 写入 KB
5. KB 缓存命中时返回 `imports=[]` → 生成的仓颉代码无 import 语句

**修复方案**（已实现）：

1. **强化 prompt**（`configs/prompt_templates.yaml`）：在 `type_resolution_description_response_format` 模板中增加 `IMPORTANT: The CANGJIE IMPORTS section is MANDATORY` 提示，并将占位符从 `<cangjie_imports_if_any>` 改为 `<cangjie_imports>`，强调即使是内置类型也必须包含该块（可以为空）

2. **Imports 推断兜底**（`translate_type_rag.py`）：新增 `CANGJIE_BUILTIN_TYPES` 集合和 `_strip_generic_params()` 辅助函数。当 LLM 省略 IMPORTS 块时（`imports is None`）：
   - 如果翻译后类型是内置类型（如 `Int64`, `HashMap<K,V>` → 基础名 `HashMap` 在集合中），设 `imports = ''`，被视为"无需 import"，继续验证
   - 如果不是内置类型，添加 feedback 要求 LLM 重新提供 IMPORTS，扣减 budget 重试

3. **KB 存储逻辑修复**（`translate_type_rag.py`）：将 `imports.split('\n') if imports else []` 改为 `[line for line in imports.split('\n') if line.strip()] if imports else []`，过滤掉空行，避免 `""` → `[""]`
