# Fragment 翻译增强：原理、实现与消融分析

> 10 页 PPT（Marp / markdown-slides 格式，可用 VS Code Marp 插件或 `marp --pdf` 导出）
> 项目：x2cangjie — Java → 仓颉（Cangjie）自动翻译
> 日期：2026-07-08

---

## Slide 1 — 封面

**Fragment 翻译增强：原理、实现与消融分析**

副标题：基于伪代码中间层、语法注入与结构检索的 LLM 代码翻译改进

汇报人：[你的名字]
项目：x2cangjie
日期：2026-07-08

---

## Slide 2 — 背景：x2cangjie 在做什么

**目标**：把 Java 库自动翻译成仓颉（Cangjie）语言

**Pipeline（8 步）**：
```
preprocess → create_schema → get_dependencies → translate_types
→ create_skeleton → build_mock_corpus → translate_fragment → analyze_errors
```

**核心是第 7 步** `translate_fragment`：LLM 逐个 fragment 翻译，每填一个跑 `cjpm build` 编译验证，失败带错误反馈重试

**观察到的两类系统性错误**：

| 错误类型 | 表现 | 根因 |
|---|---|---|
| **A: 错误继承 Java 源语法/API** | LLM 照搬 Java 的 stream API / checked exception / for-each lambda，Cangjie 不支持 | LLM 模仿源码结构而非理解意图后用目标语言惯用法重写 |
| **B: 使用错误的 Cangjie 语法/API** | 泛型用 `extends` 而非 `where T <: Bound`、`Any` 当 HashMap key、`boolean` 而非 `Bool` | Cangjie 是新语言，LLM 训练数据中几乎没有 Cangjie 代码 |

**针对 A/B 两类错误，做了三件事（Part 1/2/3），互相独立、可单独或组合开关**

---

## Slide 3 — Part 1：伪代码中间层（解决错误 A）

**参考论文**

| 论文 | 出处 | 核心思想 |
|---|---|---|
| **A1: Pseudocode-based Code Translation** | arXiv:2510.00920, 2025 | 模拟人类"语义翻译"策略：源→伪代码→目标，两阶段 |
| A3: NL in the Middle | CASCON 2025 | 自然语言中间表示效果最好（比零样本 +13.8%） |
| A6: Assessing Intermediate Languages | arXiv:2407.05411 | 警示：伪代码收益可能部分来自 CoT 多步推理效应 |

**论文原理（A1）**

- 直接翻译 Python → Java 时，LLM 试图模仿源码结构，生成语义不一致的代码
- 伪代码中间层：LLM 先把源码抽象成语言无关伪代码（描述意图和逻辑），再从伪代码生成目标代码
- 测试 5 种策略组合，发现 **"伪代码 + 源代码"组合** 效果最好——伪代码居中解决歧义，源码作为 fallback

**项目实现**

```
原流程:  Java fragment → [prompt] → LLM → Cangjie
新流程:  Java fragment → LLM → 伪代码+注释  ← Phase-1 (新增)
                ↓
          伪代码 + Java源码 + metadata → [prompt] → LLM → Cangjie  ← Phase-2
```

- Phase-1 prompt 规约：仅通用关键字（FOR/WHILE/IF）、API 调用改写为动词短语、每块前 `//` 注释说明意图
- 失败退化为直接翻译：Phase-1 失败返回空串，Phase-2 无伪代码继续
- `_skip_prompt_build` 优化：Phase-1 只需源码，跳过 RAG/KB/generics 昂贵上下文加载

---

## Slide 4 — Part 2：Cangjie 语法 EBNF 注入（解决错误 B）

**参考论文**

| 论文 | 出处 | 核心思想 |
|---|---|---|
| **B2: Grammar Prompting** | Wang et al., ACL 2023 | 将目标语言 BNF 语法规则注入 prompt，**仅 prompt 注入就显著提升语法正确率** |
| B1: DocCGen | EMNLP 2024 | 从文档提取 grammar/schema 做约束解码，对 OOD 场景效果显著 |

**论文原理（B2）**

- 对 DSL（领域特定语言），LLM 训练数据中几乎没见过该语言
- 方法：在 prompt 中注入目标语言的 BNF 语法规则，让 LLM 在生成时参考
- 实验发现 **不约束解码、仅在 prompt 中提供 grammar 就已经有显著提升**
- 对 DSL 效果最好——因为 DSL 在训练数据中罕见

**Cangjie 对 LLM 就是 DSL** —— 训练数据极少，不知道 `where T <: Bound`、`AnyHashable`、`Bool`

**项目实现**

新建 `grammar_prompt.py`，注入两部分文本：

**第一部分：EBNF 语法摘要 + 8 条硬约束（G1-G8）**

| 约束 | 对应典型错误 |
|---|---|
| G1 泛型用 `where T <: Bound` | Java `? extends T` |
| G3 `Any` 不满足 `Hashable`，用 `AnyHashable` | `HashMap<Object, V>` 编译报错 |
| G5 布尔类型是 `Bool` 不是 `boolean` | Java `boolean` |
| G6 字符串插值 `"${expr}"` | Java `String.format` |

