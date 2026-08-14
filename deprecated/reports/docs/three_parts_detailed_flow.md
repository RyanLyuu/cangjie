# 三部分详细流程

## 0. 全局视角：一个 fragment 的完整处理流程

三部分都挂在 `compositional_translation_validation.py` 的 `translate()` 主循环里。按依赖顺序遍历 `traversal.json` 中的每个 fragment，对每个 fragment 执行以下步骤：

```
for each fragment in traversal.json:

    ┌─ Part 1 (如果 use_pseudocode=true) ─┐
    │  Phase-1 LLM 调用: Java → 伪代码     │
    │  pseudocode = 提取的伪代码 or ""      │
    └──────────────────────────────────────┘
                    ↓
    ┌─ PromptGenerator 构造 ──────────────┐
    │  load_fragment() 组装 Java 源码      │
    │                                      │
    │  Part 2 (如果 use_grammar_prompt):   │
    │    grammar_context = 静态 EBNF 文本   │
    │                                      │
    │  Part 3 (如果 use_syntax_rag):       │
    │    检索 top-3 结构相似 Cangjie 片段    │
    │    syntax_graph_context = 检索结果    │
    │                                      │
    │  Part 1:                             │
    │    add_pseudocode_bridge(pseudocode)  │
    └──────────────────────────────────────┘
                    ↓
    ┌─ build_base_prompt() ───────────────┐
    │  persona                             │
    │  instruction                         │
    │  grammar (Part 2)                    │
    │  Java source                         │
    │  pseudocode bridge (Part 1)          │
    │  partial translation                 │
    │  generics context                    │
    │  Progressive KB few-shot             │
    │  RAG docs                            │
    │  syntax graph (Part 3)              │
    │  ICL                                 │
    │  error feedback (仅重试时)            │
    │  "### Response:"                     │
    └──────────────────────────────────────┘
                    ↓
    ┌─ Phase-2 LLM 调用 ──────────────────┐
    │  prompt_model() → JSON response      │
    │  extract_json_translation()          │
    └──────────────────────────────────────┘
                    ↓
    ┌─ 编译验证 ──────────────────────────┐
    │  cjpm build                          │
    │  失败 → feedback = 编译错误           │
    │         → 回到 build_base_prompt      │
    │         → 带 feedback 重试            │
    │  成功 → 记录 status                   │
    │         → 继续下一个 fragment          │
    └──────────────────────────────────────┘
```

三部分各自的"开销时刻"不同：Part 2 是零开销（静态文本缓存一次）；Part 3 是每 fragment 一次检索（毫秒级，纯内存计算）；Part 1 是每 fragment 多一次 LLM 调用（最贵，baseline 11.7s → pseudo 15.1s）。

---

## 1. Part 1：伪代码中间层 — 两阶段翻译

**触发条件**：`--use_pseudocode=true`

**参考论文**：A1 (Pseudocode-based Code Translation, arXiv:2510.00920)

### 1.1 核心思路

模拟人类自然语言翻译中的"语义翻译"策略。直接翻译时 LLM 试图模仿源码结构，生成语义不一致的代码。伪代码中间层让 LLM 先理解源码意图用语言无关的伪代码表达，再从伪代码生成目标代码。

### 1.2 Phase-1：伪代码生成（新增）

```
┌─────────────────────────────────────────────────────┐
│  1. translate() 循环取出一个 fragment                 │
│     ↓                                                │
│  2. 构造一个精简版 PromptGenerator                    │
│     _skip_prompt_build=True                          │
│     → 只跑 load_fragment()，组装 Java 源码            │
│     → 跳过 RAG/KB/generics/grammar/syntax-graph      │
│       这些昂贵上下文加载                               │
│     ↓                                                │
│  3. 用 PSEUDOCODE_SYSTEM_PROMPT + Java 源码           │
│     构造 Phase-1 prompt                               │
│     ↓                                                │
│  4. 调用 LLM (prompt_model)                          │
│     要求输出：                                        │
│     - 三反引号包裹的伪代码块                           │
│     - 仅通用关键字 (FOR/WHILE/IF/ELSE/RETURN)        │
│     - 每个 Java API 调用改写为动词短语                 │
│       (Collections.sort(xs) → sort xs in place)      │
│     - 每个逻辑块前 // 注释说明意图                     │
│     - 不提及 Cangjie/Python 等目标语言                 │
│     ↓                                                │
│  5. _extract_pseudocode() 从 LLM 响应中               │
│     提取三反引号块或裸块                               │
│     ↓                                                │
│  6. 如果失败(网络/空响应) → pseudocode = ""           │
│     如果成功 → pseudocode = 提取的伪代码文本           │
└─────────────────────────────────────────────────────┘
```

