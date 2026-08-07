#!/bin/bash

# Resolve types with Codex, generate the TODO skeleton, and require cjpm build success.
# Usage: ./scripts/java/create_skeleton.sh <project> <schema_model> <suffix> <temperature> [translate_tests] [agent_model]
# translate_tests: "true" or "false" (default: false)

if [ $# -lt 4 ]; then
  echo "Usage: ./scripts/java/create_skeleton.sh <project> <schema_model> <suffix> <temperature> [translate_tests] [agent_model]"
  exit 1
fi

project=$1
model=$2
suffix=$3
temperature=$4
translate_tests=${5:-false}
agent_model=${6:-}

if [ "$translate_tests" != "true" ] && [ "$translate_tests" != "false" ]; then
  echo "Invalid translate_tests value: $translate_tests (expected true or false)"
  exit 1
fi

echo "Creating skeleton for $project"
export PYTHONPATH=$(pwd)
args=(
  --project "$project"
  --model "$model"
  --suffix "$suffix"
  --temperature "$temperature"
)
if [ "$translate_tests" = "true" ]; then
  args+=(--include-tests)
fi
if [ -n "$agent_model" ]; then
  args+=(--agent-model "$agent_model")
fi
python3 -m src.java.type_resolution.cli "${args[@]}"
