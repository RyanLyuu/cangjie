# CangjieTypeSkill：面向 Java→Cangjie 仓库级翻译的类型处理方法设计

> 历史方案：本文的约束求解、contract freeze 和 type-impact repair 设计已被新方案取代。当前实现以 `cangjie_type_skill_plan.md` 和 `docs/type_skill_pipeline_report.md` 为准。

## 1. 方法目标

CangjieTypeSkill 面向基于 LLM 的 Java→Cangjie 仓库级代码翻译，目标是解决以下问题：

- Java 类型在不同上下文中可能需要映射为不同的 Cangjie 类型；
- 不同文件、函数和调用点可能独立产生冲突的类型决策；
- LLM 可能生成不存在或不可用的 Cangjie 类型与 API；
- 局部修复可能破坏其他调用点、继承关系或泛型约束；
- 单纯依靠类型指南或编译反馈，难以保证仓库级一致性。

核心思想是：

> 将类型知识、上下文解析、仓库约束、目标骨架和修复影响范围统一为一个可执行的仓库级类型契约系统，并通过 Skill 编排 LLM 与静态分析工具协作。

---

## 2. 方法定位

CangjieTypeSkill 不是单一 Prompt，而是由三部分组成：

```text
Skill 编排层
+ 可执行类型工具
+ 持久化仓库类型契约
```

### 2.1 Skill 编排层

负责规定：

- 何时分析类型；
- 何时检索 Cangjie 文档；
- 何时生成或修改类型契约；
- 哪些签名属于冻结状态；
- 编译错误应如何映射到类型契约；
- 何时执行局部修复，何时执行跨文件修复。

### 2.2 可执行类型工具

负责：

- Java 类型事实提取；
- 类型使用图构建；
- Cangjie 候选类型检索；
- Cangjie 类型探针编译；
- 类型契约检查；
- 调用点与影响范围分析；
- 目标 Skeleton 生成；
- 编译诊断结构化。

### 2.3 持久化状态

负责保存：

- Java 类型使用图；
- 候选类型及证据；
- 仓库级类型契约；
- 冻结签名；
- 类型冲突；
- 契约修改记录；
- 修复历史。

---

## 3. 整体架构

```text
Java Repository
       │
       ▼
Type Semantic Analyzer
       │
       ▼
Java Type-Usage Graph
       │
       ▼
Context-Aware Candidate Resolver
       │
       ▼
候选 Cangjie 类型、证据与置信度
       │
       ▼
Repository Type Contract Planner
       │
       ▼
仓库级类型契约
       │
       ▼
Contract-Constrained Skeleton Generator
       │
       ▼
Cangjie 目标骨架
       │
       ▼
Type-Constrained Translation
       │
       ▼
Contract Checker + Cangjie Compiler
       │
       ├── 成功 ──► 后续功能翻译与验证
       │
       └── 失败 ──► Type-Impact-Guided Repair
```

---

## 4. Type Semantic Analyzer

Type Semantic Analyzer 对应仓库级分析阶段，但输出必须是结构化类型事实，而不是仅生成自然语言报告。

### 4.1 分析对象

需要提取：

- 类、接口、枚举；
- 字段；
- 方法与构造器；
- 参数与返回值；
- 局部变量；
- 泛型参数；
- 类型实参；
- 方法重载；
- 继承与接口实现关系；
- Java 标准库和第三方库类型。

### 4.2 类型语义属性

每个类型出现位置除声明类型外，还应记录：

- 是否可能为 `null`；
- 是否可变；
- 是否有序；
- 是否允许重复元素；
- 是否允许空元素；
- 数值宽度；
- 是否发生自动装箱或拆箱；
- 是否发生数值提升；
- 是否参与显式或隐式转换；
- 是否属于只读包装；
- 是否抛出异常；
- 是否参与重载决议；
- 是否参与 override 或 interface implementation。

示例：

```yaml
occurrence_id: CSVRecord.get.return
symbol: org.apache.commons.csv.CSVRecord.get
role: return_type
declared_type: java.lang.String

semantic_properties:
  nullable: possible
  mutable: false

operations:
  - returned_to_caller
  - compared_with_null

flows_to:
  - CSVParser.value
  - CSVPrinter.print.parameter
```