### 1.3 Phase-2：翻译（原有流程，prompt 增加了伪代码块）

```
┌─────────────────────────────────────────────────────┐
│  7. 构造正式版 PromptGenerator                        │
│     _skip_prompt_build=False                         │
│     → 完整加载所有上下文                               │
│     → 调 add_pseudocode_bridge(pseudocode)           │
│       把伪代码存入 self.pseudocode_context             │
│     ↓                                                │
│  8. build_base_prompt() 组装完整 prompt               │
│     在 Java 源码之后、partial translation 之前         │
│     注入伪代码块：                                     │
│                                                      │
│     ### Java Source                                  │
│     [Java fragment 源码]                              │
│                                                      │
│     ### Pseudocode Bridge (language-agnostic)        │
│     [伪代码 + // 注释]                                │
│                                                      │
│     ### Partial Cangjie Translation                  │
│     [已有骨架内容]                                    │
│     ↓                                                │
│  9. 调用 LLM → 返回 JSON {code, reasoning, imports}  │
│     ↓                                                │
│ 10. extract_json_translation() 解析                   │
│     ↓                                                │
│ 11. cjpm build 编译验证                               │
│     失败 → feedback 重试 (带编译错误)                  │
│     成功 → 继续下一个 fragment                         │
└─────────────────────────────────────────────────────┘
```

### 1.4 关键设计点

- **不丢弃 Java 源码**：Phase-2 的 prompt 同时包含 Java 源码和伪代码。伪代码居中解决歧义（"这段代码的意图是什么"），源码作为 fallback（伪代码有歧义时 LLM 可以回看源码）
- **失败退化**：Phase-1 任何环节失败都返回空串，Phase-2 在无伪代码的情况下继续，等于退回 baseline 行为
- **`_skip_prompt_build` 优化**：Phase-1 只需要 Java 源码来生成伪代码，不需要 RAG/KB/generics 这些昂贵上下文。这个开关避免"只想要源码却白跑了全套检索"

### 1.5 代码定位

| 步骤 | 文件 | 函数/变量 |
|---|---|---|
| Phase-1 LLM 调用 | `compositional_translation_validation.py` | `_generate_pseudocode()` |
| 伪代码提取 | `compositional_translation_validation.py` | `_extract_pseudocode()` |
| Phase-1 系统提示 | `compositional_translation_validation.py` | `PSEUDOCODE_SYSTEM_PROMPT` |
| 伪代码注入 | `prompt_generator.py` | `add_pseudocode_bridge()` / `self.pseudocode_context` |
| 模板配置 | `configs/prompt_templates.yaml` | `pseudocode_generation_system` / `pseudocode_bridge_context` |

---

## 2. Part 2：Cangjie 语法 EBNF 注入 — 静态规则前置

**触发条件**：`--use_grammar_prompt=true`

**参考论文**：B2 (Grammar Prompting, ACL 2023) / B1 (DocCGen, EMNLP 2024)

### 2.1 核心思路

Cangjie 对 LLM 来说是 DSL——训练数据极少，不知道 `where T <: Bound`、`AnyHashable`、`Bool`。B2 论文发现把目标语言的 BNF 语法规则作为 prompt 的一部分注入 LLM，仅 prompt 注入（不需要约束解码）就显著提升语法正确率。

### 2.2 初始化阶段（整个项目只执行一次）

```
┌─────────────────────────────────────────────────────┐
│  1. PromptGenerator.__init__() 检测到                │
│     use_grammar_prompt == 'true'                     │
│     ↓                                                │
│  2. 调用 get_grammar_prompt()                        │
│     ↓                                                │
│  3. grammar_prompt.py 的单例逻辑：                    │
│     a. 尝试从 configs/prompt_templates.yaml 加载      │
│        - cangjie_grammar_context (EBNF + G1-G8)      │
│        - cangjie_grammar_runtime_note (API 映射)     │
│     b. YAML 加载成功 → 拼接两部分文本                  │
│     c. YAML 加载失败 → 用代码内 inline fallback       │
│        (短版 EBNF + G1-G5)                           │
│     ↓                                                │
│  4. 结果缓存到模块级单例变量                           │
│     后续所有 fragment 共享同一块文本                   │
│     (grammar 是静态的，不需要每个 fragment 重新生成)   │
└─────────────────────────────────────────────────────┘
```

