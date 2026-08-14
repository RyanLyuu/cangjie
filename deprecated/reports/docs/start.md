# x2cangjie 项目预处理与翻译流程指南

x2cangjie 是一个将 Java 代码翻译为 Cangjie 的工具链，基于 TRAM 架构但采用 Java→Cangjie 翻译模式。

## 核心特点

**增量翻译验证**：翻译过程中逐步替换骨架文件中的 `throw Exception('TODO')` 占位符，每翻译一个片段即进行编译验证，确保代码正确性。

**与 cangjie 的主要区别**：使用 tree-sitter 直接解析 Java AST 生成 Schema，而非 CodeQL。

## 环境要求

- Python 3.8+
- Java 17+
- tree-sitter-java
- Cangjie SDK (cjc, cjpm)
- LLM API 配置 (configs/model_configs.yaml)

## 初始数据准备

> 参考 TRAM 环境配置，详情见 TRAM/Dockerfile

### 1. tree-sitter 语法文件

```bash
mkdir -p misc/sitter-libs
git clone https://github.com/tree-sitter/tree-sitter-java.git misc/sitter-libs/java
cd misc/sitter-libs/java && git checkout v0.23.5
git clone https://github.com/tree-sitter/tree-sitter-python.git misc/sitter-libs/python
cd misc/sitter-libs/python && git checkout v0.23.5
```

### 2. JavaCallgraph

```bash
mkdir -p misc/java-callgraph
git clone https://github.com/gousiosg/java-callgraph.git misc/java-callgraph
cd misc/java-callgraph && mvn clean install -DskipTests
```

### 3. 类型映射文件

```bash
mkdir -p data/java/type_resolution
# 使用 cangjie 项目中已有的类型映射，或参考 cangjie 创建
```

## 基于 `_evosuite_cleaned_base` 从 2.3 开始运行

本流程适用于已经完成 Java 侧预处理、Schema 生成和依赖顺序生成的 EvoSuite clean base：

```text
projects/java/cleaned_final_projects_evosuite_cleaned_base/<project>
data/java/schemas_evosuite_cleaned_base/<model>/<temperature>/<project>
data/java/dependencies_evosuite_cleaned_base/<project>/traversal.json
```

对应 suffix 固定为：

```text
_evosuite_cleaned_base
```

### 前置检查

```bash
project=<project>
model=<model_name>
temperature=<temperature>
suffix=_evosuite_cleaned_base

base="projects/java/cleaned_final_projects${suffix}/${project}"
test -d "$base/target/classes"
test -d "data/java/schemas${suffix}/${model}/${temperature}/${project}"
test -f "data/java/dependencies${suffix}/${project}/traversal.json"
```

### 1. 类型翻译

首次使用 RAG 时先准备索引：

```bash
bash scripts/java/crawl_java_base.sh
export OPENAI_API_KEY=""
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
python -m src.java.rag.indexer
```

执行类型翻译：

```bash
bash scripts/java/translate_types.sh <project> <model_name> <temperature> _evosuite_cleaned_base
```

### 2. 生成骨架结构

```bash
bash scripts/java/create_skeleton.sh <project> <model_name> _evosuite_cleaned_base <temperature>
```

### 3. 构建 mock 测试语料

```bash
bash scripts/java/build_mock_corpus.sh <project>
```

脚本会优先读取：

```text
projects/java/cleaned_final_projects_evosuite_cleaned_base/<project>
```

生成文件位于：

```text
/tmp/cangjie_mock/<project>/
```

### 4. 执行片段翻译

```bash
bash scripts/java/translate_fragment.sh <project> <model_name> _evosuite_cleaned_base <temperature> true false
```

参数含义：

- `true`：启用 RAG。
- `false`：不跳过 mock 测试。若只想跑编译验证，可把最后一个参数改为 `true`。

主要输出：

```text
data/java/schemas_evosuite_cleaned_base/translations/<model>/<temperature>/<project>/
data/java/skeletons/<project>/src/
```

---

## 阶段一：项目预处理

> 阶段一复用 TRAM 的预处理流程。详细步骤参考 TRAM/README.md。

### 1.0 下载原始 Java 项目

```bash
bash scripts/java/download_original_projects.sh
```

- **作用：** 从 GitHub 下载 10 个 Apache Commons 系列 Java 项目。
- **生成文件：** `projects/java/original_projects/` 目录。
- **包含项目：** commons-cli, commons-codec, commons-csv, commons-exec, JavaFastPFOR, commons-fileupload, commons-graph, jansi, commons-pool, commons-validator

