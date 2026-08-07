#!/bin/bash

# Usage: ./scripts/java/get_dependencies.sh <project> <suffix> [project_root] [jdeps]
# Example: ./scripts/java/get_dependencies.sh JavaFeatureTest ""

if [ $# -lt 2 ] || [ $# -gt 4 ]; then
  echo "Usage: ./scripts/java/get_dependencies.sh <project> <suffix> [project_root] [jdeps]"
  exit 1
fi

project=$1
suffix=$2
project_root=${3:-}
jdeps=${4:-}

echo "extracting dependencies for $project"
args=(
  --project_name "$project"
  --function parse_dependencies
  --suffix "$suffix"
)
if [ -n "$project_root" ]; then
  args+=(--project_root "$project_root")
fi
if [ -n "$jdeps" ]; then
  args+=(--jdeps "$jdeps")
fi
python3 -m src.java.utils.parse_dependencies "${args[@]}"
