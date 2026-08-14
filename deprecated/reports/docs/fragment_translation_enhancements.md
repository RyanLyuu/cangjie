# Fragment 翻译优化：实现说明文档

> 本文记录 x2cangjie 三项 fragment 翻译增强改造的设计、实现与使用方式：
> - **Part 1**: 伪代码中间层（Java → 伪代码 → Cangjie 两阶段翻译）
> - **Part 2**: Cangjie 语法 / EBNF 规则注入
> - **Part 3**: 语法图 RAG（CFG/DFG 结构相似检索）
>
> 文末附"完整项目运行流程"。

---

## 总体思路

x2cangjie 的 fragment 翻译有两类错误：
- **A: 错误继承 Java 源语法/API 模式** — LLM 倾向于模仿 Java 源实现方式，即使 Cangjie 不支持该模式。
- **B: 使用错误的 Cangjie 语法/API** — LLM 对 Cangjie 训练数据稀薄，不知道该怎么写。

针对上述问题分别引入：
- **Part 1** 解决 A：先让 LLM 将 Java fragment 解为语言无关的"伪代码 + 自然语言注释"中间表示，再基于伪代码 + 元数据翻译成 Cangjie。两阶段解耦"理解 Java 语义"和"生成正确 Cangjie 语法/API"。
- **Part 2** 解决 B：将 Cangjie 关键语法规则以 EBNF 摘要 + 运行时映射注释的形式注入 prompt 作为硬约束提示，不依赖约束解码。
- **Part 3** 同时缓解 A/B：从 CangjieCorpus 提取控制流 + 数据流结构指纹，按结构相似度检索并注入 few-shot 结构示例。

三部分均为**默认关闭**（`"false"`），按 flag 开启，**向后兼容**：
- 关闭时行为与改造前完全一致。
- 互为独立，可单独或组合打开。
- 失败退化（fail-open）：任何 Part 失败时不影响主流程，仅打印警告。

参考论文索引详见 `docs/related_work_code_translation.md`。

---

## Part 1 — 伪代码中间层

### 动机

灵感来自 *Can Emulating Semantic Translation Help LLMs with Code Translation? A Study Based on Pseudocode*（arXiv:2510.00920）。论文在 Python/Java/C++/Go/Rust 上证明：相比于直接 `Source → Target`，使用伪代码中间表示可以显著减少"直接翻译时 LLM 模仿源语言实现方式导致的语义错误"。x2cangjie 中 Cangjie 是低资源语言，伪代码中间层解耦了语义理解与目标语言渲染，特别契合我们的场景。

### 设计要点

1. **两阶段**：
   - Phase 1 — `Java fragment → 伪代码（带 `//` 自语注释、语言无关、纯自然语言描述操作意图）`，作为"语义桥梁"。
   - Phase 2 — `伪代码 + 元数据（部分骨架、泛型规则、RAG 文档、KB 例子、Part 2/3 注入）→ Cangjie`，作为实际翻译。
2. **不丢弃 Java 源码**：Phase 2 的 prompt 同时包含 Java 源代码和伪代码，伪代码居中解决歧义。这与论文中 "Strategy 4/5" 一致 —— LLM 可对照源码化解伪代码模糊性。
3. 失败退化为直接翻译 — Phase 1 LLM 调用失败（网络/JSON/空响应）时返回空串，主翻译继续进行无语义桥梁的版本。

### 实现位置

| 文件 | 变更 |
|---|---|
| `src/java/translation/compositional_translation_validation.py` | 新增 `PSEUDOCODE_SYSTEM_PROMPT`、`_extract_pseudocode()`、`_generate_pseudocode(fragment, args, model_info, client) -> str`；`translate()` 循环在构建 `PromptGenerator` 前先调用一次 LLM 拿伪代码块，再以 `pseudocode=` 形参传入；`__init__` 的 `argparse` 加入 `--use_pseudocode`（默认 `"false"`）。 |
| `src/java/translation/prompt_generator.py` | `__init__` 新增 `pseudocode=""` 与 `_skip_prompt_build=False` 形参，新增 `self.pseudocode_context`；新增 `add_pseudocode_bridge()` 方法；`build_base_prompt()` 在 Java 源代码之后、partial translation 之前注入伪代码桥梁文本。 |
| `configs/prompt_templates.yaml` | 新增模板 `pseudocode_generation_system`、`pseudocode_generation_user`、`pseudocode_bridge_context`（供人审阅；运行期使用代码内嵌字符串以保证确定性，见 `_generate_pseudocode()`）。 |
| `scripts/java/translate_fragment.sh` | 新增第 9 位置参数 `use_pseudocode`（默认 `"false"`），加校验，透传 `--use_pseudocode=` 给 Python。 |

### Phase-1 prompt 规约

