# x2cangjie 复现 TRAM mock 覆盖率偏低原因分析（jansi）

日期：2026-05-17  
分析对象：`TRAM/` 原始实现、`x2cangjie/` 当前实现、TRAM 论文 PDF、本地 jansi 产物。

## 结论摘要

以 jansi 为例，覆盖率低不只是“还没引入 EvoSuite”造成的。EvoSuite 是最大、最直接的覆盖来源差异，但当前 x2cangjie 还有几类独立因素会继续压低 mock 可覆盖率和可通过率：

1. `/tmp/cangjie_mock/jansi` 现在已经生成，但规模很小：只有 21 个 `_test.cj` / 21 个 workflow，覆盖 7 个 unique focal `class.method`。
2. 这 7 个 focal 中，按当前 jansi schema 的 normal main non-constructor 方法口径，只有 2 个能直接匹配到非重载方法；有效覆盖约为 2/301 = 0.66%。
3. 大量生成测试集中在 `Ansi.ansi`、`AnsiRenderer.render`、`Ansi.cursorDownLine`、`Ansi.cursorUpLine` 这类重载方法，而当前统计/翻译逻辑会跳过 `is_overload` 方法。
4. 构造器 focal 注释为 `org.fusesource.jansi.io.AnsiOutputStream.<init>`，但 `test_runner.py` 当前正则会把它误解析成 `class=io, method=AnsiOutputStream`，导致构造器测试无法匹配。
5. x2cangjie 的 mock 日志解析策略每个 Java 测试日志通常只生成 1 个 workflow；TRAM 原版会对日志中的每个 `START OF` 方法调用都生成一个 focal workflow，天然覆盖更多方法调用。
6. x2cangjie 的 `build_mock_corpus.sh` 从 `projects/java/original_projects/<project>` 扫描原始开发者测试；TRAM 论文结果使用 `cleaned_final_projects_evosuite` / `evosuite_cleaned`，并通过 `executed_tests` JSON 驱动可执行测试集合。
7. Cangjie 目标端 mock 能力弱于 Python：对象构造、private/protected/let 字段、静态字段、副作用回放、泛型约束、inner class 重命名都会让同样的日志无法稳定变成可编译的 Cangjie 测试。
8. x2cangjie 当前 validation/result 口径和 TRAM 论文口径不同：TRAM 统计 `mocking_validation` 的 MS/MF/NM；x2cangjie 主要把 Cangjie mock 执行结果写入 `test_execution`，且本地 jansi schema 仍是 pending 状态，不能直接对齐论文表格。

优先级判断：当前应先修 mock corpus 的有效匹配率（构造器正则、重载方法口径、workflow 粒度），再补 EvoSuite。否则即使引入 EvoSuite，也会因为“生成很多但匹配不上/被统计跳过”而达不到 TRAM 论文水平。

## 论文中的 jansi 基准

TRAM Table 1 中 jansi 的关键数字：

| 指标 | jansi |
|---|---:|
| AMF | 409 |
| Syntax Check | 96.58% |
| Mocking: NM（无 mock tests） | 47.68% |
| Mocking: MS（mock success） | 31.05% |
| Mocking: MF（mock fail） | 21.27% |
| Test Translation: NT | 97.56% |
| Test Translation: ATP | 0.00% |

解释：

- 论文里 jansi 的 mock success 本来就不是很高，只有 31.05%，且 47.68% AMF 没有 mock tests。
- jansi 的 ATP 是 0.00%，说明 TRAM 在 jansi 上主要靠 mock-based in-isolation validation，而不是完整翻译测试通过。
- 论文总计显示 TRAM 可验证 69.98% AMF，MS 总体 43.10%；但 jansi 明显低于总体均值，是比较难的项目。

本地 TRAM 执行清单对 jansi 的测试来源规模：

| 来源 | 测试类数 | 测试方法数 |
|---|---:|---:|
| developer tests (`executed_tests`) | 7 | 35 |
| EvoSuite (`evosuite_executed_tests`) | 10 | 330 |
| EvoSuite plus (`evosuite_plus_executed_tests`) | 21 | 413 |

这说明如果 x2cangjie 只用原始开发者测试，测试入口数量和 TRAM 论文设置至少差一个数量级。

## 本地 x2cangjie 的 jansi 状态

更新后的本地可见状态：

- `/tmp/cangjie_mock/jansi` 已存在。
- 生成 `_test.cj`: 21 个。
- 生成 `.workflow.json`: 21 个。
- 所有 `_test.cj` 都有 `// focal call:` 注释。
- unique focal `class.method`: 7 个。
- workflow size: min 0, max 4, avg 1.86；其中 3 个 workflow 是空列表。
- `x2cangjie/data/java/schemas_decomposed_tests/deepseek-chat/0.0/jansi/` 目录为空。
- `x2cangjie/jansi_deepseek_body.log` 只有 run header，没有实际 fragment 处理记录。
- `x2cangjie/data/java/schemas/gpt-4o-2024-11-20/0.0/jansi/` 有 32 个 schema 文件，但所有统计仍为 pending：
  - main methods: 314
  - test methods: 39
  - fields: 362
  - normal non-constructor main methods: 301
  - `translation_status`: 全部 `pending`
  - `test_execution`: 全部 `pending`

