# EvoSuite Cleaned Base 完整命令流

从 `projects/java/cleaned_final_projects_evosuite/<project>` 生成当前主流程使用的 `_evosuite_cleaned_base`。

```bash
project=<project>
model=deepseek-chat
temperature=0.0
suffix=_evosuite_cleaned_base

src="projects/java/cleaned_final_projects_evosuite/${project}"
auto="projects/java/automated_reduced_projects/${project}"
dst="projects/java/cleaned_final_projects${suffix}/${project}"
```

## 1. 接入预处理输入目录并清理 EvoSuite 测试污染

`handle_keyword_conflicts.sh` 固定读取 `automated_reduced_projects/<project>`，所以先把 EvoSuite 项目放到这里，再原地清理 EvoSuite 测试。这样后面的关键字处理、命名冲突处理、call graph 和 schema 都基于同一份已清理源码。

```bash
rm -rf "$auto"
mkdir -p "$(dirname "$auto")"
cp -r "$src" "$auto"

python src/java/isolation_validation/clean_evosuite_tests.py "$auto" "$auto"
find "$auto/src/test/java" -name '*_scaffolding.java' -delete
```

这一步会去掉 `org.evosuite.runtime.*`、`EvoRunner`、`EvoRunnerParameters`、`extends *_ESTest_scaffolding`，并把 `MockFile`、`MockPrintWriter`、`MockPrintStream` 等替换回 Java 标准类。

## 2. 处理关键字、命名冲突和 shadow 冲突

```bash
bash scripts/java/handle_keyword_conflicts.sh "$project"
bash scripts/java/handle_name_conflicts.sh "$project"
```

产物：

```text
projects/java/keyword_handled/<project>/
projects/java/name_handled/<project>/
```

## 3. 构建 JAR、生成 call graph、缩减依赖

```bash
bash scripts/java/merge_jar.sh "$project"
bash scripts/java/generate_cg.sh "$project"
bash scripts/java/reduce_third_party_libs.sh "$project"
```

产物：

```text
projects/java/name_handled/<project>/target/*.jar
projects/java/name_handled/<project>/target/*-tests.jar
projects/java/name_handled/<project>/target/*-merged.jar
projects/java/name_handled/<project>/callgraph.txt
data/java/call_graphs/<project>/callgraph.txt
```

## 4. 生成 `_evosuite_cleaned_base` 项目目录

```bash
rm -rf "$dst"
mkdir -p "$(dirname "$dst")"
cp -r "projects/java/name_handled/${project}" "$dst"
```

## 5. 重新构建 cleaned base

```bash
(
  cd "$dst"
  mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip \
    -Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8
)
```

必须生成：

```text
projects/java/cleaned_final_projects_evosuite_cleaned_base/<project>/target/classes
```

## 6. 重新生成 schema

```bash
bash scripts/java/create_schema.sh "$project" "$model" "$temperature" "$suffix"
```

产物：

```text
data/java/schemas_evosuite_cleaned_base/<model>/<temperature>/<project>/
```

## 7. 重新生成 dependencies / traversal

```bash
bash scripts/java/get_dependencies.sh "$project" "$suffix"
```

产物：

```text
data/java/dependencies_evosuite_cleaned_base/<project>/traversal.json
```

## 8. 类型翻译与 skeleton

```bash
bash scripts/java/translate_types.sh "$project" "$model" "$temperature" "$suffix"
bash scripts/java/create_skeleton.sh "$project" "$model" "$suffix" "$temperature" false
```