要求 LLM 输出的伪代码块：
- 仅一套三反引号包裹；
- 仅使用 `FOR / WHILE / IF / ELSE / RETURN / BREAK` 等通用关键字；
- 每个 Java API 调用改写为动词短语（如 `Collections.sort(xs)` → `sort xs in place`）；
- 每个逻辑块前用 `//` 注释说明意图；
- 不提及 Cangjie/Python 等任何目标语言；
- 保持原始控制流顺序与变量名。

`_extract_pseudocode()` 用启发式剥离三反引号围栏，失败时返回原文本，确保下游 PromptGenerator 能拿到非空字符串。

### `_skip_prompt_build` 钩子

`_generate_pseudocode` 内部只需要 `source_fragment_code`（组装好的 Java fragment），不需要 RAG/KB/generics/grammar/syntax-graph 等昂贵上下文。因此 PromptGenerator 加了一个内部 `_skip_prompt_build` 形参：置 `True` 时在 `load_fragment()` 之后即 `return`，跳过昂贵上下文加载与 prompt 构建。这避免了一次"只想要源码却白跑了全套检索"的开销，尤其是避免另一次无谓的 RAG 调用。

---

## Part 2 — Cangjie 语法 / EBNF 注入

### 动机

灵感来自 *Grammar Prompting for Domain-Specific Language Generation with Large Language Models*（Wang et al., ACL 2023）—— 证明**仅**在 prompt 里写入目标语言的 EBNF 规则（无需约束解码）已经能显著提升低资源/DSL 目标语言的语法正确率。Cangjie 对 LLM 而言近乎 DSL。DocCGen（EMNLP 2024）进一步证明从文档提取 grammar/schema 用于约束生成，在 OOD（未见库/低资源）场景效果显著。

### 设计要点

==Cangjie 是新语言，LLM 训练数据里几乎没有 Cangjie 代码。LLM 翻译时只能靠猜——猜语法规则、猜关键字、猜类型名。猜错就编译失败。
比如 LLM 翻译 Java 的泛型方法，会写成：
// LLM 猜的（Java 风格，Cangjie 里编译报错）==

```
func foo<T extends Comparable<T>>(x: T): T { ... }
```

==但 Cangjie 的正确写法是：
// Cangjie 正确语法==

```
func foo<T>(x: T): T where T <: Comparable<T> { ... }
```

==extends → <:，泛型约束位置不同。LLM 不知道这个差异，因为没有 Cangjie 代码可学。
EBNF 就是把 Cangjie 的语法规则显式写进 prompt，让 LLM 在生成代码之前先读一遍规则。这相当于开卷考试——之前是闭卷（LLM 靠记忆猜），现在是开卷（LLM 可以照着规则表写）。==

1. **EBNF 摘要**（变量/函数/类声明、控制流、match 等）+ **8 条硬语义约束**（G1-G8）作为 prompt 头部硬约束块。
2. **运行时类型映射注释**（`Object → AnyHashable`、`Runnable → () -> Unit` 等一组高频 API 名映射），在 grammar 块之后附加，"名字你必须 NOT 用；等价映射"。
3. **可编辑**: 规则权威版放 `configs/prompt_templates.yaml`（`cangjie_grammar_context` / `cangjie_grammar_runtime_note`），不写死代码 —— 非工程师可直接编辑。代码内有 fallback 短版以便配置不可达时仍可工作。
4. **缓存一次**: `get_grammar_prompt()` 单例懒加载，所有 fragment 共享同一块文本，避免重复 YAML 解析。

### 实现位置

| 文件 | 变更 |
|---|---|
| `src/java/translation/grammar_prompt.py` | 新模块。`build_grammar_prompt()`、`get_grammar_prompt()` 单例 + `reset_cache()`；从 `configs/prompt_templates.yaml` 加载（缓存），失败回退到模块内 `_FALLBACK_GRAMMAR` / `_FALLBACK_RUNTIME`。 |
| `src/java/translation/prompt_generator.py` | 顶部 import `get_grammar_prompt`；`__init__` 加 `self.grammar_context`，当 `args.use_grammar_prompt == 'true'` 时调用 `get_grammar_prompt()` 取得文本；`build_base_prompt()` 在 `add_instruction()` 之后、`add_source_code()` 之前注入 grammar 文本，让模型先读硬约束再读 Java 源码。 |
| `configs/prompt_templates.yaml` | 新增长模板 `cangjie_grammar_context`（EBNF 摘要 + G1-G8 约束）、`cangjie_grammar_runtime_note`（API 名映射表）。 |
| `scripts/java/translate_fragment.sh` | 新增第 10 位置参数 `use_grammar_prompt`（默认 `"false"`），加校验，透传 `--use_grammar_prompt=`。 |

### 为什么不做约束解码