### 2.3 每个 fragment 的 prompt 组装

```
┌─────────────────────────────────────────────────────┐
│  5. build_base_prompt() 按固定顺序组装：              │
│                                                      │
│     ### Role                                         │
│     [persona 设定，含 AnyHashable 提示]               │
│                                                      │
│     ### Instruction                                  │
│     [翻译任务指令]                                    │
│                                                      │
│     ### Cangjie Grammar Reference  ← Part 2 注入位置  │
│     [EBNF 语法摘要]                                   │
│     [G1-G8 硬约束]                                    │
│     [运行时 API 映射表]                               │
│                                                      │
│     ### Java Source                                  │
│     [Java fragment 源码]                              │
│     ...                                              │
└─────────────────────────────────────────────────────┘
```

### 2.4 注入的完整内容

**EBNF 摘要**（告诉 LLM Cangjie 的语法骨架长什么样）：

```ebnf
var_decl      ::= "let" IDENT ":" TYPE "=" EXPR | "var" IDENT ":" TYPE "=" EXPR
func_decl     ::= "func" IDENT "(" [ PARAMS ] ")" [ ":" TYPE ] "{" STMTS "}"
class_decl    ::= ("class"|"abstract class"|"open class") IDENT [GENERICS] [":" SUPERTYPES] "{" MEMBERS "}"
GENERICS      ::= "<" TYPE_PARAM { "," TYPE_PARAM } ">"
TYPE_PARAM    ::= IDENT [ "where" IDENT "<:" TYPE ]
match_stmt    ::= "match" "(" EXPR ")" "{" { CASE "=>" BLOCK } "}"
```

**G1-G8 硬约束**（告诉 LLM 最容易犯的 8 个语法错误）：

| 约束 | 内容 | LLM 常犯的错 |
|---|---|---|
| G1 | 泛型约束 `where T <: Bound` | 写成 Java 的 `extends` |
| G2 | 型变用 `out T` / `in T` | 写成 Java 通配符 `? super T` |
| G3 | `Any` 不满足 `Hashable`，HashMap key 用 `AnyHashable` | `HashMap<Any, V>` 编译报错 |
| G4 | 整数字面量需类型后缀，默认 `Int32` | Java `int` 默认 32 位 |
| G5 | 布尔类型是 `Bool` | 写成 Java 的 `boolean` |
| G6 | 字符串插值 `"${expr}"` | 写成 Java `String.format` |
| G7 | void 函数返回类型 `Unit` | 写成 Java 的 `void` |
| G8 | 运算符重载用 `operator func` | 写成 Java 的 `equals()` |

**API 映射表**（告诉 LLM Java API 到 Cangjie 的对应关系）：

```
Object (HashMap key)  → AnyHashable
Runnable              → () -> Unit
Callable<V>           → () -> V
Consumer<T>           → (T) -> Unit
Supplier<T>           → () -> T
Predicate<T>          → (T) -> Bool
Comparator<T>         → (T, T) -> Int64
List<T>               → Array<T>
Map<K,V>              → HashMap<K,V>
Set<T>                → HashSet<T>
```

### 2.5 关键设计点

- **注入位置在 Java 源码之前**：让 LLM 先读语法规则再读代码，带着规则去翻译
- **规则可编辑**：权威版在 YAML 配置里，非工程师可以直接改，代码内只有 fallback 短版
- **不做约束解码**：OpenAI API 不支持逐 token logits 访问，无法在解码时只允许合法 token 序列。但 `cjpm build` 编译失败 → 错误反馈 → LLM 重试，已经是 rejection sampling 的形态——grammar prompt 减少首次犯错的概率，编译验证兜底

### 2.6 代码定位

| 步骤 | 文件 | 函数/变量 |
|---|---|---|
| 单例加载 | `grammar_prompt.py` | `get_grammar_prompt()` / `build_grammar_prompt()` |
| 注入 | `prompt_generator.py` | `self.grammar_context` / `build_base_prompt()` |
| 模板配置 | `configs/prompt_templates.yaml` | `cangjie_grammar_context` / `cangjie_grammar_runtime_note` |

---

## 3. Part 3：语法图 RAG — 结构相似检索