当前 mock corpus 的 focal 分布：

| focal | 测试数 | 当前 schema/runner 风险 |
|---|---:|---|
| `Ansi.ansi` | 10 | schema 中 `ansi` 全部是 `is_overload=true`，统计/翻译会跳过 |
| `AnsiRenderer.render` | 4 | schema 中 `render` 全部是 `is_overload=true`，统计/翻译会跳过 |
| `Ansi.setEnabled` | 2 | 可匹配到 normal main method |
| `AnsiOutputStream.<init>` | 2 | runner 正则会误解析为 `io.AnsiOutputStream` |
| `Ansi.cursorUpLine` | 1 | schema 中是重载方法 |
| `Ansi.cursorDownLine` | 1 | schema 中是重载方法 |
| `AnsiRenderer.test` | 1 | 可匹配到 normal main method |

按当前 schema 口径，jansi 有 301 个 normal main non-constructor 方法；上述 corpus 只有 `Ansi.setEnabled` 和 `AnsiRenderer.test` 两个 focal 能直接匹配，约 0.66%。这解释了为什么即使 tmp mock 文件已经生成，覆盖率仍会显著低于 TRAM 论文水平。

因此，当前仓库里的 jansi 仍没有形成可直接复算论文 Table 1 的完整结果文件；但 tmp corpus 已经足以证明低覆盖的主要瓶颈从“没有 mock corpus”转移到了“corpus 有效 focal 覆盖与 schema/runner 匹配率太低”。

## 实现差异与影响

### 1. 测试来源：EvoSuite 缺失是最大差异，但不是唯一差异

TRAM 的 `scripts/generate_mock_tests.sh` 调用：

- `src/isolated_validation/generate_logs.py "$PROJECT" 400 executed_tests True`
- 输入包含 `java_projects/cleaned_final_projects_evosuite/<project>`
- 生成并保存到 `data/mock_tests/<project>`

x2cangjie 的 `scripts/java/build_mock_corpus.sh` 当前：

- 输入是 `projects/java/original_projects/<project>`
- 用 `find src/test/java -name '*Test.java' -o -name '*Tests.java'` 扫描原始测试
- 用 grep 提取 `@Test` 后面的 `void` 方法
- 输出到 `/tmp/cangjie_mock/<project>`

影响：

- 没有 EvoSuite 时，jansi 从 TRAM 可见的 330/413 个 EvoSuite 测试入口退化到原始开发者测试规模。
- 即使原始测试存在，grep 方式也可能漏掉非标准布局、继承测试、参数化测试、`@Test` 与方法签名间隔多行的测试。
- TRAM 先抽取已执行测试 JSON，再驱动逐个方法执行；x2cangjie 直接静态扫描，测试发现口径更弱。

### 2. workflow 粒度：x2cangjie 每个日志生成太少 focal cases

TRAM 原版 `TRAM/src/isolated_validation/log_parser.py` 的 `parse_logs` 会遍历日志中所有 `==========START OF` 块，对每个方法调用都调用 `retrieve_mocking_info_for_one_method`，生成多个 mock workflows。

x2cangjie 的 `x2cangjie/src/java/isolation_validation/log_parser.py` 明确写着：“一个日志文件（= 一个 @Test）只生成一个 workflow”：

- 若有嵌套调用，只选“嵌套调用数最多”的 depth-0 方法作为 focal。
- 若没有嵌套调用，把所有 depth-0 方法合并进一个 workflow。

影响：

- 同一个 Java 测试里多个被覆盖方法，在 TRAM 中可能分别成为 focal method；在 x2cangjie 中通常只留下一个。
- 这会直接降低“有 matching `_test.cj` 的方法数”，即降低 NM/MS/MF 中的可覆盖分母。
- 这个问题与 EvoSuite 独立存在：引入更多测试后，如果每个测试仍只产一个 workflow，覆盖率仍会被压缩。

这次 `/tmp/cangjie_mock/jansi` 的实测结果支持该判断：21 个测试文件只覆盖 7 个 unique focal，且集中在少数 API 上。TRAM 的 developer-test 执行清单里 jansi 有 35 个测试方法；在 TRAM 原版 parser 下，一个测试日志可以拆出多个 focal workflow，而当前 x2cangjie 版本通常只保留一个。

### 3. mock 匹配方式更脆弱

