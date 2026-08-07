#!/bin/bash

# Usage: ./scripts/java/handle_name_conflicts.sh <project>
# Example: ./scripts/java/handle_name_conflicts.sh JavaFeatureTest

if [ $# -ne 1 ]; then
  echo "Usage: ./scripts/java/handle_name_conflicts.sh <project>"
  exit 1
fi

project="$1"

echo "Handling name conflicts for $project"
export PYTHONPATH=$(pwd)
python3 -m src.java.preprocessing.handle_name_conflicts --project "$project"