论文里的 Earley parser 约束解码需要逐 token 访问 logits，OpenAI API 仅能用 `logit_bias` 间接近似；且 `cjpm build` 编译验证 + `--validate_by_cangjie` 重试回路已经是一套"rejection sampling"的形态 —— 我们在编译失败时进入 feedback 循环，让 LLM 在错误信号下自纠正。Grammar Prompt 注入是在不破坏现有 API 调用架构的前提下拿到 deltas 最低成本的方式。

---

## Part 3 — 语法图 RAG（CFG/DFG 结构相似检索）

### 动机

灵感来自 *CodeGRAG: Extracting Composed Syntax Graphs for Retrieval Augmented Cross-Lingual Code Generation*（Huang et al., 2024）。CodeGRAG 从代码提取 CFG + DFG，用 GNN + 跨语言检索器检索结构相似片段做 few-shot。我们做"实用化简化版"：纯正则结构指纹 + Jaccard 相似度，无 NN/CUDA/额外依赖。

### 结构指纹

对 Java 或 Cangjie 代码块统一提取 `StructSig`（语言无关，因为关键字 token 集合包含 Java 与 Cangjie 两种范式）：
- **shape_bag**: 桶化计数（0/1/2-4/≥5 → "0/1/2/3"）的 12 个操作类别，包括 `cf_if / cf_loop / cf_switch_match / cf_return / cf_throw / cf_try_catch / op_call / op_index / op_field_access / op_new_alloc / op_assign / op_lambda`。
- **call_names**: 方法调用点的标识符集合（去除 `if/for` 等控制流关键字）。
- **container_types**: 命中常见集合类型名（list/array/map/hashmap/set 等）。
- **category**: 由 corpus 目录粗分类（std/manual/extra）。

容器类型与函数调用名只起"语义微调"作用，结构 shape 权重最大。这是个"风格启发"而非精确等价的 CFG/DFG 同构判断。

### 实现

| 文件 | 变更 |
|---|---|
| `src/java/rag/syntax_graph.py` | 新模块。`infer_structural_signature(code, category)` 公共提取器，`StructSig` dataclass；`build_syntax_graph_index(corpus_root, out_path)` 扫 `CangjieCorpus` 下 `.cj/.cangjie/.cj.txt` 文件和 `.md` 中 ```cangjie/cj``` 围栏块，pickle 序列化 `data/java/rag/syntax_graph_index.pkl`（+ `.jsonl` 人读副本）；`_SyntaxGraphRAG` 单例 retriever（Jaccard 加权：`0.6*shape + 0.25*call + 0.15*container`，得分 <0.05 丢弃），首次调用 _lazy build 索引若无则尝试在线 build。 |
| `src/java/translation/prompt_generator.py` | 顶部 import `get_syntax_graph_rag`；`__init__` 加 `self.syntax_graph_context` 占位字段；在 `load_fragment()` 之后、`build_base_prompt()` 之前，当 `args.use_syntax_rag == 'true'` 时调用 `sgrag.inject(self.source_fragment_body, top_k=3)`；`build_base_prompt()` 在 RAG 文档之后、ICL 之前注入结构示例块。 |
| `tests/test_syntax_graph.py` | 4 个 unit test：提取器、跨语言相似、空代码、无索引时 graceful 返回 ""。 |
| `scripts/java/build_syntax_graph_index.sh` | 一键脚本：`bash scripts/java/build_syntax_graph_index.sh [corpus_root]`，可选预构建索引（retriever 也会第一次调用时 lazy-build，但预建会更快）。 |
| `scripts/java/build_mock_corpus.sh` | （未改动，仅文档对齐说明）。 |

### 旁路附加：语法图 RAG vs 原 RAG

本项目已有 `src/java/rag/` 语义检索（ChromaDB vector + BM25 + RRF）用于文档检索（如 Cangjie 标准库 API 文档）；Part 3 是**结构检索**（结构指纹），互补：原 RAG 回答"该用什么 API"，Part 3 回答"该写什么样的代码骨架"。

---

## CLI flag 与组合建议

### 新增三个 flag

```text
--use_pseudocode           Part 1: 伪代码中间层
--use_grammar_prompt       Part 2: Cangjie EBNF 语法提示
--use_syntax_rag           Part 3: 语法图 RAG 结构相似检索
```

全部默认 `"false"`，与现有 `--use_rag / --use_progressive_kb` 一致，按 `"true"/"false"` 字符串形式传入。

### `translate_fragment.sh` 调用