### 1.1 构建并验证 Java 项目

```bash
bash scripts/java/build_original_projects.sh
```

- **作用：** 在 `cleaned_final_projects_decomposed_tests` 目录下构建并测试所有项目。
- **依赖：** 需要 Java 8 环境和 Maven。
- **注意：** 仅验证项目能正常编译测试，不进行翻译。

### 1.2 添加 JAR 插件

**命令：**

```bash
bash scripts/java/add_plugin.sh <project>
```

- **作用：** 将 `<project>-jar-plugin` 添加到项目的 `pom.xml`，用于生成测试 JAR。
- **生成文件：** `projects/java/automated_reduced_projects/<project>/` 目录（从 `original_projects` 复制并添加插件）。

---

### 1.3 处理 Cangjie 关键字冲突

**命令：**

```bash
bash scripts/java/handle_keyword_conflicts.sh <project>
```

- **作用：** 处理 Java 代码中与 Cangjie 关键字冲突的标识符。
- **输入：** `projects/java/automated_reduced_projects/<project>/`
- **输出：** `projects/java/keyword_handled/<project>/` (新建目录，非原地修改)
- **处理规则：** 将 Cangjie 关键字（如 `type`、`init`、`in`）作为标识符时添加 `__` 或 `_` 后缀
- **Python 脚本：** `src/java/preprocessing/handle_keyword_conflicts.py`

---

### 1.3.2 处理 Cangjie 展平后的命名冲突与 shadow 冲突

**命令：**

```bash
bash scripts/java/handle_name_conflicts.sh <project>
```

- **作用：** 处理 Cangjie 不支持嵌套类、为避免包循环而展平 Java 子包后带来的同名类冲突，以及 Java 继承/作用域 shadow 在 Cangjie schema/skeleton 中造成的名字污染。
- **输入：** `projects/java/keyword_handled/<project>/`
- **输出：** `projects/java/name_handled/<project>/` (新建目录，非原地修改)
- **重命名策略：**
  - 定义文件中的裸引用 (`InnerClass` → `OuterClass_InnerClass`)
  - 跨文件的限定引用 (`OuterClass.InnerClass` → `OuterClass.NewName`)
  - 通过继承访问的子类中的裸引用（解析 `extends`/`implements` 关系）
  - 被展平到同一 Cangjie 包的子包同名顶级类 (`sub/package/Foo` → `sub_package_Foo`)
  - 子包展平采用最小必要展平：父子包被合并到根包时，孙子包仍可保留为根包下的子包
  - 继承 shadow 冲突：子类字段与祖先字段同名时改名为 `<name>_field`；方法/构造器参数与当前类或祖先字段同名时改名为 `<name>_param`
  - shadow 改名会同步更新当前类作用域内的声明、裸引用和 `this.<field>` 引用，避免后续 schema 把变量、字段和类型名混在一起
- **Python 脚本：** `src/java/preprocessing/handle_name_conflicts.py`

---

### 1.4 构建项目并合并 JAR

**命令：**

```bash
bash scripts/java/merge_jar.sh <project>
```

- **作用：** 执行 `mvn clean install` 构建项目，将主代码和测试代码合并成单个 JAR。
- **依赖：** 需要 Java 和 Maven 环境。
- **输入：** `projects/java/name_handled/<project>/`
- **生成文件：**
  - `projects/java/name_handled/<project>/target/*.jar` (主 JAR)
  - `projects/java/name_handled/<project>/target/*-tests.jar` (测试 JAR)
  - `projects/java/name_handled/<project>/target/*-merged.jar` (合并后的 JAR)

---

### 1.5 生成调用图

**命令：**

```bash
bash scripts/java/generate_cg.sh <project>
```

- **作用：** 使用 `JavaCallgraph` 工具生成项目的调用图。
- **依赖：** `misc/java-callgraph/target/javacg-0.1-SNAPSHOT-static.jar`
- **生成文件：** `projects/java/name_handled/<project>/callgraph.txt`

---

### 1.6 缩减第三方依赖

**命令：**

```bash
bash scripts/java/reduce_third_party_libs.sh <project>
rm -rf projects/java/cleaned_final_projects/<project>
mkdir -p projects/java/cleaned_final_projects
cp -r projects/java/name_handled/<project> projects/java/cleaned_final_projects/<project>
```

