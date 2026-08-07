#!/bin/bash

# Usage: ./scripts/java/merge_jar.sh <project>

if [ $# -ne 1 ]; then
  echo "Usage: ./merge_jar.sh <project>"
  exit 1
fi

project="$1"
project_dir="./projects/java/name_handled/$project"

if [ ! -d "$project_dir" ]; then
  echo "Error: Directory '$project_dir' does not exist."
  exit 1
fi

if [ "$project" == "commons-graph" ]; then
  TARGET_FILE="$project_dir/src/main/java/org/apache/commons/graph/export/DefaultExportSelector.java"

  if [ ! -f "$TARGET_FILE" ]; then
    echo "Error: File '$TARGET_FILE' not found."
    exit 1
  fi

  awk 'NR==62 {$0="return null;"} {print}' "$TARGET_FILE" > "${TARGET_FILE}.tmp" && mv "${TARGET_FILE}.tmp" "$TARGET_FILE"
fi

if [ "$project" == "commons-pool" ]; then
  TARGET_FILE="$project_dir/src/test/java/org/apache/commons/pool2/performance/PerformanceTest.java"
  rm -f "$TARGET_FILE"
fi

cd "$project_dir" || exit 1

echo "Running 'mvn clean install' in $project_dir..."
if ! mvn clean install -Drat.skip -Dgpg.skip -Dcheckstyle.skip -Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8; then
  echo "Error: Maven build failed."
  exit 1
fi

TARGET_DIR="target"

MAIN_JAR=$(find "$TARGET_DIR" -type f -name "*[^-tests].jar" | grep -v "merged" | head -n 1)
TEST_JAR=$(find "$TARGET_DIR" -type f -name "*-tests.jar" | head -n 1)

MERGED_JAR="$TARGET_DIR/$(basename "$MAIN_JAR" .jar)-merged.jar"

if [ -z "$MAIN_JAR" ]; then
  echo "Error: Main JAR file not found in $TARGET_DIR."
  exit 1
fi

if [ -z "$TEST_JAR" ]; then
  echo "Error: Test JAR file not found in $TARGET_DIR."
  exit 1
fi

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

echo "Extracting $MAIN_JAR..."
unzip -q "$MAIN_JAR" -d "$TEMP_DIR"

echo "Extracting $TEST_JAR..."
unzip -q -o "$TEST_JAR" -d "$TEMP_DIR"

echo "Creating merged JAR at $MERGED_JAR..."
jar cf "$MERGED_JAR" -C "$TEMP_DIR" .

echo "Merged JAR created successfully at $MERGED_JAR."
