#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <project> <schema_model> <temperature> <suffix> [include_tests] [agent_model]" >&2
  exit 1
fi

project=$1
model=$2
temperature=$3
suffix=$4
include_tests=${5:-false}
agent_model=${6:-}

args=(
  --project "$project"
  --model "$model"
  --temperature "$temperature"
  --suffix "$suffix"
  --types-only
)

if [ "$include_tests" = "true" ]; then
  args+=(--include-tests)
fi
if [ -n "$agent_model" ]; then
  args+=(--agent-model "$agent_model")
fi

python3 -m src.java.type_resolution.cli "${args[@]}"