**触发条件**：`--use_syntax_rag=true`

**参考论文**：B3 (CodeGRAG, arXiv:2405.02355) / B4 (Syntax-Aware RAG, EMNLP 2023 Findings)

### 3.1 核心思路

CodeGRAG 论文从代码提取控制流图（CFG）和数据流图（DFG）融合成组合语法图，用 GNN 加跨语言预训练模型检索结构相似代码。关键发现是语法图可以作为跨语言桥梁——不同语言的控制流/数据流结构相似，可以跨语言检索。

我们做了实用化简化版：纯正则结构指纹 + Jaccard 相似度，无 NN/CUDA/额外依赖。

### 3.2 阶段 A：索引构建（离线，整个项目只做一次）

```
┌─────────────────────────────────────────────────────┐
│  方式 1: 手动预建                                     │
│  bash scripts/java/build_syntax_graph_index.sh       │
│                                                      │
│  方式 2: 首次 use_syntax_rag=true 时自动构建           │
│                                                      │
│  1. build_syntax_graph_index(corpus_root)            │
│     ↓                                                │
│  2. _iter_cangjie_code_blocks() 扫描 CangjieCorpus   │
│     - 扫 .cj / .cangjie / .cj.txt 文件               │
│     - 扫 .md 文件里的 ```cangjie / ```cj 围栏块       │
│     - 每个代码块按 ~50 行切分                          │
│     ↓                                                │
│  3. 对每个代码块调 infer_structural_signature()       │
│     提取结构指纹 StructSig (见 3.3)                   │
│     ↓                                                │
│  4. pickle 序列化到                                   │
│     data/java/rag/syntax_graph_index.pkl             │
│     + JSONL 人类可读副本                               │
│     (12874 个代码块)                                  │
└─────────────────────────────────────────────────────┘
```

### 3.3 结构指纹 StructSig — 语言无关提取

`infer_structural_signature(code, category)` 对 Java 或 Cangjie 代码统一提取，语言无关（关键字 token 集合包含 Java 和 Cangjie 两种范式）：

| 维度 | 内容 | 桶化方式 |
|---|---|---|
| `shape_bag` | 12 个操作类别的计数 | 0=无, 1=1次, 2=2-4次, 3=≥5次 |
| `call_names` | 方法调用点标识符（去除控制流关键字） | 集合 |
| `container_types` | 命中常见集合类型名（list/array/map/set 等） | 集合 |
| `category` | corpus 目录粗分类（std/manual/extra） | 字符串 |

12 个操作类别：

```
cf_if            - if 语句计数
cf_loop          - for/while 计数
cf_switch_match  - switch/match 计数
cf_return        - return 计数
cf_throw         - throw 计数
cf_try_catch     - try/catch 计数
op_call          - 方法调用计数
op_index         - 数组索引计数
op_field_access  - 字段访问计数
op_new_alloc     - new/alloc 计数
op_assign        - 赋值计数
op_lambda        - lambda 计数
```

### 3.4 阶段 B：检索注入（每个 fragment 执行）

```
┌─────────────────────────────────────────────────────┐
│  5. PromptGenerator.load_fragment() 完成后            │
│     检测到 use_syntax_rag == 'true'                   │
│     ↓                                                │
│  6. get_syntax_graph_rag() 获取单例 retriever         │
│     ↓                                                │
│  7. _SyntaxGraphRAG.__init__():                      │
│     a. 检查 index.pkl 是否存在                        │
│     b. 不存在 → 自动调 build_syntax_graph_index()     │
│     c. 存在 → pickle.load 加载索引                    │
│     ↓                                                │
│  8. retrieve(source_fragment_body, top_k=3)           │
│     ↓                                                │
│  9. 对 Java fragment 提取结构指纹：                    │
│     infer_structural_signature(java_code, "")        │
│     → 得到 Java 侧的 StructSig                        │
│     ↓                                                │
│ 10. 遍历索引中所有 Cangjie 代码块的 StructSig         │
│     计算加权 Jaccard 相似度 (见 3.5)                  │
│     ↓                                                │
│ 11. 过滤 score < 0.05 的低质量匹配                    │
│     取 top-3 得分最高的 Cangjie 代码块                 │
│     ↓                                                │
│ 12. format_retrieved_snippets()                      │
│     格式化为 prompt 文本块                             │
│     ↓                                                │
│ 13. 存入 self.syntax_graph_context                    │
└─────────────────────────────────────────────────────┘
```