- **作用：** 分析调用图，移除未使用的第三方依赖，只保留项目自身的代码。
- **输入：** `callgraph.txt` 和 `name_handled/` 项目。
- **生成文件：** `projects/java/cleaned_final_projects/<project>/` (清理后的项目)。
- **Python 脚本：** `src/java/preprocessing/reduce_third_party_libs.py`

## 阶段二：Schema 生成与翻译

### 2.1 创建项目 Schema

> x2cangjie 使用 tree-sitter 直接解析 Java AST，而非 CodeQL。

**命令：**

```bash
bash scripts/java/create_schema.sh <project> <model_name> <temperature> <suffix>
```

- **作用：** 使用 tree-sitter 解析 Java AST，生成项目结构 schema（JSON 格式）。
- **参数：**
  - `<project>` - 项目名
  - `<model_name>` - 模型名（如 `gpt-4o-2024-11-20`）
  - `<temperature>` - 采样温度
  - `<suffix>` - 后缀，如 `_decomposed_tests`（可为空）
- **生成文件：** `data/java/schemas<suffix>/<model_name>/<temperature>/<project>/`
- **Python 脚本：** `src/java/decomposition/create_schema.py`

**输出格式**

Schema 文件为 JSON 格式，包含：

- `classes`: 类信息（方法、字段、继承关系）
- `cangjie_imports`: Cangjie 导入语句
- Schema key 格式：`{start}-{end}:{classname}`（TRAM 格式）

---

### 2.2 生成翻译顺序

**命令：**

```bash
python src/java/utils/parse_dependencies.py --project_name=<project> --function=parse_dependencies --suffix=<suffix>
```

- **作用：** 使用 `jdeps` 分析 Java 依赖关系，生成 `traversal.json` 文件
- **输入：** 编译后的项目（`projects/java/cleaned_final_projects{suffix}/{project}/target/classes`）
- **生成文件：** `data/java/dependencies{suffix}/{project}/traversal.json`
- **Python 脚本：** `src/java/utils/parse_dependencies.py`

**traversal.json 格式：**

```json
{
  "0": "Animal",
  "1": "Dog",
  "2": "Main"
}
```

**用途：** 翻译时按此顺序处理类，确保被依赖的类先翻译。

**前提条件：** 项目必须已完成预处理、JAR 合并和调用图生成（阶段一 1.4-1.6）。

---

### 2.3 类型翻译

> 使用 RAG 知识库进行 Java 到 Cangjie 的类型映射。

**第一步：爬取 Java 类型文档（首次设置）**

```bash
bash scripts/java/crawl_java_base.sh
```

- **作用：** 从 Oracle Java 文档爬取 java.base 模块的类型描述信息。
- **生成文件：** `data/java/crawl/java.base_module_doc.json`
- **Python 脚本：** `src/java/crawler/crawl_java_package.py`

**第二步：构建 RAG 知识库索引（首次使用）**

```bash
export OPENAI_API_KEY=""
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
python -m src.java.rag.indexer
```

- **作用：** 扫描 `misc/CangjieCorpus` 目录，对 Cangjie 文档进行分块、向量化（text-embedding-3-large），构建 ChromaDB 向量索引和 BM25 稀疏索引。
- **依赖：** OpenAI API key（或 OpenRouter），约处理 20,000+ 文档块
- **生成文件：**
  - `data/java/rag/chromadb/` — ChromaDB 向量存储
  - `data/java/rag/bm25_index.pkl` — BM25 索引
  - `data/java/rag/chunks.json` — 文档块元数据（检查用）

**第三步：执行类型翻译**

```bash
bash scripts/java/translate_types.sh <project> <model_name> <temperature> <suffix>
```

- **作用：** 使用确定性类型表、`import_map`、Progressive KB 缓存和 interface shim 解析 Java 类型，构建类型映射。
- **说明：** 类型解析阶段不再调用 LLM/RAG；复杂泛型未命中确定性规则时会记录原因并降级到静态 fallback。
- **Python 脚本：** `src/java/type_resolution/translate_type_rag.py`

---

### 2.4 生成骨架结构

**命令：**

```bash
bash scripts/java/create_skeleton.sh <project> <model> <suffix> <temperature>
```

