#!/bin/bash

# Usage: ./scripts/java/get_dependencies.sh <project> <suffix> [project_root] [jdeps] [maven]
# Example: ./scripts/java/get_dependencies.sh JavaFeatureTest ""

if [ $# -lt 2 ] || [ $# -gt 5 ]; then
  echo "Usage: ./scripts/java/get_dependencies.sh <project> <suffix> [project_root] [jdeps] [maven]"
  exit 1
fi

project=$1
suffix=$2
project_root=${3:-}
jdeps=${4:-}
maven=${5:-}

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
if [ -n "$maven" ]; then
  args+=(--maven "$maven")
fi
python3 -m src.java.utils.parse_dependencies "${args[@]}"
