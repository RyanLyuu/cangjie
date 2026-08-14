#!/bin/bash

# Usage: ./scripts/java/decompose_test.sh <project>
# Example: ./scripts/java/decompose_test.sh Calculator

if [ $# -ne 1 ]; then
  echo "Usage: ./scripts/java/decompose_test.sh <project>"
  exit 1
fi

project="$1"

echo "Decomposing tests for $project"
mkdir -p projects/java/cleaned_final_projects_decomposed_tests/$project
cp -r projects/java/cleaned_final_projects/$project projects/java/cleaned_final_projects_decomposed_tests/
export PYTHONPATH=$(pwd)
python3 -m src.java.preprocessing.decompose_dev_test --project=$project