```bash
# 旧行为（全部新参数默认 false，向后兼容）
bash scripts/java/translate_fragment.sh jansi deepseek-chat _evosuite_cleaned_base 0.0 true true false true

# 全开（建议组合，最重，质量优先）
bash scripts/java/translate_fragment.sh jansi deepseek-chat _evosuite_cleaned_base 0.0 \
    true true false true \
    true true true

# 仅 Part 1 + Part 2（推荐起点：解耦语义继承 + 提语法）
bash scripts/java/translate_fragment.sh jansi deepseek-chat _evosuite_cleaned_base 0.0 \
    true true false true \
    true true false

# 仅 Part 3（结构示例；可作为 RAG 文档检索的补充）
bash scripts/java/translate_fragment.sh jansi deepseek-chat _evosuite_cleaned_base 0.0 \
    true true false true \
    false false true
```

### 推荐组合

| 场景 | use_pseudocode | use_grammar_prompt | use_syntax_rag |
|---|---|---|---|
| 仅修 Java→Cangjie API 模式继承错 | true | false | false |
| 不熟悉 Cangjie 语法（多为编译报语法错） | false | true | false |
| 需要 few-shot 结构模板 | false | false | true |
| **推荐起点**：同时解 A+B，性价比最高 | true | true | false |
| 全开（贵但增益最高） | true | true | true |

### 调试辅助

- `debug.sh <project> <model> <suffix> <temp> [use_rag]` 已有的更底层 wrapper 不变 —— 你只要给它 `use_pseudocode=true` 等额外参数。**注意**:`debug.sh` 目前 `tee "$@"`，要使用新参数请直接以位置参数传入，例如：`bash debug.sh jansi deepseek-chat _evosuite_cleaned_base 0.0 true false false true true true true`。三反引号里第 5-11 位置参数照旧 (use_rag, skip_mock, translate_tests, use_progressive_kb, use_pseudocode, use_grammar_prompt, use_syntax_rag)。

---

## 新增 / 修改文件清单

### 新增

```
src/java/translation/grammar_prompt.py                           # Part 2 模块
src/java/rag/syntax_graph.py                                     # Part 3 模块
tests/test_grammar_prompt.py                                     # Part 2 单测
tests/test_syntax_graph.py                                       # Part 3 单测
scripts/java/build_syntax_graph_index.sh                         # Part 3 索引构建脚本
docs/fragment_translation_enhancements.md                        # 本文档
```

### 修改

```
src/java/translation/compositional_translation_validation.py      # Part 1: _generate_pseudocode() + translate() 循环注入 + CLI flag
src/java/translation/prompt_generator.py                         # Part 1/2/3: 形参、上下文加载、build_base_prompt 注入点
configs/prompt_templates.yaml                                    # Part 1/2 模板
scripts/java/translate_fragment.sh                               # 三个新位置参数 + 校验 + 透传
```

---

## 运行需知 / 失败退化行为

- 所有新模块**fail-open**：任何异常均被 `try/except` 捕获，仅 `print(f"[...] Warning: ...")`，不影响主翻译循环。
- Part 3 **首次开 `use_syntax_rag=true`** 时若 `data/java/rag/syntax_graph_index.pkl` 不存在，会触发 `build_syntax_graph_index()` 重新扫 `misc/CangjieCorpus`。建议提前用 `bash scripts/java/build_syntax_graph_index.sh` 预建索引以加速首次运行。
- Part 1 与 Part 3 在 `_skip_prompt_build=True` 的伪代码生成阶段不会触发 Part 2/Part 3 的上下文加载 —— Part 1 内部 PromptGenerator 只用 `source_fragment_code`，避免重复 RAG 检索。
- 当前对每个有 `--use_pseudocode=true` 的 fragment 会多一次 LLM 调用（Phase-1 伪代码生成）。LLM token 消耗约 +20-40%（取决于 fragment 大小）。如需极致，可在 `--recursion_depth=1` 时提前跳过伪代码（当前实现并不跳过——所有递归层均尝试伪代码，因为是按 fragment 粒度而非按递归层 —— 一般 recursion_depth=2 不会有大量子 fragment，开销可控）。

---

## 单元测试 / 验证

| 测试 | 覆盖 |
|---|---|
| `tests/test_grammar_prompt.py::test_build_grammar_prompt_returns_nonempty_block_with_ebnf_marker` | Part 2 加载与产物 |
| `tests/test_grammar_prompt.py::test_get_grammar_prompt_is_cached` | 单例缓存 |
| `tests/test_grammar_prompt.py::test_cache_reset_reloads` | fallback 路径 |
| `tests/test_syntax_graph.py::test_signature_has_control_flow_tokens_for_loop_and_branch` | Part 3 提取器 |
| `tests/test_syntax_graph.py::test_cross_lingual_similarity_high_for_equivalent_structure` | 跨语言相似度 |
| `tests/test_syntax_graph.py::test_signature_empty_for_blank_code` | 边界 |
| `tests/test_syntax_graph.py::test_singleton_returns_empty_when_no_index` | 无索引退化 |

**运行**：

