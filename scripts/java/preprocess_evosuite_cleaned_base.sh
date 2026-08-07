#!/usr/bin/env bash
# preprocess_evosuite_cleaned_base.sh
# 对单个项目执行从 EvoSuite 项目到 _evosuite_cleaned_base 的完整预处理流程。
#
# 用法:

# Ensure UTF-8 encoding for Java charset-dependent tests
export LANG=C.utf8
export LC_ALL=C.utf8
#   bash scripts/java/preprocess_evosuite_cleaned_base.sh <project> [evo_src_suffix]
#
# 参数:
#   <project>        项目名，如 jansi, commons-cli, commons-codec 等
#   [evo_src_suffix] EvoSuite 源目录后缀，默认 _evosuite
#                    脚本会从 projects/java/cleaned_final_projects<后缀>/<project> 读取
#
# 示例:
#   bash scripts/java/preprocess_evosuite_cleaned_base.sh jansi
#   bash scripts/java/preprocess_evosuite_cleaned_base.sh commons-codec _evosuite
#
# 流程参考: evosuite_cleaned_base_commands.md

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <project> [evo_src_suffix]"
  echo "Example: $0 jansi"
  echo "Example: $0 commons-codec _evosuite"
  exit 1
fi

PROJECT="$1"
EVO_SUFFIX="${2:-_evosuite}"
SUFFIX="_evosuite_cleaned_base"

JAVA11_PROJECTS="JavaFastPFOR commons-exec commons-graph"
JAVA11_RUNTIME_PROJECTS="jansi"
JAVA11_HOME="/usr/lib/jvm/java-11-openjdk-amd64"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

EVO_SRC="projects/java/cleaned_final_projects${EVO_SUFFIX}/${PROJECT}"
AUTO="projects/java/automated_reduced_projects/${PROJECT}"
KEYWORD="projects/java/keyword_handled/${PROJECT}"
NAME="projects/java/name_handled/${PROJECT}"
DST="projects/java/cleaned_final_projects${SUFFIX}/${PROJECT}"

echo "============================================================"
echo "  Preprocessing: $PROJECT"
echo "  EvoSuite source: $EVO_SRC"
echo "  Output:          $DST"
echo "============================================================"

# ── 检查 EvoSuite 源目录是否存在 ──
if [ ! -d "$EVO_SRC" ]; then
  echo "ERROR: EvoSuite source directory not found: $EVO_SRC"
  echo "       You need to prepare this directory first (add EvoSuite tests to original project)."
  echo ""
  echo "Typical setup: copy original project and add EvoSuite tests, then place under:"
  echo "  projects/java/cleaned_final_projects_evosuite/<project>/"
  exit 1
fi

# ── Step 1: 复制 EvoSuite 项目到 automated_reduced_projects 并清理 EvoSuite 测试 ──
echo ""
echo ">>> Step 1/8: Copy EvoSuite project & clean tests"

rm -rf "$AUTO"
mkdir -p "$(dirname "$AUTO")"
cp -r "$EVO_SRC" "$AUTO"

export PYTHONPATH="$(pwd)"
python3 -m src.java.preprocessing.clean_evosuite_tests "$AUTO" "$AUTO"
find "$AUTO/src/test/java" -name '*_scaffolding.java' -type f -delete
rm -rf "$AUTO/src/test"

echo "    Done: $AUTO"

# ── Step 2: 处理 Cangjie 关键字冲突 ──
echo ""
echo ">>> Step 2/8: Handle Cangjie keyword conflicts"

bash scripts/java/handle_keyword_conflicts.sh "$PROJECT"
echo "    Done: $KEYWORD"

# ── Step 3: 处理命名冲突 (展平 / shadow) ──
echo ""
echo ">>> Step 3/8: Handle name conflicts"

bash scripts/java/handle_name_conflicts.sh "$PROJECT"
echo "    Done: $NAME"

# ── Step 4: 构建 JAR ──
echo ""
echo ">>> Step 4/8: Build JAR (mvn clean install)"

