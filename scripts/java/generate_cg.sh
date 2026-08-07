#!/bin/bash

# Usage: ./scripts/java/generate_cg.sh <project>

if [ $# -ne 1 ]; then
  echo "Usage: ./generate_cg.sh <project>"
  exit 1
fi

script_dir=$(dirname "$(realpath "$0")")

project="$1"
project_dir="./projects/java/name_handled/$project"

if [ ! -d "$project_dir" ]; then
  echo "Error: Directory '$project_dir' does not exist."
  exit 1
fi

cd "$project_dir" || exit 1

TARGET_DIR="target"

MAIN_JAR=$(find "$TARGET_DIR" -type f -name "*[^-tests].jar" | grep -v "merged" | head -n 1)

MERGED_JAR="$TARGET_DIR/$(basename "$MAIN_JAR" .jar)-merged.jar"

JAVACG_PATH="$script_dir/../../misc/java-callgraph/target/javacg-0.1-SNAPSHOT-static.jar"

if [ ! -f "$JAVACG_PATH" ]; then
  echo "Error: javacg-0.1-SNAPSHOT-static.jar not found at $JAVACG_PATH."
  exit 1
fi

echo "Generating call graph for $MERGED_JAR..."
java -jar "$JAVACG_PATH" "$MERGED_JAR" > callgraph.txt

echo "Call graph saved to callgraph.txt."

# Also copy to data/java/call_graphs/ for downstream scripts (create_schema.py, get_dependencies.py)
DATA_DIR="$script_dir/../../data/java/call_graphs/$project"
mkdir -p "$DATA_DIR"
cp callgraph.txt "$DATA_DIR/callgraph.txt"
echo "Call graph also copied to $DATA_DIR/callgraph.txt."