---

## 5. Java Type-Usage Graph

系统构建 Java Type-Usage Graph，表示类型在仓库中的传播和约束关系。

### 5.1 节点

节点包括：

- 类型声明；
- 字段类型位置；
- 参数类型位置；
- 返回类型位置；
- 局部变量类型位置；
- 泛型参数；
- 方法和构造器；
- 调用点；
- cast 表达式；
- collection element。

### 5.2 边

边包括：

- `assignment`：赋值；
- `argument-to-parameter`：实参到形参；
- `return-to-caller`：返回值到调用方；
- `field-read` / `field-write`：字段读写；
- `override`：方法覆盖；
- `implements`：接口实现；
- `generic-instantiation`：泛型实例化；
- `cast`：类型转换；
- `null-flow`：空值传播；
- `collection-element-flow`：集合元素传播；
- `exception-flow`：异常传播；
- `overload-resolution`：重载选择。

示例：

```text
CSVRecord.get.return
        │ return-to-caller
        ▼
CSVParser.value
        │ argument-to-parameter
        ▼
CSVPrinter.print.parameter
```

该图用于：

- 传播类型决策；
- 发现局部映射冲突；
- 生成目标签名；
- 计算类型修改的影响范围；
- 指导跨文件修复。

---

## 6. Context-Aware Candidate Resolver

Candidate Resolver 根据源类型、代码上下文和 Cangjie API，为每个类型出现位置生成多个候选映射，而不是直接让 LLM 给出唯一答案。

### 6.1 候选来源

候选来自：

```text
Java→Cangjie 规则库
+ Cangjie 官方 API / 标准库检索
+ 项目中已有 Cangjie 用法
+ LLM 上下文推断
```

### 6.2 上下文信息

解析类型时至少提供：

- Java 完整限定类型名；
- Java API 文档；
- 类型所在字段、方法或表达式；
- 该值上的实际操作；
- 调用方与被调用方；
- 可变性和空值分析结果；
- 泛型信息；
- 继承和接口信息；
- 相关测试代码。

### 6.3 结构化输出

```yaml
occurrence: CSVRecord.get.return
source_type: java.lang.String

semantic_properties:
  nullable: possible
  mutable: false

candidates:
  - target_type: Option<String>
    confidence: 0.94
    evidence:
      - source_has_null_return_path
      - callers_check_null
    rules:
      - NULLABLE_RETURN

  - target_type: String
    confidence: 0.31
    evidence:
      - declared_type_is_string
```

LLM 只能提出候选与解释，不能直接覆盖仓库级契约。

---

## 7. Java→Cangjie 类型知识库

知识库使用结构化规则，而不是只保存自然语言建议。

### 7.1 第一层规则类别

#### Nullability

处理：

- Java 引用类型可能返回 `null`；
- nullable 字段；
- `null` 赋值；
- `null` 比较；
- `Optional<T>`；
- 空值在调用链中的传播。

#### Numeric

处理：

- `byte`、`short`、`int`、`long`；
- `float`、`double`；
- `char` 与整数；
- Java 数值提升；
- 显式转换；
- boxed primitive；
- 溢出和截断风险。

#### Collection

处理：

- `List`、`Set`、`Map`；
- 数组；
- 可变与只读集合；
- 顺序；
- 重复元素；
- 索引访问；
- 元素类型；
- nullable element；
- iterator 行为。

#### Generic

处理：

- 泛型参数数量；
- upper/lower bound；
- `? extends T`；
- `? super T`；
- Java 泛型型变与 Cangjie 泛型约束；
- raw type；
- 泛型方法。

#### Signature

处理：

- 参数数量和顺序；
- 参数类型；
- 返回类型；
- receiver；
- varargs；
- overload；
- 构造器；
- override；
- interface implementation。

#### Initialization

处理：

- 字段默认值；
- `static` 初始化；
- 构造器初始化；
- final/let 语义；
- 延迟初始化；
- 初始化顺序。

### 7.2 规则表示

