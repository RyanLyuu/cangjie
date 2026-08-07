#!/usr/bin/env bash
# preprocess_evo_cleaned.sh
# Run EvoSuite cleaned base preprocessing for a single project.
# Reference: evosuite_cleaned_base_commands.md
#
# Usage:
#   bash scripts/java/preprocess_evo_cleaned.sh <project>
#
# Example:
#   bash scripts/java/preprocess_evo_cleaned.sh commons-codec
#
# Prerequisites:
#   - projects/java/cleaned_final_projects_evosuite/<project> exists
#   - misc/java-callgraph/target/javacg-0.1-SNAPSHOT-static.jar built
#   - JDK 8 + Maven (JDK 11 needed for JavaFastPFOR)

set -euo pipefail

# Ensure UTF-8 encoding for Java charset-dependent tests
export LANG=C.utf8
export LC_ALL=C.utf8

if [ $# -ne 1 ]; then
  echo "Usage: $0 <project>"
  echo "Example: $0 commons-codec"
  exit 1
fi

PROJECT="$1"
SUFFIX="_evosuite_cleaned_base"

# JavaFastPFOR requires JDK 11 for compilation (bytecode level).
# jansi requires JDK 11 runtime for spotless-maven-plugin.
# When JAVA_8_MAVEN_OPTS is empty, merge_jar.sh uses its own defaults (JDK 8).
JAVA11_PROJECTS="JavaFastPFOR commons-exec commons-graph"
JAVA11_RUNTIME_PROJECTS="jansi"
JAVA11_HOME="/usr/lib/jvm/java-11-openjdk-amd64"

# commons-graph requires skipping animal-sniffer: its parent POM's signature
# artifact (java110:1.0) is unavailable from Maven Central.
# Also clear any cached resolution failure so Maven doesn't short-circuit.
ANIMAL_SNIFFER_SKIP_PROJECTS="commons-graph"
if echo "$ANIMAL_SNIFFER_SKIP_PROJECTS" | grep -qw "$PROJECT"; then
  ANIMAL_SNIFFER_SKIP="-Danimal.sniffer.skip=true"
  rm -rf ~/.m2/repository/org/codehaus/mojo/signature/java110 2>/dev/null || true
else
  ANIMAL_SNIFFER_SKIP=""
fi

if echo "$JAVA11_PROJECTS" | grep -qw "$PROJECT"; then
  MVN_COMPILER_OPTS="-Dmaven.compiler.source=11 -Dmaven.compiler.target=11"
elif echo "$JAVA11_RUNTIME_PROJECTS" | grep -qw "$PROJECT"; then
  MVN_COMPILER_OPTS="-Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8"
else
  MVN_COMPILER_OPTS="-Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8"
fi

# Helper function to run Maven with optional JDK 11 runtime
run_maven() {
  local project="$1"
  local mvn_args="$2"
  if echo "$JAVA11_RUNTIME_PROJECTS" | grep -qw "$project"; then
    echo "  Using JDK 11 runtime: $JAVA11_HOME"
    JAVA_HOME="$JAVA11_HOME" mvn clean install $mvn_args
  else
    mvn clean install $mvn_args
  fi
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

EVO_SRC="projects/java/cleaned_final_projects_evosuite/${PROJECT}"
AUTO="projects/java/automated_reduced_projects/${PROJECT}"
KEYWORD="projects/java/keyword_handled/${PROJECT}"
NAME="projects/java/name_handled/${PROJECT}"
DST="projects/java/cleaned_final_projects${SUFFIX}/${PROJECT}"

echo "============================================================"
echo "  EvoSuite Cleaned Base preprocessing: ${PROJECT}"
echo "  Source: ${EVO_SRC}"
echo "  Output: ${DST}"
echo "============================================================"

# -- Check source directory --
if [ ! -d "$EVO_SRC" ]; then
  echo "ERROR: EvoSuite source directory not found: ${EVO_SRC}"
  echo "  Please place the project with EvoSuite tests there, e.g.:"
  echo "  mkdir -p projects/java/cleaned_final_projects_evosuite"
  echo "  cp -r projects/java/original_projects/${PROJECT} ${EVO_SRC}"
  exit 1
fi

# -- Step 1: Copy and clean EvoSuite tests --
echo ""
echo "[1/8] Copy EvoSuite project and clean tests"

rm -rf "$AUTO"
mkdir -p "$(dirname "$AUTO")"
cp -r "$EVO_SRC" "$AUTO"

export PYTHONPATH="$(pwd)"
python3 -m src.java.preprocessing.clean_evosuite_tests "$AUTO" "$AUTO"
find "$AUTO/src/test/java" -name '*_scaffolding.java' -type f -delete 2>/dev/null || true
rm -rf "$AUTO/src/test"

echo "  Done: ${AUTO}"

# -- Step 2: Keyword conflicts --
echo ""
echo "[2/8] Handle Cangjie keyword conflicts"

bash scripts/java/handle_keyword_conflicts.sh "$PROJECT"

echo "  Done: ${KEYWORD}"

# -- Step 3: Name conflicts --
echo ""
echo "[3/8] Handle name conflicts (flatten + shadow)"

bash scripts/java/handle_name_conflicts.sh "$PROJECT"

echo "  Done: ${NAME}"

# -- Step 4: Build JAR --
echo ""
echo "[4/8] Build JAR (mvn clean install)"

# merge_jar.sh hardcodes JDK 8 flags. For JavaFastPFOR we override after it runs.
# We still call merge_jar.sh for the JAR merge logic, but for JavaFastPFOR we
# rebuild with JDK 11 flags afterwards.
if echo "$JAVA11_PROJECTS" | grep -qw "$PROJECT"; then
  # Run merge_jar.sh to get the merge logic, but it will fail on mvn.
  # Instead, build manually with JDK 11 settings.
  project_dir="projects/java/name_handled/${PROJECT}"
  if [ ! -d "$project_dir" ]; then
    echo "ERROR: $project_dir not found"
    exit 1
  fi
  cd "$project_dir"
  echo "  Building with JDK 11 (JavaFastPFOR)..."
  JAVA_HOME="$JAVA11_HOME" mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip -Dmaven.javadoc.skip=true $ANIMAL_SNIFFER_SKIP $MVN_COMPILER_OPTS
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
  JAVA_HOME="$JAVA11_HOME" mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip \
    $ANIMAL_SNIFFER_SKIP -DjavadocSource=8 $MVN_COMPILER_OPTS
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

echo "  Done: JAR files in ${NAME}/target/"

# -- Step 5: Generate call graph --
echo ""
echo "[5/8] Generate call graph"

bash scripts/java/generate_cg.sh "$PROJECT"

echo "  Done: data/java/call_graphs/${PROJECT}/callgraph.txt"

# -- Step 6: Reduce third-party libs --
echo ""
echo "[6/8] Reduce third-party libs"

bash scripts/java/reduce_third_party_libs.sh "$PROJECT"

# -- Step 7: Copy to evosuite_cleaned_base --
echo ""
echo "[7/8] Copy to cleaned_final_projects_evosuite_cleaned_base"

rm -rf "$DST"
mkdir -p "$(dirname "$DST")"
cp -r "$NAME" "$DST"

echo "  Done: ${DST}"

# -- Step 8: Rebuild cleaned base --
echo ""
echo "[8/8] Rebuild cleaned base (mvn clean install -DskipTests)"

cd "$DST"
if echo "$JAVA11_PROJECTS" | grep -qw "$PROJECT"; then
  echo "  Rebuilding with JDK 11 ($PROJECT)..."
  JAVA_HOME="$JAVA11_HOME" mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip -Dmaven.javadoc.skip=true $ANIMAL_SNIFFER_SKIP $MVN_COMPILER_OPTS
elif echo "$JAVA11_RUNTIME_PROJECTS" | grep -qw "$PROJECT"; then
  echo "  Rebuilding with JDK 11 runtime ($PROJECT)..."
  JAVA_HOME="$JAVA11_HOME" mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip \
    $ANIMAL_SNIFFER_SKIP -DjavadocSource=8 $MVN_COMPILER_OPTS
else
  mvn clean install -DskipTests -Drat.skip -Dgpg.skip -Dcheckstyle.skip $ANIMAL_SNIFFER_SKIP $MVN_COMPILER_OPTS
fi
cd "$ROOT"

# -- Verification --
echo ""
echo "============================================================"
if [ -d "${DST}/target/classes" ]; then
  echo "  OK: ${DST}/target/classes exists"
else
  echo "  WARNING: ${DST}/target/classes missing, downstream steps may fail"
fi
if [ -f "data/java/call_graphs/${PROJECT}/callgraph.txt" ]; then
  echo "  OK: callgraph.txt exists"
else
  echo "  WARNING: callgraph.txt missing, downstream steps may fail"
fi

echo ""
echo "  Preprocessing complete: ${PROJECT}"
echo ""
echo "  Next steps:"
echo "    bash scripts/java/create_schema.sh ${PROJECT} <model> 0.0 _evosuite_cleaned_base"
echo "    bash scripts/java/get_dependencies.sh ${PROJECT} _evosuite_cleaned_base"
echo "============================================================"