- **作用：** 在 `data/java/skeletons/<project_name>` 下创建 Cangjie 骨架文件。
- **骨架内容：** 包含类/方法签名的空实现，使用 `throw Exception('TODO')` 占位。
- **运行时支持：** 如果骨架中出现 `AnyHashable`（例如 `HashMap<Object, V>` 被映射为 `HashMap<AnyHashable, V>`），脚本会自动把 `AnyHashable.cj` 渲染并注入到 `data/java/skeletons/<project>/src/runtime/AnyHashable.cj` 和 translations skeleton 的同名位置；包名按 `cjpm.toml` 的 `name` 生成为 `<project>.runtime`，引用形式为 `import <project>.runtime.AnyHashable`。
- **参数说明：**
  - `<project>` - 项目名
  - `<model>` - 模型名（如 `gpt-4o-2024-11-20`）
  - `<suffix>` - 后缀
  - `<temperature>` - 采样温度
- **Python 脚本：** `src/java/translation/create_skeleton.py`

---

### 2.4.5 构建 mock 测试语料（前置）

**命令：**

```bash
bash scripts/java/build_mock_corpus.sh <project>
```

- **作用：** 把 Java 项目改造为可生成方法级日志的工作副本，对所有 `*Test.java` / `*Tests.java` 中的 `@Test` 方法逐个 `mvn -Dtest=<FQCN>#<method>` 执行，把日志解析成 `_test.cj` + `.workflow.json` emit 到 `/tmp/cangjie_mock/<project>/`。
- **耗时：** 与项目测试方法数成正比，可能需要数分钟到数十分钟。
- **前置：** Java 项目位于 `projects/java/original_projects/<project>/` 且能用 `mvn` 构建。
- **生成文件：** `/tmp/cangjie_mock/<project>/<stem>_test.cj` 与同名 `.workflow.json`（`stem` 即 Java 测试方法名，可能含 numbered suffix）。

> ⚠️ §2.5 的 `translate_fragment.sh` 启动时若发现 `/tmp/cangjie_mock/<project>/` 不存在会直接报错。必须先跑本步骤。

---

### 2.5 执行翻译（增量翻译验证 + mock 测试）

**命令：**

```bash
bash scripts/java/translate_fragment.sh <project> <model> <suffix> <temperature>
```

- **作用：** 调用 LLM 翻译代码片段，按依赖顺序执行，每翻译一个片段即更新骨架、验证编译，并对普通方法自动跑 mock 测试。
- **参数：**
  - `<project>` - 项目名
  - `<model>` - 模型名（如 `gpt-4o-2024-11-20`）
  - `<temperature>` - 采样温度
- **RAG 注入：** 翻译时自动检索 CangjieCorpus 中相关的 API 文档和语法参考，注入到 LLM Prompt 中；编译失败时自动检索错误修复文档上下文（`--use_rag` 默认启用）。
- **Python 脚本：** `src/java/translation/compositional_translation_validation.py`

### 翻译流程

1. **会话级初始化**：自动创建 `data/java/skeletons/<project>/src/runtime/`，把 `helper.cj` 与 `simple_ioc.cj` 注入其中（包名渲染为 `<project>.runtime`）；翻译会话结束（含异常）时自动清理这两个文件。
2. **按依赖顺序获取片段**：使用反向调用图确定翻译顺序
3. **RAG 检索**：从 CangjieCorpus 检索当前代码片段相关的文档上下文
4. **生成 Prompt**：注入 RAG 上下文 + Cangjie ICL 示例（来自 configs/prompt_templates.yaml）
5. **调用 LLM**：获取翻译结果
6. **提取代码**：从 markdown 代码块中提取 Cangjie 代码
7. **编译验证**：使用 `cjpm build` 验证代码正确性；如果翻译结果首次引入 `AnyHashable`，编译验证会按当前 skeleton 的 `cjpm.toml` 包名自动补齐 `src/runtime/AnyHashable.cj` 和对应 import。
8. **Mock 测试验证**：仅对**普通方法**（非 test 方法、非 constructor、非 field/static_initializer）触发：
   - 在 `/tmp/cangjie_mock/<project>/` 中按 `// focal call:` 注释匹配 simple class+method，找出该 fragment 对应的 `_test.cj`。
   - `change_mode apply` → 拷贝匹配测试到 `<skeleton>/src/test/` → `side_effect.instrument` → `cjpm test` → `side_effect.deinstrument` → `change_mode restore`。
   - 没有匹配测试时跳过（`test_execution: not-exercised`）。