```bash
conda activate x2cangjie
export PYTHONPATH=$(pwd)
python -m pytest tests/test_grammar_prompt.py tests/test_syntax_graph.py -v
```

> 注：本机 Windows 环境无 Python/pytest，本仓库在 Docker 内使用 conda env `x2cangjie` 运行。新增测试用 monkeypatch 重定向 RAG 默认路径，**不需要** Cangjie SDK / ChromaDB / LLM 调用，纯单元可跑。

---

## 已知限制与后续可改进项

1. **Part 1 可优 ablation**：论文 A6 警告伪代码增益可能部分来自 CoT 多步推理效应，而非伪代码语言中立性。建议做 ablation 对比 (a) 直接翻译、(b) CoT 先分析再翻译、(c) 伪代码中间层，分离增量来源。
2. **Part 2 未启用约束解码**：`cjpm build` 编译错误信号已经实现了"rejection sampling"，但 logit-bias 近似约束未做——这是后续可以引入的增量。
3. **Part 3 同构判断粗糙**：纯正则 + Jaccard 是对 CodeGRAG 的简化版；若需要更强，可接 tree-sitter-java 解析 + 真实 CFG/DFG，以及引入跨语言的预训练代码搜索模型做检索源。
4. **Part 1 Phase-1 prompt 还可优化**：可参考论文 GitHub 仓库 `imcsq/Pseudocode-based-Code-Translation` 中的 `02cothint1` 等 prompt 变体，做对比实验。
5. **未做端到端评估**：本次只接通了代码并写了单测，未端到端跑 jansi/commons-cli 实测——需在配置实际 LLM 与 `cjpm` 的 Docker 环境中运行并通过 `analyze_errors.sh` 统计 fragment 通过率增量，以实证上述每部分的收益。

---

# 完整项目运行流程

下面给出从零到 fragment 翻译完成的端到端运行流程，涵盖环境、预处理、schema、依赖、翻译、错误分析，以及本次新增的三部分如何在最后一步被开关控制地叠加进去。

## 0. 环境与依赖

```bash
conda activate x2cangjie
export PYTHONPATH=$(pwd)                       # 必需，所有 python 调用都依赖
export OPENAI_API_KEY="sk-or-..."
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"   # 或你的 provider
# Cangjie SDK（cjc / cjpm）必须自行安装并加入 PATH；不可经 conda/maven 获得
which cjc cjpm                                  # 应均返回可执行路径
# misc/ 下的 tree-sitter-java/python v0.23.5、java-callgraph、CangjieCorpus 必须已 clone 与 build
# configs/model_configs.yaml 必须从 .example 拷贝并填好 model_id / base_url / api_key
```

详细搭建见 `Dockerfile` 与 `docs/start.md` 第 1-3 步。

## 1. Java 侧预处理

```bash
# 对 EvoSuite clean base 流程：先按 evosuite_cleaned_base_commands.md 走 0-3 步，
# 产物落到 cleaned_final_projects_evosuite_cleaned_base/$project
bash scripts/java/preprocess.sh jansi           # 或对 evosuite clean base，参照 evosuite_cleaned_base_commands.md
# 产物：projects/java/cleaned_final_projects[_evosuite_cleaned_base]/jansi/ ...
```

## 2. schema 生成

```bash
model=deepseek-chat
temp=0.0
suffix=_evosuite_cleaned_base
bash scripts/java/create_schema.sh jansi "$model" "$temp" "$suffix"
# 产物：data/java/schemas${suffix}/${model}/${temp}/jansi/*.json
```

## 3. 依赖顺序生成

```bash
bash scripts/java/get_dependencies.sh jansi "$suffix"
# 产物：data/java/dependencies${suffix}/jansi/traversal.json
```

## 4. 类型翻译（首次用 RAG 需先建索引）

```bash
# 一次性建 RAG 文档索引
bash scripts/java/crawl_java_base.sh
export OPENAI_API_KEY="sk-or-..."
python -m src.java.rag.indexer

# 执行类型翻译
bash scripts/java/translate_types.sh jansi "$model" "$temp" "$suffix" false true
```

## 5. 骨架生成

```bash
bash scripts/java/create_skeleton.sh jansi "$model" "$suffix" "$temp"
# 产物：data/java/skeletons/jansi/src/*.cj（含 throw Exception('TODO') 占位符）
```

## 6. 构建 mock 测试语料

```bash
bash scripts/java/build_mock_corpus.sh jansi
# 产物：/tmp/cangjie_mock/jansi/
```

## 7.**Fragment 翻译（新增三部分在此处叠加）**

基础调用（旧路径，向后兼容）：

```bash
bash scripts/java/translate_fragment.sh jansi "$model" "$suffix" "$temp" \
    true true false true
# 参数顺序：project model suffix temperature use_rag skip_mock translate_tests use_progressive_kb
```