**第二部分：运行时 API 映射表**（`Object` → `AnyHashable`、`Runnable` → `() -> Unit` 等）

- 可编辑：规则权威版在 `configs/prompt_templates.yaml`，不写死代码
- 缓存一次：`get_grammar_prompt()` 单例懒加载
- 不做约束解码：OpenAI API 不支持逐 token logits，靠 `cjpm build` 编译错误反馈实现 rejection sampling

---

## Slide 5 — Part 3：语法图 RAG（CFG/DFG 结构相似检索）

**参考论文**

| 论文 | 出处 | 核心思想 |
|---|---|---|
| **B3: CodeGRAG** | Huang et al., arXiv:2405.02355, 2024 | 从代码提取 CFG+DFG 融合图，用 GNN + 跨语言检索，检索结构相似代码片段 |
| B4: Syntax-Aware RAG | EMNLP 2023 Findings | 在 RAG 中引入语法感知——不只用语义相似检索，还用语法结构相似度 |

**论文原理（B3 CodeGRAG）**

1. **提取**：从代码提取控制流图（CFG）和数据流图（DFG），融合为"组合语法图"
2. **检索**：用混合 GNN + 预训练跨语言代码搜索模型计算相似度，检索结构相似代码块
3. **注入**：检索到的语法图作为 LLM 上下文，辅助生成
- 关键发现：**语法图作为跨语言桥梁**——不同语言的控制流/数据流结构相似，可跨语言检索

**项目实现（实用化简化）**

纯正则结构指纹 + Jaccard 相似度，无 NN/CUDA/额外依赖：

| 维度 | 内容 |
|---|---|
| `shape_bag` | 12 个操作类别计数（cf_if / cf_loop / op_call / op_index 等），桶化为 0-3 |
| `call_names` | 方法调用点标识符集合 |
| `container_types` | 命中集合类型名（list/array/map/set 等） |

检索：Jaccard 加权相似度 = `0.6×shape_sim + 0.25×call_sim + 0.15×container_sim`，返回 top-3

索引：扫描 CangjieCorpus（12874 个代码块），pickle 序列化到 `data/java/rag/syntax_graph_index.pkl`

**与现有 RAG 互补**：原 RAG 是文档级检索（"该用什么 API"），Part 3 是结构级检索（"该写什么样的代码骨架"）

---

## Slide 6 — 三部分如何组合工作

**Prompt 注入顺序**

```
persona → instruction → grammar (Part 2) → Java source
→ pseudocode bridge (Part 1) → partial translation
→ generics context → Progressive KB few-shot
→ RAG docs → syntax graph (Part 3) → ICL → feedback → "### Response:"
```

**CLI 开关（三个 flag 默认 false，向后兼容）**

```bash
bash scripts/java/translate_fragment.sh <project> <model> <suffix> <temp> \
    <use_rag> <skip_mock> <translate_tests> <use_progressive_kb> \
    <use_pseudocode> <use_grammar_prompt> <use_syntax_rag>
```

| 场景 | use_pseudocode | use_grammar_prompt | use_syntax_rag |
|---|---|---|---|
| 仅修 Java→Cangjie API 模式继承错 | true | false | false |
| 不熟悉 Cangjie 语法（多为编译报语法错） | false | true | false |
| 需要 few-shot 结构模板 | false | false | true |
| **全开（增益最高）** | true | true | true |

**设计逻辑**：grammar 在最前（先读规则再读代码）；伪代码在源码后（理解意图后再翻译）；结构示例在 RAG 文档后、ICL 前（作为"怎么写"的模板参考）

---

## Slide 7 — 代码结构

**新增/修改文件清单**

```
新增:
  src/java/translation/grammar_prompt.py       # Part 2 模块
  src/java/rag/syntax_graph.py                 # Part 3 模块
  src/java/analysis/ablation_compare.py        # 消融对比分析
  scripts/java/build_syntax_graph_index.sh     # Part 3 索引构建
  scripts/java/run_ablation.sh                 # 一键消融 sweep
  tests/test_grammar_prompt.py                 # Part 2 单测
  tests/test_syntax_graph.py                   # Part 3 单测
  tests/test_ablation_compare.py               # 消融分析单测

修改:
  src/java/translation/compositional_translation_validation.py  # Part 1 + CLI flags
  src/java/translation/prompt_generator.py                      # Part 1/2/3 注入点
  configs/prompt_templates.yaml                                 # Part 1/2 新模板
  scripts/java/translate_fragment.sh                            # 3 个新位置参数
```

**关键代码入口**

