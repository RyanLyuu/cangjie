#!/bin/bash

projects=(
    "commons-cli"
    "commons-codec"
    "commons-csv"
    "commons-exec"
    "JavaFastPFOR"
    "commons-fileupload"
    "commons-graph"
    "jansi"
    "commons-pool"
    "commons-validator"
)

projects_dir=projects/java/cleaned_final_projects;
main=$(pwd);

for project in "${projects[@]}"; do
    echo "building $project"
    cd "$projects_dir/$project" || exit
    mvn clean test -Drat.skip -Dmaven.compiler.source=1.8 -Dmaven.compiler.target=1.8
    cd "$main" || exit
done
