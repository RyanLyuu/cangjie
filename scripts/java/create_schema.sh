#!/bin/bash

# Usage: ./scripts/java/create_schema.sh <project> <schema_model> <temperature> <suffix> [project_root]
# Example: ./scripts/java/create_schema.sh JavaFeatureTest gpt-4o-2024-11-20 0.0 ""

if [ $# -lt 4 ] || [ $# -gt 5 ]; then
  echo "Usage: ./scripts/java/create_schema.sh <project> <schema_model> <temperature> <suffix> [project_root]"
  exit 1
fi

project=$1
model_name=$2
temperature=$3
suffix=$4
project_root=${5:-}

echo "Creating schema for $project"
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"
args=(
  --project_name "$project"
  --suffix "$suffix"
  --model_name "$model_name"
  --temperature "$temperature"
)
if [ -n "$project_root" ]; then
  args+=(--project_root "$project_root")
fi
python3 -m src.java.decomposition.create_schema "${args[@]}"