启用本次新增三部分（在第 9-11 位置参数）：

```bash
# 开启 Part 1 (use_pseudocode) + Part 2 (use_grammar_prompt)，保留原默认
bash scripts/java/translate_fragment.sh jansi "$model" "$suffix" "$temp" \
    true true false true \
    true true false
# 参数：use_rag=true, skip_mock=true, translate_tests=false, use_progressive_kb=true,
#       use_pseudocode=true, use_grammar_prompt=true, use_syntax_rag=false

# 全开三部分（最重，质量最高）
bash scripts/java/translate_fragment.sh jansi "$model" "$suffix" "$temp" \
    true true false true \
    true true true

# 调试模式（tee 全部输出至 ./translate_debug.log）
bash debug.sh jansi "$model" "$suffix" "$temp" \
    true false false true \
    true true true
```

首次开 `use_syntax_rag=true` 时，建议预构建语法图索引以加速：

```bash
bash scripts/java/build_syntax_graph_index.sh misc/CangjieCorpus
# 产物：data/java/rag/syntax_graph_index.pkl + .jsonl
```

主翻译循环的行为：

```
for each fragment in traversal.json (依赖顺序):
    if --use_pseudocode:
        Phase-1 LLM call: Java fragment → 伪代码块（带 // 自语注释）
    else:
        伪代码块 := ""
    PromptGenerator(args, fragment, pseudocode=伪代码块):
        load_fragment()
        if _skip_prompt_build: return              # 仅 _generate_pseudocode 走这条捷径
        construct_adaptive_icl()
        if use_rag: rag.inject_fragment_context()   # 文档级 RAG
        if use_progressive_kb: progressive_kb.retrieve()
        if generics 模式: generics_rule_lib.match_rules()
        if use_grammar_prompt: get_grammar_prompt() → grammar_context
        if use_syntax_rag: syntax_graph_rag.inject(source_fragment_body) → syntax_graph_context
        build_base_prompt():
            persona → instruction → grammar(Part2) → java源 →
            pseudocode_bridge(Part1) → partial_translation → generics →
            kb few-shot → RAG 文档 → syntax graph 示例(Part3) →
            ICL → feedback → "### Response:"
    LLM call → JSON {code, reasoning, imports}
    extract_json_translation() → syntactic check → cangjie_compilation_validation()
    if 编译失败: feedback = 编译错误; 跳回 PromptGenerator 重建带 feedback
    if 编译成功: (skip_mock=false 时) mock 测试 → 继续或回退
    translation_status = success / fallback:*
```

## 8. 错误分析

```bash
bash scripts/java/analyze_errors.sh jansi "$model" "$temp" "$suffix"
# 产物：data/java/analysis/jansi_${model}_${temp}${suffix}_errors.txt
# 含：编译通过/失败统计、错误分类、per-fragment 错误、残留 TODO 检查、CSV 数据导出
```

## 9. 批量运行多个项目

```bash
MODEL=deepseek-chat TEMP=0.0 SUFFIX=_evosuite_cleaned_base \
USE_RAG=true SKIP_MOCK=true TRANSLATE_TESTS=false \
bash scripts/java/run_525_evosuite_round.sh
# 当前在 scripts 内迭代 PROJECTS=(jansi commons-cli)
# 若要叠加本次三部分，需在脚本里或环境变量中加入对应的 use_pseudocode 等
# 该脚本未直接支持这三处环境变量；如需批量叠加，建议手改脚本。
```

## 10. 单元测试新增模块

```bash
conda activate x2cangjie
export PYTHONPATH=$(pwd)
python -m pytest tests/test_grammar_prompt.py tests/test_syntax_graph.py -v
# 不依赖 Cangjie SDK / LLM；纯单元覆盖 Part 2 / Part 3 的提取与降级路径
```

## 11. 回滚

任一 Part 关闭只需将对应位置参数设 `false`，**默认关闭**保证不破坏任何既有路径：

```bash
bash scripts/java/translate_fragment.sh jansi "$model" "$suffix" "$temp" \
    true true false true \
    false false false
```

欢迎阅读 `docs/related_work_code_translation.md` 了解三部分的论文依据与可选演进路径。

---

# 消融测试（ablation）

为量化三部分各自的翻译增益，提供了消融测试工具链：对 2³ = 8 种 flag 组合逐一运行 fragment 翻译、采样 schema 数据，再对翻译通过率等指标做横向对比 + 显著性检验。

## 涉及文件