x2cangjie 的 `test_runner.py` 用 `_FOCAL_RE = r"//\s*focal call:\s*[\w.$]+\.(\w+)\.(\w+)"` 从 `_test.cj` 注释中抽取 simple class/method，再和 fragment 的 simple name 匹配。

风险点：

- jansi 里有大量 inner classes，例如 `Ansi$Attribute_ESTest`、`Ansi$Color_ESTest`、`AnsiRenderer$Code_ESTest`。
- x2cangjie 预处理会把内部类重命名为 `Outer_Inner`，但日志、Java 类名、Cangjie 文件名、schema key 之间未必完全一致。
- 构造器、重载、静态方法、被关键字改名的方法都可能匹配失败。

TRAM Python 端是按生成文件名后缀匹配 `_Class_method.py` / `$Class_method.py`，并且 mock_helper 里有专门处理 private/protected、constructor、inner class patch 名称的逻辑。x2cangjie 当前匹配链路更短，但也更容易漏。

本次 tmp 结果中有一个明确 bug：`// focal call: org.fusesource.jansi.io.AnsiOutputStream.<init>` 会被当前正则错误匹配为 `class=io, method=AnsiOutputStream`，而不是 `class=AnsiOutputStream, method=<init>`。这会让 2 个构造器测试完全无法被 `find_matching_tests` 找到。需要把 focal 解析改成基于右侧 token 的结构化解析，并显式支持 `<init>`。

另一个明确问题是重载口径：生成的 focal 里 `Ansi.ansi`、`AnsiRenderer.render`、`cursorUpLine`、`cursorDownLine` 在 schema 中都是 `is_overload=true`，但现有统计脚本和部分流程会跳过 overload。结果是“文件存在，但覆盖统计不认”。

### 4. Cangjie mock 框架能力与 Python mock 不等价

TRAM 论文依赖 Python `unittest.mock`，其优势包括：

- 可以 patch 任意模块路径下的函数/方法。
- 可以用 `object.__new__` 绕开构造器创建对象。
- 可以动态写入字段和 monkey patch 行为。
- 对 private/protected 名称、构造器、异常、side effect 都能在 Python 层模拟。

x2cangjie 为了达到类似效果增加了多套补丁：

- `change_mode.py` 把 private/protected 字段改成 public var，处理部分零参构造器。
- `side_effect.py` 通过扫描 Cangjie 源码，在 callee 调用语句后插入 side-effect stub。
- `mock_helper.py` 手工把 Java JSON snapshot 转成 Cangjie 对象/集合/断言代码。

这些都是 best-effort，不是语言原生动态能力。主要限制：

- Cangjie 没有 Python 式空壳实例构造，很多对象必须显式构造并初始化全部字段。
- `let`、private/protected、构造器参数、静态字段和泛型约束会阻止 snapshot 复原。
- `HashMap` / `HashSet` key 需要 `Hashable & Equatable`，`Any` 不能像 Python `object` 那样兜底。
- 对多行调用、重载调用、同名短方法调用，`side_effect.py` 的短名匹配可能插错或漏插。

所以即便测试数量对齐，Cangjie mock 的“可编译率”和“可执行率”也会低于 Python mock。

### 5. validation 主循环和论文口径不一致

TRAM 原版 `compositional_translation_validation.py` 同时维护：

- `syntactic_validation`
- `field_exercise`
- `graal_validation`
- `mocking_validation`
- `test_execution`

论文 Table 1 的 MS/MF/NM 来自 `mocking_validation`。

x2cangjie 当前主循环主要维护：

- `cangjie_compilation`
- `test_execution`

mock 测试由 `run_mock_tests_for_fragment` 执行，结果写入 `test_execution`：

- 无匹配测试：`not-exercised`
- mock 通过：`{"outcome": "success", ...}`
- mock 失败：`{"outcome": "failure", ...}`

影响：

- 不能直接拿 x2cangjie 的 `test_execution` 数字与论文的 `mocking_validation` 表格逐项比较。
- 如果本地没有 `/tmp/cangjie_mock/<project>`，`run_mock_tests_for_fragment` 会返回 `no-tests`，最终大量方法是 `not-exercised`。
- 论文的 NM/MS/MF 是“mock 测试覆盖和结果”的口径；x2cangjie 还需要补一个 `print_results` 等价统计脚本，区分 no-tests、compile harness failure、assertion failure、translation failure。

### 6. jansi 项目自身放大了这些问题

jansi 特点：

- 依赖 terminal、ANSI escape、native loader、OS/arch 判断、Windows/Linux 分支。
- 有多个内部类和枚举类。
- 包含 native resources 和环境相关行为。
- EvoSuite 对这类项目会生成大量边界测试，但也可能包含环境假设。