9. **更新骨架**：验证通过后，替换骨架中的 `throw Exception('TODO')`
10. **递归重试**：编译失败和 mock 测试失败**共享 4 次预算**（普通方法）；失败时把上一次输出（mock 失败时取 `cjpm test` 末尾 50 行）注入下一轮 prompt 作为 feedback。预算耗尽后即定格。

### 生成文件

- 翻译结果 JSON：`data/java/schemas_decomposed_tests/translations/<model>/<temperature>/<project>/`
- 骨架文件：`data/java/skeletons/<project>/src/` (增量更新)
- 运行时目录：`data/java/skeletons/<project>/src/runtime/`
  - `helper.cj` / `simple_ioc.cj`：mock 翻译会话期间自动注入，测试通过 `import <project>.runtime.*` 使用
  - `AnyHashable.cj`：仅在需要 `AnyHashable` 时按需生成
- Schema 内 `test_execution` 字段：`{"outcome": "success" / "failure", "message": ...}` 或 `"not-exercised"` / `"pending"`

---

## 阶段三：验证与测试

### 运行 Cangjie 测试

```bash
cd data/java/skeletons/<project>
cjpm build
cjc --test src/test
```

### 编译验证

翻译模块使用 `cjpm build` 进行编译验证，确保生成的 Cangjie 代码语法正确。

---

### Mock 测试验证（手动调试流程）

> 自动按 fragment 触发的 mock 测试已并入 §2.5 主流程。本节脚本保留作为**手动调试工具**：当主流程在某个 fragment 反复失败、需要单独复现/排查时使用。

#### 前置条件

- Java 项目位于 `projects/java/original_projects/<project>/`，能用 `mvn` 单独构建
- Cangjie 项目位于 `projects/cangjie/original_projects/<project>/`，含 `cjpm.toml` 与 `src/`
- `src/java/isolation_validation/` 下的 `helper.cj`、`simple_ioc.cj` 与 emitter 脚本可访问
- 安装：JDK 8/11、Maven、Python 3、Cangjie SDK（cjpm/cjc）
- AspectJ + JUnit 4/5 依赖会被 `mock.sh` 自动注入到 Java 项目

#### 1. 生成 mock 测试样本

```bash
./mock.sh <project>
```

- 复制 Java 项目到 `src/java/isolation_validation/<project>/` 工作副本（不污染原始目录）
- 注入 AspectJ 依赖（`modify_pom.py`），向每个 Java 包补 `LoggingAspect.java` / `CustomToStringConverter.java`（`add_java_files.py`）
- 枚举 `src/test/java/**/*Test.java` 内的 `@Test` 方法，逐个 `mvn clean install -Dtest=<FQCN>#<method>`
- 解析方法级日志（`log_parser.py` + `script.py`），将 `<stem>_test.cj` 与 `<stem>.workflow.json` emit 到 `/tmp/cangjie_mock/<project>/`

> ⚠️ 当前 `mock.sh` 中 `TEST_CLASS` **硬编码为 `com.example.minimal.AppTest`**，仅适用于 minimal 示例。运行其他项目前需先在 `mock.sh` 中替换该常量；自动枚举将随主流程接入完成。

#### 2. 注入 mock 运行时辅助

```bash
./runtime.sh inject <project>
```

- 按 `cjpm.toml` 中的 `name` 字段将 `helper.cj` 与 `simple_ioc.cj` 渲染为 `<project>.runtime` 包后写入 `projects/cangjie/original_projects/<project>/src/runtime/`
- `helper.cj` 模板：`src/java/isolation_validation/helper.cj`
- `simple_ioc.cj` 模板：`src/java/isolation_validation/simple_ioc.cj`

#### 3. 运行 mock 测试

##### 选项 A：批量执行（最简）

```bash
./run.sh <project> [METHOD]
```

- 全局 `change_mode apply`（把 `private` / `protected` 字段与零参 init 临时改成 `public`，记录 `// CHANGE_MODE:` 桩注释以便还原）
- 对 staging 中匹配的每条测试：拷贝到 `$CJ_SRC/test/` → `side_effect.py instrument` 在 focal method 调用点注入副作用回放 → `cjpm test` → `side_effect.py deinstrument` → 清除测试副本
- 退出（含 Ctrl-C）时 trap 自动 `change_mode restore`

`METHOD` 为可选子串过滤 `_test.cj` 文件名，留空则跑全部。

##### 选项 B：批量执行并记录日志（推荐调试）

