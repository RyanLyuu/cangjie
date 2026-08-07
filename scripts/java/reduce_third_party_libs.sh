#!/bin/bash

# Usage: ./scripts/java/reduce_third_party_libs.sh <project>

if [ $# -ne 1 ]; then
  echo "Usage: ./scripts/java/reduce_third_party_libs.sh <project>"
  exit 1
fi

project="$1"

export PYTHONPATH=$(pwd)
python3 -m src.java.preprocessing.reduce_third_party_libs "$project"