```yaml
rule_id: JAVA_NULLABLE_RETURN

source_pattern:
  role: return_type
  type_category: reference

preconditions:
  nullable_analysis: possible

target_requirement:
  category: optional
  inner_type: inferred

required_adaptations:
  producer:
    - wrap_some_or_none
  consumer:
    - explicit_none_handling

checks:
  - all_call_sites_accept_optional
  - return_paths_match_contract
```

---

## 8. Cangjie Type Probe

LLM 提出的候选类型必须通过 Cangjie Type Probe 验证。

### 8.1 验证内容

验证：

- 类型是否存在；
- import 是否正确；
- 泛型参数数量是否正确；
- 方法是否存在；
- 方法返回值类型是否符合预期；
- 构造方式是否有效；
- 类型是否支持所需操作。

### 8.2 探针示例

```cangjie
import std.collection.*

func __type_probe(x: ArrayList<String>): String {
    x.add("a")
    return x[0]
}
```

候选只有在最小探针通过 `cjc` 或 `cjpm build` 后，才可进入契约求解。

---

## 9. Repository Type Contract

Repository Type Contract 是整个方法的核心。它将局部类型候选转化为仓库级统一决策。

### 9.1 三层契约

#### 语言级规则

描述 Java 与 Cangjie 的通用类型差异。

```yaml
rule: NULLABLE_REFERENCE
source: Java reference type
target: Option<T>
```

#### 项目级决策

描述项目内自定义类型和模块的统一映射。

```yaml
source_type: org.apache.commons.csv.Headers
target_type: Headers
target_module: csv.headers
```

#### 符号级契约

描述具体字段、参数、返回值和方法签名。

```yaml
symbol: org.apache.commons.csv.CSVRecord.get

source_signature:
  parameters:
    - java.lang.String
  return_type: java.lang.String
  nullable_return: possible

target_signature:
  parameters:
    - String
  return_type: Option<String>

constraints:
  frozen_signature: true
  callers_must_handle_none: true
```

优先级：

```text
符号级契约
> 项目级决策
> 语言级规则
> LLM 临时候选
```

---

## 10. 仓库级类型约束

对每个类型出现位置 $o_i$，候选集合记为：

$$
C_i=\{\tau_{i1},\tau_{i2},\ldots\}
$$

系统需要选择：

$$
M(o_i)\in C_i
$$

并满足以下约束。

### 10.1 值表示兼容

源语言可能出现的值必须能由目标类型表示：

$$
ValueCompat(o_i,M(o_i))
$$

例如 Java 返回值可能为 `null`，则普通非空 `String` 不能完整表示源值域。

### 10.2 操作兼容

目标类型必须支持该位置上需要执行的操作：

$$
OperationCompat(o_i,M(o_i))
$$

例如源集合被执行 `add`，则只读集合候选不满足约束。

### 10.3 数据流兼容

值在字段、参数和返回值之间流动时，两端目标类型必须兼容：

$$
FlowCompat(M(o_i),M(o_j))
$$

### 10.4 结构兼容

目标映射必须保持：

- override；
- interface implementation；
- 泛型实例化；
- overload 集合；
- 构造器关系；
- 继承关系。

记为：

$$
StructureCompat(M(o_i),M(o_j))
$$

### 10.5 目标函数

可将映射选择表示为：

$$
\max_M
\sum_i Score(o_i,M(o_i))
-\lambda \cdot ConversionCost(M)
-\mu \cdot Inconsistency(M)
$$

并要求所有类型图边满足对应兼容约束。

第一版可采用：

```text
规则过滤
→ 候选排序
→ 图约束传播
→ 冲突检测
→ LLM 仲裁
→ Cangjie 编译器确认
```

---

## 11. Contract Conflict Resolution

当两个局部合理的映射无法组合时，系统生成结构化冲突。

示例：

```text
A.return = Option<String>
B.parameter = String
A.return → B.parameter
```

输出：

```yaml
conflict_id: CONTRACT-CONFLICT-017

producer:
  symbol: A.return
  type: Option<String>

consumer:
  symbol: B.parameter
  type: String

edge:
  kind: argument-to-parameter

candidate_resolutions:
  - unwrap_or_default_at_call_site
  - explicit_none_branch
  - change_consumer_contract
  - prove_non_null_on_this_path
```

LLM 只能从允许的解决策略中选择，不能直接绕过契约。