```bash
./log_tests.sh <project> [METHOD]
```

- 与 `run.sh` 行为一致，但把每条 `cjpm test` 的 stdout/stderr `tee` 到 `logs/cjpm_test_<project>_<timestamp>.log`
- 每条测试单独写入 `>>> PASS: <name> (rc=0)` / `>>> FAIL: <name> (rc=N)` 摘要
- 末尾追加 SUMMARY，列出全部通过 / 失败的测试名

##### 选项 C：单步调试（手动 cjpm test）

```bash
./instrument.sh apply <project> [METHOD]   # 应用 change_mode 与 side_effect，不跑测试
# 在 projects/cangjie/original_projects/<project>/ 下手动 cjpm test，可反复
./instrument.sh restore <project>          # 还原源代码（去桩 + 修饰符还原）
```

#### 4. 清理

```bash
./runtime.sh clean <project>                  # 删除 helper.cj / simple_ioc.cj
rm -rf /tmp/cangjie_mock/<project>            # 重新采集 Java 端日志前清空 staging
```

#### 调试脚本一览

| 脚本            | 位置        | 用途                                         |
| --------------- | ----------- | -------------------------------------------- |
| `mock.sh`       | repo 父目录 | Java → `_test.cj` 一次性生成（耗时）         |
| `runtime.sh`    | repo 父目录 | 注入 / 清理 `helper.cj` 与 `simple_ioc.cj`   |
| `run.sh`        | repo 父目录 | 批量跑 mock 测试，仅终端输出                 |
| `log_tests.sh`  | repo 父目录 | 同 `run.sh`，并把 `cjpm test` 输出落 `logs/` |
| `instrument.sh` | repo 父目录 | 手动 apply / restore，便于反复跑 cjpm test   |

---

## 核心模块说明

### x2cangjie 独有模块

| 模块        | 路径                                                           | 功能                                          |
| ----------- | -------------------------------------------------------------- | --------------------------------------------- |
| Schema 生成 | `src/java/decomposition/create_schema.py`                      | tree-sitter 解析 Java AST                     |
| 类型翻译    | `src/java/type_resolution/translate_type_rag.py`               | 确定性类型解析、KB 缓存、interface shim       |
| 骨架生成    | `src/java/translation/create_skeleton.py`                      | 生成 Cangjie 骨架文件                         |
| 片段翻译    | `src/java/translation/compositional_translation_validation.py` | LLM 翻译与增量验证                            |
| 编译验证    | `src/java/translation/cangjie_compilation_validation.py`       | cjpm build 验证                               |
| Prompt 生成 | `src/java/translation/prompt_generator.py`                     | Cangjie ICL 示例，含 RAG 注入                 |
| 依赖解析    | `src/java/translation/get_reverse_traversal.py`                | 按 pre-generated 顺序翻译                     |
| 依赖生成    | `utils.py`                                                     | 使用 jdeps 生成 traversal.json                |
| RAG 引擎    | `src/java/rag/`                                                | 混合检索（向量+BM25），CangjieCorpus 文档检索 |
| 语料加载    | `src/java/rag/corpus_loader.py`                                | Markdown 分块、代码块保护、MinHash 去重       |
| 查询构建    | `src/java/rag/query_builder.py`                                | Java→Cangjie 术语映射查询                     |
| 混合检索    | `src/java/rag/retriever.py`                                    | ChromaDB 向量 + BM25 + RRF 融合               |
| 索引构建    | `src/java/rag/indexer.py`                                      | 离线索引：文本分块 → 向量化 → 存储            |
| 上下文注入  | `src/java/rag/injector.py`                                     | 文档块格式化与 Prompt 注入                    |

### 复用 cangjie 的模块

| 模块           | 路径                                                | 功能                   |
| -------------- | --------------------------------------------------- | ---------------------- |
| 缩减第三方依赖 | `src/java/preprocessing/reduce_third_party_libs.py` | 移除未使用的第三方依赖 |
| 分解测试       | `src/java/preprocessing/decompose_dev_test.py`      | 将测试分解为独立片段   |
| 提取测试       | `src/java/static_analysis/extract_source_tests.py`  | 提取测试覆盖率信息     |

## 配置文件

- `configs/model_configs.yaml` - LLM API 配置
- `configs/prompt_templates.yaml` - Prompt 模板（Cangjie 代码示例）
- `configs/java_cangjie_terms.yaml` - Java→Cangjie 术语映射（RAG 查询构建）

