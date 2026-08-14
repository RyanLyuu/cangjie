#!/bin/bash

# Usage: ./scripts/java/translate_types.sh <project> <model_name> <temperature> <suffix> <translate_tests> <use_progressive_kb>
# Example: ./scripts/java/translate_types.sh commons-cli gpt-4o-2024-11-20 0.0 "" false true
# translate_tests: "true" or "false" (default: false)
# use_progressive_kb: "true" or "false" (default: true). Enables Progressive KB for few-shot type translation.

if [ $# -lt 4 ]; then
  echo "Usage: ./scripts/java/translate_types.sh <project> <model_name> <temperature> <suffix> [translate_tests] [use_progressive_kb]"
  exit 1
fi

project=$1
model_name=$2
temperature=$3
suffix=$4
translate_tests=${5:-false}
use_progressive_kb=${6:-true}

if [ "$translate_tests" != "true" ] && [ "$translate_tests" != "false" ]; then
  echo "Invalid translate_tests value: $translate_tests (expected true or false)"
  exit 1
fi

if [ "$use_progressive_kb" != "true" ] && [ "$use_progressive_kb" != "false" ]; then
  echo "Invalid use_progressive_kb value: $use_progressive_kb (expected true or false)"
  exit 1
fi

echo "Translating types for $project (translate_tests=$translate_tests, use_progressive_kb=$use_progressive_kb)"
export PYTHONPATH=$(pwd)
python src/java/type_resolution/translate_type_rag.py \
    --project_name=$project \
    --model_name=$model_name \
    --temperature=$temperature \
    --suffix=$suffix \
    --translate_tests=$translate_tests \
    --use_progressive_kb=$use_progressive_kb \
    --debug