---

## 12. Contract-Constrained Skeleton Generator

在翻译函数体之前，根据仓库类型契约生成 Cangjie 目标骨架。

示例：

```cangjie
public class CSVRecord {
    private let values: Array<String>

    public func get(name: String): Option<String> {
        TODO()
    }
}
```

默认冻结：

- 类名；
- 接口名；
- 字段类型；
- 参数类型；
- 返回类型；
- 泛型参数；
- 可见性；
- override / interface 关系；
- module；
- import；
- overload 集合。

Translator 默认只能填充函数体。

---

## 13. Contract Change Request

如果 Translator 认为签名必须修改，不能直接修改代码，而必须提交契约变更请求。

```yaml
symbol: CSVRecord.get
old_type: Option<String>
proposed_type: String
reason:
  diagnostic: TYPE_MISMATCH
  location: CSVParser.cj:142
```

Contract Planner 随后：

1. 查找源 Java 语义；
2. 检查全部调用点；
3. 检查 override 和 interface 关系；
4. 计算受影响范围；
5. 判断应修改调用点还是修改契约；
6. 批准或拒绝变更。

---

## 14. Type-Constrained Translation

Translator 接收：

- 当前 fragment；
- 相关源 Java 代码；
- 目标 Skeleton；
- 相关类型契约；
- 允许使用的 Cangjie API；
- 直接依赖的已冻结签名；
- 禁止修改项。

示例上下文：

```yaml
target_symbol: CSVRecord.get

frozen_signature:
  parameters:
    - String
  return_type: Option<String>

allowed_operations:
  - Some
  - None
  - Array.get

forbidden_changes:
  - parameter_types
  - return_type
  - method_name
```

Translator 只负责在契约范围内实现语义。

---

## 15. Contract-Constrained Editing

由于普通 Agent API 无法执行 token 级类型约束，系统采用 patch 级硬约束。

Agent 提交结构化 patch：

```json
{
  "target_symbol": "CSVRecord.get",
  "body_patch": "...",
  "signature_changes": [],
  "new_imports": []
}
```

提交前检查：

- 是否修改冻结签名；
- 是否引入不存在的类型或成员；
- 实参与形参是否兼容；
- 返回表达式是否满足返回类型；
- `Option` 是否被显式处理；
- 泛型参数是否满足约束；
- override 签名是否一致；
- 改动是否超出允许影响范围。

违反契约的 patch 直接拒绝，不进入仓库。

---

## 16. Contract Checker

Contract Checker 同时执行 AST、LSP 和编译器级检查。

### 16.1 定义检查

检查目标声明是否与契约一致：

- 字段类型；
- 参数类型；
- 返回类型；
- 泛型参数；
- 可见性；
- override；
- interface implementation。

### 16.2 使用点检查

检查：

- 每个调用点的参数；
- 返回值接收类型；
- 字段赋值；
- 集合元素类型；
- 显式转换；
- nullability 处理；
- overload 选择。

### 16.3 仓库一致性检查

检查：

- 同一符号是否存在多个冲突映射；
- Skeleton 和实现是否一致；
- 生产代码和测试代码是否使用同一契约；
- 调用链是否出现未适配的类型变化。

---

## 17. 编译诊断标准化

Cangjie 编译器输出需要转换为结构化诊断。

```yaml
diagnostic_id: TYPE-MISMATCH
location: CSVParser.cj:142

actual_type: Option<String>
expected_type: String

producer_symbol: CSVRecord.get.return
consumer_symbol: CSVPrinter.append.parameter

contract_edge:
  kind: argument-to-parameter
```

结构化诊断用于区分：

- 使用点适配缺失；
- 生产者契约错误；
- 消费者契约错误；
- 泛型传播错误；
- import 或 API 错误；
- Skeleton 与实现不一致。

---

## 18. Type-Impact-Guided Repair

修复不应只针对编译器报告的第一处错误，而应定位类型根因并计算影响闭包。

定义：

$$
Impact(s)=Reachable_{type\text{-}flow}(s)
$$

影响范围包括：

- 类型定义；
- 字段；
- 方法签名；
- 所有调用点；
- override；
- interface implementation；
- 测试代码；
- 序列化和反序列化逻辑。