## 与 TRAM/cangjie 的区别

| 特性     | TRAM           | cangjie        | x2cangjie    |
| -------- | -------------- | -------------- | ------------ |
| 翻译方向 | Java→Python    | Java→Python    | Java→Cangjie |
| AST 解析 | tree-sitter    | CodeQL         | tree-sitter  |
| 类型分析 | CodeQL         | CodeQL         | RAG + cjpm   |
| 编译验证 | Python exec    | GraalVM        | cjpm build   |
| ICL 示例 | Python         | Python         | Cangjie      |
| 翻译方式 | 全量翻译后重组 | 全量翻译后重组 | 增量翻译验证 |

## 目录结构

```
x2cangjie/
├── configs/
│   ├── model_configs.yaml       # LLM API 配置
│   └── prompt_templates.yaml     # Prompt 模板（Cangjie 示例）
├── scripts/java/
│   ├── download_original_projects.sh  # 下载原始 Java 项目
│   ├── build_original_projects.sh    # 构建原始项目
│   ├── add_plugin.sh            # 添加 JAR 插件
│   ├── handle_keyword_conflicts.sh  # 处理 Cangjie 关键字冲突
│   ├── handle_name_conflicts.sh    # 处理内部类/子包展平/shadow 命名冲突
│   ├── merge_jar.sh             # 构建并合并 JAR
│   ├── generate_cg.sh           # 生成调用图
│   ├── reduce_third_party_libs.sh  # 缩减第三方依赖
│   ├── extract_coverage.sh      # 提取测试覆盖率
│   ├── decompose_test.sh        # 分解测试
│   ├── create_schema.sh         # 创建 Schema（tree-sitter）
│   ├── create_skeleton.sh       # 创建骨架
│   ├── build_mock_corpus.sh     # 生成 mock 测试语料（前置一次性）
│   ├── translate_fragment.sh     # 增量翻译验证（含 mock 测试）
│   └── get_dependencies.sh      # 生成 traversal.json
├── src/java/
│   ├── decomposition/
│   │   └── create_schema.py     # Schema 生成（tree-sitter）
│   ├── type_resolution/
│   │   └── translate_type_rag.py  # 确定性类型解析
│   ├── translation/
│   │   ├── create_skeleton.py    # 骨架生成
│   │   ├── compositional_translation_validation.py  # 增量翻译验证（含 RAG）
│   │   ├── cangjie_compilation_validation.py       # 编译验证
│   │   ├── prompt_generator.py  # Prompt 生成（含 RAG 注入）
│   │   └── get_reverse_traversal.py  # 按顺序翻译
│   ├── rag/                      # RAG 检索增强生成系统
│   │   ├── __init__.py           # RagEngine 统一接口
│   │   ├── corpus_loader.py      # Markdown 分块引擎
│   │   ├── query_builder.py      # Java→Cangjie 查询构建
│   │   ├── retriever.py          # 混合检索（向量+BM25+RRF）
│   │   ├── injector.py          # 文档块格式化注入
│   │   └── indexer.py           # 离线索引构建
│   ├── preprocessing/           # 预处理脚本
│   │   ├── handle_keyword_conflicts.py   # 关键字冲突处理
│   │   ├── handle_name_conflicts.py      # 命名冲突处理（内部类、子包展平、继承 shadow）
│   │   ├── _shared.py                     # 共享工具（tree-sitter 解析等）
│   │   ├── reduce_third_party_libs.py
│   │   └── decompose_dev_test.py
│   └── static_analysis/         # 复用 cangjie
│       └── extract_source_tests.py
├── data/java/rag/                # RAG 索引数据（构建生成）
│   ├── chromadb/                 # ChromaDB 向量存储
│   ├── bm25_index.pkl           # BM25 稀疏索引
│   └── chunks.json              # 文档块元数据
└── docs/
    └── start.md                 # 本文档

# repo 父目录下的 mock 测试调试脚本（暂未并入主流程）
mock.sh           # Java → /tmp/cangjie_mock/<P>/*_test.cj 一次性生成
runtime.sh        # 注入 / 清理 helper.cj 与 simple_ioc.cj
run.sh            # 批量跑 mock 测试
log_tests.sh      # 同 run.sh，并把 cjpm test 输出落 logs/
instrument.sh     # 单步调试（apply / restore，便于反复跑 cjpm test）
```
