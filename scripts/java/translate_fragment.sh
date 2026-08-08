#!/usr/bin/env bash

set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "Usage: $0 <project> <schema_model> <suffix> <temperature> [translate_tests] [agent_model]" >&2
  exit 1
fi

project=$1
model=$2
suffix=$3
temperature=$4
translate_tests=${5:-false}
agent_model=${6:-}

args=(
  --project "$project"
  --model "$model"
  --suffix "$suffix"
  --temperature "$temperature"
)
if [ "$translate_tests" = "true" ]; then
  args+=(--include-tests)
elif [ "$translate_tests" != "false" ]; then
  echo "Invalid translate_tests value: $translate_tests (expected true or false)" >&2
  exit 1
fi
if [ -n "$agent_model" ]; then
  args+=(--agent-model "$agent_model")
fi

export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
python3 -m src.java.translation.baseline_fragment_translation "${args[@]}"