| 文件 | 用途 |
|---|---|
| `scripts/java/run_ablation.sh` | 一键跑 8 组组合：每组先重建 skeleton、再 translate_fragment、再 snapshot schema 到 per-run 子目录 |
| `src/java/analysis/ablation_compare.py` | 读取 8 个 per-run schema 快照、计算指标、生成 Markdown 报告 + metrics.csv + significance.csv |
| `tests/test_ablation_compare.py` | 单元测试：Fisher exact、stats_to_metrics、generate_markdown_report smoke |
| 旧文件 `src/java/analysis/analyze_errors.py`、`scripts/java/analyze_errors.sh` | 未改动。新代码 `import` `analyze_project()` 复用，不修改 |

## 8 种 run-tag

| run-tag | use_pseudocode | use_grammar_prompt | use_syntax_rag |
|---|---|---|---|
| `baseline` | false | false | false |
| `pseudo` | true | false | false |
| `grammar` | false | true | false |
| `syntax` | false | false | true |
| `pseudo+grammar` | true | true | false |
| `pseudo+syntax` | true | false | true |
| `grammar+syntax` | false | true | true |
| `all` | true | true | true |

run-tag 由 `run_ablation.sh` 自动写入，名称固定不可改（`ablation_compare.py` 中的 `RUN_TAGS` 数组必须与此保持一致）。

## 关键设计点

1. **为何要 snapshot**：`translate_fragment.sh` 每次写回的是 *同一份* schema JSON 目录（`data/java/schemas<suffix>/<model>/<temp>/<project>/`），后一次运行会覆盖前一次的 translation_status/compilation_outcome。因此必须为每个 run-tag 拷贝一份独立的 schema 快照存到 `data/java/ablation/<run-tag>/`，否则后跑的会覆盖前面的统计数据。这是 **必须** 步骤，否则消融数据被污染。
2. **skeleton 同步重建**：`run_ablation.sh` 在每组运行前调一次 `create_skeleton.sh`，保证翻译基线一致；否则前一组翻译产物可能影响后续组的骨架初始状态。
3. **复用既有指标**：`ablation_compare.py` import `analyze_project()` 读取 statistics 字段，**不改旧文件**。
4. **Fisher exact 自实现**：消融脚本不能依赖 scipy（未在 `environment.yaml`），用纯 python `lgamma` + hypergeometric 求和实现 2×2 Fisher exact two-sided p 值；适合 fragment count 在几十到几千之间。
5. **所有新逻辑 fail-open**：run-tag 目录缺失则跳过；todo snapshot 不存在则不报 residual_todos；Fisher 失败则在报告中显示 `nan/n/a`，不抛出。

## 使用流程

### 一键消融（推荐）

```bash
conda activate x2cangjie
export PYTHONPATH=$(pwd)
project=jansi
model=deepseek-chat
suffix=_evosuite_cleaned_base
temp=0.0

# 一键：跑 8 组 + 快照 + 自动出报告
bash scripts/java/run_ablation.sh \
    "$project" "$model" "$suffix" "$temp" \
    true true false true     # use_rag skip_mock translate_tests use_progressive_kb
```

输出：

```
data/java/ablation/<project>_<model>_<temp><suffix>/
├── baseline/              ├── pseudo+grammar/
├── pseudo/                ├── pseudo+syntax/
├── grammar/               ├── grammar+syntax/
├── syntax/                ├── all/
│   ├── *.json             │   ├── *.json
│   └── skeletons/         │   └── skeletons/
├── report.md              ← 主报告（Markdown，含横向对比表 + 显著性表）
├── metrics.csv            ← 8 行 flat 字段 table
└── significance.csv       ← run_tag × metric 的 odds ratio / p 值表
```

进度提示和 `[ablation] RUN: <tag>` 都会打到 console，便于查看哪一组正在跑 / 失败。

### 手动分步（当你只想跑部分组合或已存在的快照不重新翻译）

如果你已有 schema 快照并且不想再跑 8 次翻译，直接调一次性分析：

```bash
# 假设你之前手动跑了 8 次 + 快照到
# data/java/ablation/<project>_<model>_<temp><suffix>/<tag>/ 下

python -m src.java.analysis.ablation_compare \
    --project jansi \
    --model deepseek-chat \
    --temperature 0.0 \
    --suffix _evosuite_cleaned_base \
    --ablation-root data/java/ablation/jansi_deepseek-chat_0.0_evosuite_cleaned_base
```

ablation_root 路径下至少要有 `baseline/` 子目录（报告才能给出 delta），其他 run-tag 缺失会显示 `[WARN] Missing run tags: ...` 但不报错；缺失的那行不会出现在表格里。

### 参数详解

`run_ablation.sh`：

```text
bash scripts/java/run_ablation.sh <project> <model> <suffix> <temperature> \
    [use_rag] [skip_mock] [translate_tests] [use_progressive_kb]
```