这些特点让 Java 日志 snapshot 更复杂，也让 Cangjie 端复原更困难。TRAM 论文里 jansi 的 NM 已经高达 47.68%，说明即使在 Java-to-Python 场景中，jansi 也不是容易覆盖的项目。

## 回答你的问题：除了 EvoSuite，还有哪些因素？

有，而且至少有以下高影响因素：

1. mock corpus 虽已构建，但有效覆盖极低：21 个测试只覆盖 7 个 focal，其中按当前 schema 可直接计入的只有 2 个 normal main method。
2. 构造器 focal 解析错误：`<init>` 会被 runner 正则误解析，导致 `AnsiOutputStream.<init>` 测试无法匹配。
3. 重载方法被跳过：当前生成测试主要落在重载方法上，而 schema 统计和翻译流程会跳过 `is_overload`。
4. x2cangjie log parser 降低 workflow 数量：每个日志只产一个 workflow，会系统性减少 focal method 覆盖。
5. Cangjie mock 生成器和 runner 仍是 best-effort：对象构造、字段访问、side effect 插桩和泛型约束都会让测试生成失败或执行失败。
6. inner class / name conflict / keyword rename 可能导致 focal 匹配失败，jansi 尤其明显。
7. 原始测试发现方式弱于 TRAM 的 executed-tests JSON 驱动，可能漏测或跳过 Maven 失败的测试。
8. 统计口径未对齐：现在的 x2cangjie 结果不能直接等价成 TRAM 的 MS/NM/MF。
9. 类型映射和 RAG 质量差异：TRAM 论文的提升还包括 context-aware type resolution；Cangjie 端类型映射需要满足更强静态约束，失败会传导到 mock 测试可编译性。

## 建议的修复优先级

1. 先修 `test_runner.py` 的 focal 解析，显式支持 `<init>`，避免把 `org.fusesource.jansi.io.AnsiOutputStream.<init>` 解析成 `io.AnsiOutputStream`。
2. 明确 overload 策略：要么在 schema/traversal 中保留可区分签名的 overload focal，要么在 mock corpus 统计时不要把这些测试算作有效覆盖。
3. 修改 x2cangjie `log_parser.py`，恢复 TRAM “每个 START OF 调用生成一个 focal workflow”的策略；可以先保留当前策略为 fallback。
4. 复现 TRAM 的测试输入规模：把 EvoSuite 项目接入 x2cangjie 的 mock corpus 构建，至少生成 jansi 的 developer、evosuite、evosuite_plus 三类执行清单。
5. 固化 mock corpus 到仓库数据目录，例如 `data/java/mock_tests/<project>`，不要依赖 `/tmp/cangjie_mock/<project>` 这种易丢状态。
6. 增加 x2cangjie 版 `print_results`：按 TRAM Table 1 口径输出 AMF、NM、MS、MF、NT、ATP，并额外拆分 Cangjie harness compile failure、focal unmatched、overload skipped、constructor parse failed。
7. 专门处理 jansi inner classes：统一 Java `$`、schema `Outer_Inner`、Cangjie 文件名、focal 注释的命名映射。
8. 强化 Cangjie mock helper：优先补集合、字符串/字节流、异常、静态字段、构造器和 private/protected 字段这几类在 jansi 中高频出现的 snapshot。
9. 对 side-effect 插桩做更稳的 AST/结构化匹配，避免当前短方法名正则匹配带来的误插和漏插。

## 可复查的本地证据

- 论文 PDF：`Ke 等 - 2025 - Advancing Automated In-Isolation Validation in Repository-Level Code Translation.pdf`
- TRAM README：`TRAM/README.md`
- TRAM mock 生成入口：`TRAM/scripts/generate_mock_tests.sh`
- TRAM log parser：`TRAM/src/isolated_validation/log_parser.py`
- TRAM mock validator：`TRAM/src/mocking/validate_by_mocking.py`
- TRAM 结果统计：`TRAM/src/postprocessing/print_results.py`
- TRAM jansi executed tests：
  - `TRAM/src/isolated_validation/executed_tests/jansi.json`
  - `TRAM/src/isolated_validation/evosuite_executed_tests/jansi.json`
  - `TRAM/src/isolated_validation/evosuite_plus_executed_tests/jansi.json`
- x2cangjie mock corpus 构建：`x2cangjie/scripts/java/build_mock_corpus.sh`
- x2cangjie 当前 jansi mock corpus：`/tmp/cangjie_mock/jansi`
- x2cangjie Cangjie mock runner：`x2cangjie/src/java/isolation_validation/test_runner.py`
- x2cangjie log parser：`x2cangjie/src/java/isolation_validation/log_parser.py`
- x2cangjie validation 主循环：`x2cangjie/src/java/translation/compositional_translation_validation.py`
- x2cangjie jansi schema：`x2cangjie/data/java/schemas/gpt-4o-2024-11-20/0.0/jansi/`