if echo "$JAVA11_PROJECTS" | grep -qw "$PROJECT"; then
  echo "  Building with JDK 11 ($PROJECT)..."
  project_dir="projects/java/name_handled/${PROJECT}"
  if [ ! -d "$project_dir" ]; then
    echo "ERROR: $project_dir not found"
    exit 1
  fi
  cd "$project_dir"
  JAVA_HOME="$JAVA11_HOME" mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip -Dmaven.javadoc.skip=true \
    -Dmaven.compiler.source=11 -Dmaven.compiler.target=11
  cd "$ROOT"

  TARGET_DIR="$project_dir/target"
  MAIN_JAR=$(find "$TARGET_DIR" -type f -name "*[^-tests].jar" | grep -v "merged" | head -n 1)
  TEST_JAR=$(find "$TARGET_DIR" -type f -name "*-tests.jar" | head -n 1 || true)
  if [ -z "$MAIN_JAR" ]; then
    echo "ERROR: Could not find main JAR in $TARGET_DIR"
    exit 1
  fi
  MERGED_JAR="$TARGET_DIR/$(basename "$MAIN_JAR" .jar)-merged.jar"
  TEMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TEMP_DIR"' EXIT
  unzip -q "$MAIN_JAR" -d "$TEMP_DIR"
  if [ -n "$TEST_JAR" ]; then
    unzip -q -o "$TEST_JAR" -d "$TEMP_DIR"
  else
    echo "  No test JAR found (src/test removed), using main JAR only"
  fi
  jar cf "$MERGED_JAR" -C "$TEMP_DIR" .
  echo "  Merged JAR: $MERGED_JAR"
elif echo "$JAVA11_RUNTIME_PROJECTS" | grep -qw "$PROJECT"; then
  echo "  Building with JDK 11 runtime ($PROJECT)..."
  project_dir="projects/java/name_handled/${PROJECT}"
  if [ ! -d "$project_dir" ]; then
    echo "ERROR: $project_dir not found"
    exit 1
  fi
  cd "$project_dir"
  JAVA_HOME="$JAVA11_HOME" mvn clean install -Drat.skip -Dgpg.skip -Dcheckstyle.skip \
    -DjavadocSource=8 -Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8
  cd "$ROOT"

  TARGET_DIR="$project_dir/target"
  MAIN_JAR=$(find "$TARGET_DIR" -type f -name "*[^-tests].jar" | grep -v "merged" | head -n 1)
  TEST_JAR=$(find "$TARGET_DIR" -type f -name "*-tests.jar" | head -n 1 || true)
  if [ -z "$MAIN_JAR" ]; then
    echo "ERROR: Could not find main JAR in $TARGET_DIR"
    exit 1
  fi
  MERGED_JAR="$TARGET_DIR/$(basename "$MAIN_JAR" .jar)-merged.jar"
  TEMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TEMP_DIR"' EXIT
  unzip -q "$MAIN_JAR" -d "$TEMP_DIR"
  if [ -n "$TEST_JAR" ]; then
    unzip -q -o "$TEST_JAR" -d "$TEMP_DIR"
  else
    echo "  No test JAR found (src/test removed), using main JAR only"
  fi
  jar cf "$MERGED_JAR" -C "$TEMP_DIR" .
  echo "  Merged JAR: $MERGED_JAR"
else
  bash scripts/java/merge_jar.sh "$PROJECT"
fi
echo "    Done: JAR files in $NAME/target/"

# ── Step 5: 生成 call graph ──
echo ""
echo ">>> Step 5/8: Generate call graph"

bash scripts/java/generate_cg.sh "$PROJECT"
echo "    Done: data/java/call_graphs/${PROJECT}/callgraph.txt"

# ── Step 6: 缩减第三方依赖 ──
echo ""
echo ">>> Step 6/8: Reduce third-party libs"

bash scripts/java/reduce_third_party_libs.sh "$PROJECT"

# ── Step 7: 复制到 cleaned_final_projects_evosuite_cleaned_base ──
echo ""
echo ">>> Step 7/8: Copy to cleaned_final_projects_evosuite_cleaned_base"

rm -rf "$DST"
mkdir -p "$(dirname "$DST")"
cp -r "$NAME" "$DST"

echo "    Done: $DST"

# ── Step 8: 重新构建 cleaned base (生成 target/classes) ──
echo ""
echo ">>> Step 8/8: Rebuild cleaned base (mvn clean install -DskipTests)"

(
  cd "$DST"
  if echo "$JAVA11_PROJECTS" | grep -qw "$PROJECT"; then
    echo "  Rebuilding with JDK 11 ($PROJECT)..."
    JAVA_HOME="$JAVA11_HOME" mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip -Dmaven.javadoc.skip=true \
      -Dmaven.compiler.source=11 -Dmaven.compiler.target=11
  elif echo "$JAVA11_RUNTIME_PROJECTS" | grep -qw "$PROJECT"; then
    echo "  Rebuilding with JDK 11 runtime ($PROJECT)..."
    JAVA_HOME="$JAVA11_HOME" mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip \
      -DjavadocSource=8 -Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8
  else
    mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip \
      -Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8
  fi
)

echo ""
echo "============================================================"
echo "  PREPROCESSING COMPLETE: $PROJECT"
echo "  Output: $DST"
echo ""
echo "  Next steps:"
echo "    bash scripts/java/create_schema.sh $PROJECT <model> <temp> _evosuite_cleaned_base"
echo "    bash scripts/java/get_dependencies.sh $PROJECT _evosuite_cleaned_base"
echo "============================================================"
