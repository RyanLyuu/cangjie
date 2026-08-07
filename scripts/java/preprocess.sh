#!/bin/bash

# ./scripts/java/preprocess.sh commons-cli
# ./scripts/java/preprocess.sh commons-codec
# ./scripts/java/preprocess.sh commons-csv
# ./scripts/java/preprocess.sh commons-exec
# ./scripts/java/preprocess.sh JavaFastPFOR
# ./scripts/java/preprocess.sh commons-fileupload
# ./scripts/java/preprocess.sh commons-graph
# ./scripts/java/preprocess.sh jansi
# ./scripts/java/preprocess.sh commons-pool
# ./scripts/java/preprocess.sh commons-validator

if [ $# -ne 1 ]; then
  echo "Usage: ./scripts/java/preprocess.sh <project>"
  exit 1
fi

project="$1"

./scripts/java/add_plugin.sh $project  || { echo "add_plugin failed"; exit 1; }
./scripts/java/handle_keyword_conflicts.sh $project  || { echo "handle_keyword_conflicts failed"; exit 1; }
./scripts/java/handle_name_conflicts.sh $project  || { echo "handle_name_conflicts failed"; exit 1; }
./scripts/java/merge_jar.sh $project  || { echo "merge_jar failed"; exit 1; }
./scripts/java/generate_cg.sh $project  || { echo "generate_cg failed"; exit 1; }
./scripts/java/reduce_third_party_libs.sh $project  || { echo "reduce_third_party_libs failed"; exit 1; }

rm -rf "projects/java/cleaned_final_projects/$project"
mkdir -p "projects/java/cleaned_final_projects"
cp -r "projects/java/name_handled/$project" "projects/java/cleaned_final_projects/$project"  || { echo "copy cleaned_final project failed"; exit 1; }