| 想了解 | 读这个文件 |
|---|---|
| 翻译主循环 | `compositional_translation_validation.py` 的 `translate()` |
| prompt 组装 | `prompt_generator.py` 的 `build_base_prompt()` |
| Part 1 伪代码生成 | `compositional_translation_validation.py` 的 `_generate_pseudocode()` |
| Part 2 语法规则 | `configs/prompt_templates.yaml` 搜 `cangjie_grammar_context` |
| Part 3 结构指纹 | `src/java/rag/syntax_graph.py` 的 `infer_structural_signature()` |
| 消融报告 | `src/java/analysis/ablation_compare.py` |

---

## Slide 8 — 消融实验设计

**为什么需要消融**

A6 论文警告：伪代码中间层的收益可能部分来自 CoT 多步推理效应（多步 > 单步），而非伪代码本身的语言中立性。需要 ablation 分离每部分的增量来源。

**8 种 run-tag（2^3 = 8）**

| run-tag | use_pseudocode | use_grammar_prompt | use_syntax_rag |
|---|---|---|---|
| baseline | false | false | false |
| pseudo | true | false | false |
| grammar | false | true | false |
| syntax | false | false | true |
| pseudo+grammar | true | true | false |
| pseudo+syntax | true | false | true |
| grammar+syntax | false | true | true |
| all | true | true | true |

**实验配置**
- 项目：commons-csv（381 个 fragment）
- 模型：gpt-4o-2024-11-20
- 温度：0.0（确保可复现）
- 每组前重建 skeleton 保证基线一致
- 每组后 snapshot schema 目录避免覆盖
- Fisher exact 双侧 p 值（纯 Python 实现，不依赖 scipy）

---

## Slide 9 — 消融结果

**8 组总览（commons-csv / gpt-4o / 381 fragments）**

| Run tag | 完成 | 完成率 | Δ vs baseline |
|---|---:|---:|---:|
| `baseline` | 241 | 63.3% | — |
| `pseudo` (Part 1) | 249 | 65.4% | +2.1pp |
| `grammar` (Part 2) | 255 | 66.9% | +3.7pp |
| `syntax` (Part 3) | 258 | 67.7% | +4.5pp |
| `pseudo+grammar` (1+2) | 259 | 68.0% | +4.7pp |
| `pseudo+syntax` (1+3) | 260 | 68.2% | +5.0pp |
| `grammar+syntax` (2+3) | 260 | 68.2% | +5.0pp |
| `all` (1+2+3) | 260 | 68.2% | +5.0pp |

**单部分独立效应排序**：Part 3 (syntax, +4.5pp) > Part 2 (grammar, +3.7pp) > Part 1 (pseudo, +2.1pp)

**组合效应**：两两组合接近饱和（+5.0pp），三部分全开无额外增益——说明 Part 2 和 Part 3 覆盖的错误类型有重叠

**显著性**：Fisher exact p 值均 >0.05（单项目 381 样本量不足以达到统计显著），但趋势清晰一致——每个增强单独有效，组合达到饱和

---

## Slide 10 — 结果分析与未来工作

**关键发现**

1. **Part 3（语法图 RAG）单独贡献最大**（+4.5pp）——结构相似的 Cangjie 代码片段是最有效的 few-shot 示例
2. **Part 2（语法注入）次之**（+3.7pp）——EBNF 规则直接减少语法类编译错误
3. **Part 1（伪代码中间层）贡献最小**（+2.1pp）——可能因为 CoT 效应被其它两部分的部分机制吸收
4. **组合饱和**：Part 2+3 或 1+2+3 都达到 +5.0pp，说明覆盖的错误类型有重叠
5. **代价**：Part 1 增加每 fragment 耗时（baseline 11.7s → pseudo 15.1s → all 16.2s），Part 2/3 几乎无额外开销

**已知限制**

- 单项目（commons-csv）单模型（gpt-4o），样本量不足以达到 p<0.05
- 测试通过率为 0（skip_mock=true，未跑 mock 测试）
- 骨架预存问题（类型映射覆盖不全）在所有组同等存在，未污染对比但压低了绝对通过率

**后续可改进**

1. 扩展到多项目多模型（jansi / commons-cli + deepseek-chat / glm-5.1），增大样本量
2. 跑 mock 测试拿 test_pass 指标
3. Part 1 做 CoT-only ablation（"先分析再翻译" vs "伪代码中间层"）分离 CoT 效应
4. Part 3 升级为 tree-sitter 真实 CFG/DFG + 跨语言预训练模型

---

## Slide 11 — 参考论文速查

| ID | 论文 | 对应 Part |
|---|---|---|
| A1 | Pseudocode-based Code Translation (arXiv 2510.00920) | Part 1 |
| A3 | NL in the Middle (CASCON 2025) | Part 1 设计依据 |
| A6 | Assessing Intermediate Languages (arXiv 2407.05411) | Part 1 ablation 依据 |
| B2 | Grammar Prompting (ACL 2023) | Part 2 |
| B1 | DocCGen (EMNLP 2024) | Part 2 补充 |
| B3 | CodeGRAG (arXiv 2405.02355) | Part 3 |
| B4 | Syntax-Aware RAG (EMNLP 2023 Findings) | Part 3 补充 |

