#!/bin/bash

# Usage: ./scripts/java/add_plugin.sh <project_name>

plugin_config=$(cat <<'EOF'
<plugin>
    <groupId>org.apache.maven.plugins</groupId>
    <artifactId>maven-jar-plugin</artifactId>
    <version>3.2.0</version>
    <configuration>
        <excludes>
            <exclude>module-info.class</exclude>
        </excludes>
    </configuration>
    <executions>
        <execution>
            <goals>
                <goal>test-jar</goal>
            </goals>
        </execution>
    </executions>
</plugin>
EOF
)

if [ $# -ne 1 ]; then
    echo "Usage: ./add_plugin.sh <project_name>"
    exit 1
fi

project_name="$1"
original_dir="./projects/java/original_projects/$project_name"
reduced_dir="./projects/java/automated_reduced_projects/$project_name"

if [ ! -d "$original_dir" ]; then
    echo "Error: Project '$project_name' not found in ./projects/java/original_projects/"
    exit 1
fi

mkdir -p "$reduced_dir"
rsync -a --exclude='.git' "$original_dir/" "$reduced_dir"
if [ $? -ne 0 ]; then
    echo "Error: Failed to copy project '$project_name' to $reduced_dir."
    exit 1
fi

cd "$reduced_dir" || exit

if [ ! -f "pom.xml" ]; then
    echo "Error: pom.xml not found in $reduced_dir."
    exit 1
fi

# Check if maven-jar-plugin with test-jar goal already exists
if grep -q "<goal>test-jar</goal>" pom.xml && grep -q "maven-jar-plugin" pom.xml; then
    echo "Plugin maven-jar-plugin with test-jar goal already exists in pom.xml, skipping..."
    exit 0
fi

# Check if <build> tag exists
if grep -q "<build>" pom.xml; then
    # <build> exists, add plugin inside <plugins>
    awk -v config="$plugin_config" '
        BEGIN { in_build = 0 }
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
    # <build> doesn't exist, add it before </project>
    awk -v config="$plugin_config" '
        /<\/project>/ {
            print "    <build>";
            print "        <plugins>";
            print config;
            print "        </plugins>";
            print "    </build>";
            print;
            next
        }
        { print }
    ' pom.xml > pom.xml.new && mv pom.xml.new pom.xml
fi

echo "Plugin configuration added to pom.xml in $reduced_dir"