### 3.5 加权 Jaccard 相似度

```
shape_sim      = Jaccard(java.shape_bag, cj.shape_bag)
call_sim       = Jaccard(java.call_names, cj.call_names)
container_sim  = Jaccard(java.container_types, cj.container_types)

score = 0.6 * shape_sim
      + 0.25 * call_sim
      + 0.15 * container_sim
```

**为什么 shape 权重 0.6 最高**：控制流结构（if/loop/try-catch 的组合）是代码"骨架"的最强信号。两段代码如果控制流结构相似，大概率是同类操作（比如都是"遍历集合 + 条件过滤 + 收集结果"）。call_names 权重 0.25 次之——调用的方法名相似说明用了相同 API 模式。container_types 权重 0.15 最低——用了什么集合类型只是辅助信号。

### 3.6 prompt 注入位置

```
     ### RAG Documentation                            │
     [Cangjie 文档级语义检索结果]                       │
                                                      │
     ### Structural Examples  ← Part 3 注入位置        │
     [top-3 结构相似 Cangjie 代码片段]                  │
                                                      │
     ### ICL Examples                                 │
     [自适应上下文学习样例]                             │
                                                      │
     ### Error Feedback                               │
     [编译错误反馈，仅重试时]                           │
                                                      │
     ### Response:                                    │
```

### 3.7 关键设计点

- **为什么用 Jaccard 而不是余弦相似度**：结构指纹是集合和桶化计数，不是向量。Jaccard 是集合相似度的自然选择，且计算开销极小——12874 个块逐一比较也能在毫秒级完成。
- **与现有 RAG 的关系**：项目原有的 `src/java/rag/` 是文档级语义检索（ChromaDB vector + BM25 + RRF），检索的是 Cangjie 标准库 API 文档。Part 3 是结构级检索，检索的是真实 Cangjie 代码片段。两者回答不同问题——原 RAG 说"该用什么 API"，Part 3 说"该写什么样的代码骨架"。在 prompt 里原 RAG 在前、Part 3 在后，互补。
- **为什么是"实用化简化"**：CodeGRAG 原论文用 GNN + 跨语言预训练代码搜索模型，需要 CUDA、训练数据、模型权重。我们的纯正则 + Jaccard 方案零额外依赖、零 GPU、无需 Cangjie tree-sitter grammar（我们没有），就能拿到 +4.5pp 的最大单部分增益。代价是精度不如完整 CodeGRAG——后续可以升级。

### 3.8 代码定位

| 步骤 | 文件 | 函数/变量 |
|---|---|---|
| 索引构建 | `syntax_graph.py` | `build_syntax_graph_index()` / `_iter_cangjie_code_blocks()` |
| 结构指纹提取 | `syntax_graph.py` | `infer_structural_signature()` / `StructSig` |
| 检索 | `syntax_graph.py` | `_SyntaxGraphRAG.retrieve()` / `get_syntax_graph_rag()` |
| 相似度计算 | `syntax_graph.py` | `_jaccard()` |
| 注入 | `prompt_generator.py` | `self.syntax_graph_context` / `build_base_prompt()` |
| 索引构建脚本 | `scripts/java/build_syntax_graph_index.sh` | — |

---

## 4. 三部分对比总结

| 维度 | Part 1 伪代码中间层 | Part 2 语法 EBNF 注入 | Part 3 语法图 RAG |
|---|---|---|---|
| 解决的错误 | A: 错误继承 Java 源模式 | B: 使用错误的 Cangjie 语法 | B: 使用错误的 Cangjie 语法 |
| 参考论文 | A1 (arXiv 2510.00920) | B2 (ACL 2023) | B3 (arXiv 2405.02355) |
| 核心机制 | 两阶段 LLM 调用 | 静态文本注入 | 结构指纹检索 |
| 执行时机 | 每 fragment Phase-1 LLM 调用 | 初始化时缓存一次 | 每 fragment 一次内存检索 |
| 额外开销 | ~30% 耗时（多一次 LLM 调用） | 几乎零（静态文本） | 毫秒级（纯内存 Jaccard） |
| 注入位置 | Java 源码之后 | instruction 之后、源码之前 | RAG 文档之后、ICL 之前 |
| 单部分增益 | +2.1pp | +3.7pp | +4.5pp |
| CLI flag | `--use_pseudocode` | `--use_grammar_prompt` | `--use_syntax_rag` |