- 前 4 个位置参数与 `translate_fragment.sh` 完全一致；
- 后 4 个参数控制每组翻译时的"非增强"复用行为（为所有 8 组共享，即不在 ablation 维度内取差异），建议保持稳定（如 `true true false true` 即 RAG=true、跳过 mock 测试、不翻译测试方法、开启 Progressive KB）；
- `skip_mock=true` 跳过 mock 测试阶段：消融主要关注编译通过率与翻译完成率，测试执行通常慢且需 mock 语料，建议先 `skip_mock=true` 出第一批数据，再针对部分组关掉 skip_mock 做第二轮。

`ablation_compare.py` 直接调用时的参数：

```text
--project             项目名（必填）
--model               模型名（必填）
--temperature         温度（必填）
--suffix              schema 后缀（默认 ""）
--ablation-root       8 个 run-tag 快照子目录的父目录（必填）
--output              Markdown 报告输出路径（默认 <ablation-root>/report.md）
--csv                 metrics.csv 输出路径（默认 <ablation-root>/metrics.csv）
--skip-significance   跳过 Fisher exact 显著性检验（fragment 数太少时使用）
```

## 指标解读

| 指标 | 含义 | 期望方向 |
|---|---|---|
| `total_fragments` | 该 run 处理的 fragment 数（应所有组一致，否则数据被污染） | = |
| `completed` / `completed_rate` | translation_status == 'completed' 的数 / 比例 | ↑ |
| `compiled_pass` / `compiled_pass_rate` | cangjie_compilation.outcome == 'success' 的数 / 比例 | ↑ |
| `test_pass` / `test_pass_rate_of_compiled` | 测试通过的数 / 在编译通过池中的比例 | ↑ |
| `attempted` / `out_of_context` / `pending` | 中间态计数 | ↓（理想情况下 attempted→completed） |
| `residual_todos` / `residual_todos_per_file` | .cj 中残留 `throw Exception('TODO')` 计数 | ↓ |
| `elapsed_mean_s` | 平均每 fragment 耗时 | 视情况（提速 vs 提升） |

报告中三部分横向对比表 + delta vs baseline 表。delta 比例字段用 **pp**（percentage point, 0.1 = 10pp），不是相对百分比。

## 显著性检验（Fisher exact 2×2）

- 对每个非 baseline 的 run-tag 都针对 `completed_pass / test_pass / compiled_pass` 三个指标做 2×2 Fisher exact 二项差异检验。
- table 行列：`[row=baseline 或 alt][col=pass 或 fail]`；`fail = total - pass`。
- 当 p < 0.05 时报告中该格标记 `✓`，否则 `—`。
- 极小样本（如 n<10）该检验稳健性差，请此时加 `--skip-significance` 同时人工对比 delta 即可。
- 由于对每组都做检验，多重比较问题应自行用 Bonferroni 校正解读（~24 个检验，保守 α=0.05/24≈0.0021）。

## 注意事项

1. **样本一致性**：所有组的 `total_fragments` 必须相同（翻译器对所有 fragment 都尝试）。如果在你跑的某组不一致，说明该组中途崩溃或被 out_of_context 截断，需查 schema json。
2. **cjpm 不可用时**：可改用一个固定 mock_dir 让验证失败 + propagate error feedback，但消融数据会被编译排序一侧吞掉——这种情况下 `compiled_pass=0` 的对比无意义，只能看 `completed`。
3. **`create_skeleton` 消耗**：循环每组开头都会重建 skeleton，这会消耗额外的 LLM token（每多一组多一次 skeleton 的元数据写入，影响很小）。
4. **LLM 不稳定性**：`temperature != 0` 的 ablation 每次跑都会不同，单次结果的"增益"可能是在噪声范围内。建议 `temperature=0.0`：现在 8 组都是 deterministic prompt + deterministic 模型时增益才是真实可信的。如温度升高，需要多跑几轮取期望。
5. **总成本估算**：比单跑翻译慢约 9 倍（baseline + 7 enhancement 组）+ 8 次 skeleton 重建。LLM token 成本上升同步。

## 单元测试

```bash
conda activate x2cangjie
export PYTHONPATH=$(pwd)
python -m pytest tests/test_ablation_compare.py -v
```

6 个 test 覆盖：
- Fisher identical table → p=1.0
- Fisher maximal split (0/4 vs 4/0) → p<0.05
- Fisher all-fail identical → p=1.0
- `stats_to_metrics` 扁平化字段（含 todo）
- `stats_to_metrics` 空 dict 不崩
- `generate_markdown_report` smoke（含 delta、显著性、per-part 段落）

## 旧的 `analyze_errors.sh` 仍可独立使用

互不影响：`scripts/java/analyze_errors.sh` 仍对单个 run 输出 `data/java/analysis/<project>_<model>_<temp>_errors.txt`；ablation 工具是 *不同目录* 下的横向对比。所以你的既有分析脚本与本次消融工具并行存在。