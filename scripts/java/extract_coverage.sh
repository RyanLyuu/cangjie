#!/bin/bash

# Usage: ./scripts/java/extract_coverage.sh <project> <suffix>

if [ $# -ne 2 ]; then
  echo "Usage: ./scripts/java/extract_coverage.sh <project> <suffix>"
  exit 1
fi

project=$1
suffix=$2

# Get the project root directory (assumes script is run from project root)
project_root="$(pwd)"
project_dir="$project_root/projects/java/cleaned_final_projects${suffix}/$project"

jacoco_plugin=$(cat <<'EOF'
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.10</version>
    <executions>
        <execution>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>test</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
    </executions>
</plugin>
EOF
)

if [ ! -d "$project_dir" ]; then
    echo "Error: Project '$project' not found in $project_dir."
    exit 1
fi

cd "$project_dir" || exit

if [ ! -f "pom.xml" ]; then
    echo "Error: pom.xml not found in $project_dir."
    exit 1
fi

# Check if jacoco plugin already exists
if grep -q "jacoco-maven-plugin" pom.xml; then
    echo "JaCoCo plugin already exists in pom.xml"
else
    # Check if <build> section exists
    if grep -q "<build>" pom.xml; then
        awk -v config="$jacoco_plugin" '
            /<build>/ { in_build = 1 }
            /<\/build>/ { in_build = 0 }
            in_build && /<plugins>/ {
                print;
                print config;
                next
            }
            { print }
        ' pom.xml > pom.xml.new && mv pom.xml.new pom.xml
    else
        # Add <build> section with plugins containing jacoco
        awk -v config="$jacoco_plugin" '
            /<\/dependencies>/ {
                print
                print "    <build>"
                print "        <plugins>"
                print config
                print "        </plugins>"
                print "    </build>"
                next
            }
            { print }
        ' pom.xml > pom.xml.new && mv pom.xml.new pom.xml
    fi
    echo "JaCoCo plugin added to pom.xml"
fi

echo "Running mvn clean test -Drat.skip=true..."
mvn clean test -Drat.skip=true

cd - > /dev/null || exit

# Change back to project root directory
cd "$project_root" || exit

echo "extracting test coverage for $project"
export PYTHONPATH=$(pwd)
python3 -m src.java.static_analysis.extract_source_tests --project=$project --suffix=$suffix