修复流程：

```text
编译诊断
→ 映射到类型契约节点
→ 定位根因
→ 计算影响范围
→ 生成统一修复计划
→ 批量修改相关位置
→ 重新执行契约检查
→ 重新编译
```

示例：

```text
CSVRecord.get 返回类型变化
→ 5 个调用点
→ 2 个测试
→ 1 个接口声明
```

Repair Agent 一次性接收全部相关上下文，避免逐条修复引发新的不一致。

---

## 19. Skill 接口设计

建议提供以下工具。

### `analyze_repository_types`

输入 Java 仓库，输出类型事实和 Type-Usage Graph。

### `resolve_type_candidates`

输入类型出现位置，输出候选 Cangjie 类型、证据和置信度。

### `validate_cangjie_type`

使用最小探针验证候选类型、import 和 API。

### `solve_repository_contract`

结合候选、规则和类型图生成仓库级类型契约。

### `generate_cangjie_skeleton`

根据契约生成冻结的目标项目骨架。

### `check_type_contract`

检查目标代码是否违反类型契约。

### `request_contract_change`

提交、分析并批准或拒绝类型契约修改。

### `normalize_compiler_diagnostics`

将编译器日志转换为结构化类型诊断。

### `find_affected_symbols`

根据类型图计算受影响定义、调用点和测试。

### `plan_type_repair`

根据根因和影响范围生成统一修复计划。

---

## 20. Skill 目录结构

```text
cangjie-type-skill/
├── SKILL.md
├── schemas/
│   ├── type-occurrence.schema.json
│   ├── type-candidate.schema.json
│   ├── type-contract.schema.json
│   ├── contract-conflict.schema.json
│   └── diagnostic.schema.json
├── knowledge/
│   ├── primitives.yaml
│   ├── nullability.yaml
│   ├── numeric-conversion.yaml
│   ├── arrays.yaml
│   ├── collections.yaml
│   ├── generics.yaml
│   ├── inheritance.yaml
│   ├── overload.yaml
│   ├── initialization.yaml
│   ├── exceptions.yaml
│   └── stdlib-mapping.yaml
├── prompts/
│   ├── contextual-type-resolver.md
│   ├── contract-conflict-arbitrator.md
│   └── type-repair.md
├── tools/
│   ├── analyze_repository_types
│   ├── resolve_type_candidates
│   ├── validate_cangjie_type
│   ├── solve_repository_contract
│   ├── generate_cangjie_skeleton
│   ├── check_type_contract
│   ├── request_contract_change
│   ├── normalize_compiler_diagnostics
│   ├── find_affected_symbols
│   └── plan_type_repair
└── artifacts/
    ├── java-type-usage-graph.json
    ├── type-candidates.json
    ├── type-contract.json
    ├── frozen-signatures.json
    ├── contract-conflicts.json
    ├── diagnostics.jsonl
    ├── repair-history.jsonl
    └── cangjie-skeleton/
```

---

## 21. SKILL.md 核心约束

```text
1. 翻译前必须生成或读取 type-contract.json。
2. 所有公共字段、参数和返回类型必须来自类型契约。
3. Translator 不得直接修改冻结签名。
4. 类型候选必须经过 Cangjie Type Probe 验证。
5. 提交 patch 前必须运行 check_type_contract。
6. 编译错误必须先映射到类型契约节点。
7. 修改类型前必须计算所有受影响调用点。
8. 契约冲突必须通过 request_contract_change 处理。
9. Java 源仓库保持只读。
10. 类型决策必须同时用于生产代码和测试代码。
```

---

## 22. 方法核心

CangjieTypeSkill 的关键不在于增加更多类型说明，而在于建立以下闭环：

```text
局部上下文解析
→ 多候选类型生成
→ Cangjie 探针验证
→ 仓库级约束求解
→ 类型契约固化
→ Skeleton 冻结
→ 契约约束翻译
→ 编译与契约检查
→ 影响范围驱动修复
```

其本质是：

> 将 Java→Cangjie 类型映射从 LLM 的临时判断，转化为一个可查询、可执行、可传播、可修改并可审计的仓库级类型决策系统。
