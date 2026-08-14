#!/bin/bash

# Usage: bash scripts/java/analyze_errors.sh <project> <model> <temperature> [suffix] [output_file]
# Example: bash scripts/java/analyze_errors.sh jansi gpt-4o-2024-11-20 0.0
# Example: bash scripts/java/analyze_errors.sh jansi deepseek-chat 0.0 "" results.txt
# Example: bash scripts/java/analyze_errors.sh jansi gpt-4o-2024-11-20 0.0 "" "" --skip-build

if [ $# -lt 3 ]; then
  echo "Usage: $0 <project> <model> <temperature> [suffix] [output_file] [--skip-build]"
  echo "Example: $0 jansi gpt-4o-2024-11-20 0.0"
  echo "Example: $0 jansi gpt-4o-2024-11-20 0.0 '' results.txt"
  echo "Example: $0 jansi gpt-4o-2024-11-20 0.0 '' '' --skip-build"
  exit 1
fi

project="$1"
model="$2"
temperature="$3"
suffix="${4:-}"
output="${5:-}"
skip_build=""

# Check for --skip-build flag in remaining args
for arg in "$@"; do
  if [ "$arg" = "--skip-build" ]; then
    skip_build="--skip-build"
  fi
done

export PYTHONPATH=$(pwd)
python3 -m src.java.analysis.analyze_errors \
    --project "$project" \
    --model "$model" \
    --temperature "$temperature" \
    --suffix "$suffix" \
    ${output:+--output "$output"} \
    ${skip_build}
