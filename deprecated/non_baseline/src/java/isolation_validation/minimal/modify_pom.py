"""修改目标项目的 pom.xml，补齐隔离验证所需依赖、插件和定制配置。"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import os
import shutil

POM_FILE = "pom.xml"

DEPENDENCIES = [
    ("org.junit.jupiter", "junit-jupiter-api", "5.9.3"),
    ("org.junit.jupiter", "junit-jupiter-engine", "5.9.3"),
    ("org.junit.vintage", "junit-vintage-engine", "5.9.3"),
    ("junit", "junit", "4.13.2"),  # LoggingAspect 需要 org.junit.Before/After/Test
    ("org.reflections", "reflections", "0.10.2"),
    ("org.slf4j", "slf4j-api", "2.0.16"),
    ("org.slf4j", "slf4j-simple", "2.0.16"),
    ("org.json", "json", "20240303"),
    ("org.aspectj", "aspectjrt", "1.9.7"),
    ("org.aspectj", "aspectjweaver", "1.9.7"),
]

ASPECTJ_PLUGIN = {
    "groupId": "org.codehaus.mojo",
    "artifactId": "aspectj-maven-plugin",
    "version": "1.14.0",
    "goals": ["compile", "test-compile"],
    "configuration": {
        "complianceLevel": "1.8",
        "source": "1.8",
        "target": "1.8"
    }
}

SPOTLESS_PLUGIN = {
    "groupId": "com.diffplug.spotless",
    "artifactId": "spotless-maven-plugin",
    "version": "2.17.5"
}

def pretty_print(xml_str):
    parsed = minidom.parseString(xml_str)
    pretty_xml = parsed.toprettyxml(indent="  ")
    pretty_xml = re.sub(r"\n\s*\n", "\n", pretty_xml)
    return pretty_xml.strip()

def ensure_element(parent, tag, text=None):
    elem = parent.find(tag)
    if elem is None:
        elem = ET.SubElement(parent, tag)
    if text:
        elem.text = text
    return elem

def modify_pom(pom_file):
    tree = ET.parse(pom_file)
    root = tree.getroot()

    ns = {"maven": "http://maven.apache.org/POM/4.0.0"}
    ET.register_namespace("", ns["maven"])

    dependencies = root.find(".//maven:dependencies", ns)
    if dependencies is None:
        dependencies = ET.SubElement(root, "dependencies")

    existing_deps = set()
    # 记录已有 junit-jupiter aggregate 的版本，用于统一 api/engine 版本
    junit_aggregate_version = None
    for dependency in dependencies.findall("maven:dependency", ns):
        gid = dependency.find("maven:groupId", ns)
        aid = dependency.find("maven:artifactId", ns)
        ver = dependency.find("maven:version", ns)
        if gid is not None and aid is not None:
            existing_deps.add((gid.text.strip(), aid.text.strip()))
            if gid.text.strip() == "org.junit.jupiter" and aid.text.strip() == "junit-jupiter" and ver is not None:
                junit_aggregate_version = ver.text.strip()

    for group_id, artifact_id, version in DEPENDENCIES:
        # junit-jupiter-engine / junit-vintage-engine: 由 aggregate BOM 已覆盖，跳过
        if (group_id, artifact_id) in (
            ("org.junit.jupiter", "junit-jupiter-engine"),
            ("org.junit.vintage", "junit-vintage-engine"),
        ) and ("org.junit.jupiter", "junit-jupiter") in existing_deps:
            continue

        # junit-jupiter-api: LoggingAspect 需要 compile scope，但版本须与 aggregate 一致
        if (group_id, artifact_id) == ("org.junit.jupiter", "junit-jupiter-api") and junit_aggregate_version is not None:
            version = junit_aggregate_version

        found = False
        for dependency in dependencies.findall("maven:dependency", ns):
            gid = dependency.find("maven:groupId", ns)
            aid = dependency.find("maven:artifactId", ns)
            ver = dependency.find("maven:version", ns)
            if gid is not None and aid is not None and gid.text == group_id and aid.text == artifact_id:
                if ver is None:
                    ver = ET.SubElement(dependency, "version")
                ver.text = version
                found = True
                break
        if not found:
            dep = ET.SubElement(dependencies, "dependency")
            ET.SubElement(dep, "groupId").text = group_id
            ET.SubElement(dep, "artifactId").text = artifact_id
            ET.SubElement(dep, "version").text = version

    for dependency in dependencies.findall("maven:dependency", ns):
        gid = dependency.find("maven:groupId", ns)
        aid = dependency.find("maven:artifactId", ns)
        ver = dependency.find("maven:version", ns)

        if gid is not None and aid is not None and gid.text == "info.picocli" and aid.text == "picocli-codegen":
            dependencies.remove(dependency)

        if gid is not None and aid is not None and ver is not None:
            if gid.text == "junit" and aid.text == "junit" and ver.text.strip() == "4.10":
                ver.text = "4.13"

        deps_to_clear_scope = {(g, a) for g, a, _ in DEPENDENCIES}
        deps_to_clear_scope.add(("junit", "junit"))  # explicitly add JUnit 4

        if gid is not None and aid is not None and (gid.text, aid.text) in deps_to_clear_scope:
            scope = dependency.find("maven:scope", ns)
            if scope is not None and scope.text.strip() == "test":
                dependency.remove(scope)


    build = root.find(".//maven:build", ns)
    if build is None:
        build = ET.SubElement(root, "build")

    plugins = build.find("maven:plugins", ns)
    if plugins is None:
        plugins = ET.SubElement(build, "plugins")

    found_aspectj = False
    for plugin in plugins.findall("maven:plugin", ns):
        gid = plugin.find("maven:groupId", ns)
        aid = plugin.find("maven:artifactId", ns)

        if gid is None or aid is None:
            continue

        if gid.text == "org.apache.maven.plugins" and aid.text == "maven-compiler-plugin":
            configuration = plugin.find("maven:configuration", ns)
            if configuration is not None:
                release = configuration.find("maven:release", ns)
                if release is not None:
                    release_value = release.text
                    configuration.remove(release)
                    ET.SubElement(configuration, "source").text = release_value
                    ET.SubElement(configuration, "target").text = release_value

        if gid.text == ASPECTJ_PLUGIN["groupId"] and aid.text == ASPECTJ_PLUGIN["artifactId"]:
            ensure_element(plugin, "version", ASPECTJ_PLUGIN["version"])
            execution_elem = ensure_element(plugin, "executions")
            execution_elem.clear()
            execution = ET.SubElement(execution_elem, "execution")
            goals_elem = ET.SubElement(execution, "goals")
            for goal in ASPECTJ_PLUGIN["goals"]:
                ET.SubElement(goals_elem, "goal").text = goal
            config_elem = ensure_element(plugin, "configuration")
            config_elem.clear()
            for key, value in ASPECTJ_PLUGIN["configuration"].items():
                ET.SubElement(config_elem, key).text = value
            found_aspectj = True

        if gid.text == SPOTLESS_PLUGIN["groupId"] and aid.text == SPOTLESS_PLUGIN["artifactId"]:
            version_elem = plugin.find("maven:version", ns)
            if version_elem is not None:
                version_elem.text = SPOTLESS_PLUGIN["version"]
            else:
                version_elem = ET.Element("version")
                version_elem.text = SPOTLESS_PLUGIN["version"]
                plugin.insert(2, version_elem)

            configuration = plugin.find("maven:configuration", ns)
            if configuration is not None:
                java_elem = configuration.find("maven:java", ns)
                if java_elem is not None:
                    palantir_elem = java_elem.find("maven:palantirJavaFormat", ns)
                    if palantir_elem is not None:
                        java_elem.remove(palantir_elem)
        
        if gid is not None and aid is not None and gid.text == "org.codehaus.mojo" and aid.text == "exec-maven-plugin":
            plugins_elem = root.find(".//maven:build/maven:plugins", ns)
            if plugins_elem is not None:
                for plugin in plugins_elem.findall("maven:plugin", ns):
                    plugin_gid = plugin.find("maven:groupId", ns)
                    plugin_aid = plugin.find("maven:artifactId", ns)
                    if plugin_gid is not None and plugin_aid is not None:
                        if plugin_gid.text == "org.codehaus.mojo" and plugin_aid.text == "exec-maven-plugin":
                            plugins_elem.remove(plugin)
                            break


    if not found_aspectj:
        plugin = ET.SubElement(plugins, "plugin")
        ET.SubElement(plugin, "groupId").text = ASPECTJ_PLUGIN["groupId"]
        ET.SubElement(plugin, "artifactId").text = ASPECTJ_PLUGIN["artifactId"]
        ET.SubElement(plugin, "version").text = ASPECTJ_PLUGIN["version"]

        execution_elem = ET.SubElement(plugin, "executions")
        execution = ET.SubElement(execution_elem, "execution")
        goals_elem = ET.SubElement(execution, "goals")
        for goal in ASPECTJ_PLUGIN["goals"]:
            ET.SubElement(goals_elem, "goal").text = goal

        config_elem = ET.SubElement(plugin, "configuration")
        for key, value in ASPECTJ_PLUGIN["configuration"].items():
            ET.SubElement(config_elem, key).text = value

    xml_str = ET.tostring(root, encoding="utf-8")
    pretty_xml = pretty_print(xml_str.decode("utf-8"))

    with open(pom_file, "w", encoding="utf-8") as f:
        f.write(pretty_xml)


def rename_tests_and_update_fastpfor():
    TEST_DIR = "src/test"
    VECTOR_DIR = "src/main/java/me/lemire/integercompression/vector"
    MODULE_INFO = "src/main/java/module-info.java"

    if os.path.isdir(VECTOR_DIR):
        print(f"Removing directory: {VECTOR_DIR}")
        shutil.rmtree(VECTOR_DIR)

    if os.path.isfile(MODULE_INFO):
        print(f"Removing file: {MODULE_INFO}")
        os.remove(MODULE_INFO)

    replacements = []

    for root, dirs, files in os.walk(TEST_DIR):
        for filename in files:
            match = re.match(r'Test([A-Z].*)\.java$', filename)
            if match:
                base = match.group(1)
                old_name = f"Test{base}"
                new_name = f"{base}Test"
                old_path = os.path.join(root, f"{old_name}.java")
                new_path = os.path.join(root, f"{new_name}.java")
                print(f"Renaming {old_path} → {new_path}")
                os.rename(old_path, new_path)

                with open(new_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = re.sub(rf'\bclass\s+{old_name}\b', f'class {new_name}', content)
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(content)

                replacements.append((old_name, new_name))

    for root, dirs, files in os.walk(TEST_DIR):
        for filename in files:
            if filename.endswith(".java"):
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                original = content
                for old, new in replacements:
                    content = re.sub(rf'\b{old}\b', new, content)
                if content != original:
                    print(f"Updating references in {path}")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)



def rename_tests_and_update_pool2():
    TEST_DIR = "src/test"
    POM_FILE = "pom.xml"
    FILE_TO_DELETE = "src/test/java/org/apache/commons/pool2/impl/CallStackTest.java"
    replacements = []

    for root, dirs, files in os.walk(TEST_DIR):
        for filename in files:
            match = re.match(r'Test([A-Z].*)\.java$', filename)
            if match:
                base = match.group(1)
                old_name = f"Test{base}"
                new_name = f"{base}Test"
                old_path = os.path.join(root, f"{old_name}.java")
                new_path = os.path.join(root, f"{new_name}.java")
                print(f"Renaming {old_path} → {new_path}")
                os.rename(old_path, new_path)

                with open(new_path, "r", encoding="utf-8") as f:
                    content = f.read()
                content = re.sub(rf'\bclass\s+{old_name}\b', f'class {new_name}', content)
                with open(new_path, "w", encoding="utf-8") as f:
                    f.write(content)

                replacements.append((old_name, new_name))

    for root, dirs, files in os.walk(TEST_DIR):
        for filename in files:
            if filename.endswith(".java"):
                path = os.path.join(root, filename)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                original = content
                for old, new in replacements:
                    content = re.sub(rf'\b{old}\b', new, content)
                if content != original:
                    print(f"Updating references in {path}")
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)

    tree = ET.parse(POM_FILE)
    root = tree.getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    ET.register_namespace('', ns['m'])
    surefire = root.find(".//m:plugin[m:artifactId='maven-surefire-plugin']", ns)
    if surefire is not None:
        config = surefire.find("m:configuration", ns)
        if config is None:
            config = ET.SubElement(surefire, "configuration")

        config.insert(0, ET.Comment(" Don't allow test to run for more than 30 minutes "))

        includes = config.find("m:includes", ns)
        if includes is not None:
            config.remove(includes)
        includes = ET.SubElement(config, "includes")
        ET.SubElement(includes, "include").text = "**/*Test.java"

        excludes = config.find("m:excludes", ns)
        if excludes is not None:
            config.remove(excludes)
        excludes = ET.SubElement(config, "excludes")
        excludes.append(ET.Comment(" nested classes are not handled properly by Surefire "))
        ET.SubElement(excludes, "exclude").text = "**/*Test$*.java"
        excludes.append(ET.Comment(" Don't run this test by default - it uses lots of memory "))
        ET.SubElement(excludes, "exclude").text = "**/SoftRefOutOfMemoryTest.java"

        tree.write(POM_FILE, encoding="utf-8", xml_declaration=True)
        print(f"Updated {POM_FILE}")
    else:
        print("Surefire plugin not found in pom.xml")

    if os.path.exists(FILE_TO_DELETE):
        print(f"Deleting {FILE_TO_DELETE}")
        os.remove(FILE_TO_DELETE)
    else:
        print(f"{FILE_TO_DELETE} not found; skipping.")

def update_exec():
    exec_dir = "src/test/java/org/apache/commons/exec"
    for root, _, files in os.walk(exec_dir):
        for file in files:
            if file.endswith(".java"):
                full_path = os.path.join(root, file)
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
                new_content = re.sub(r"@Timeout\s*\(\s*[^)]*\)", "", content)
                if new_content != content:
                    print(f"Removing @Timeout from {full_path}")
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

def update_jansi():
    POM_FILE = "pom.xml"
    tree = ET.parse(POM_FILE)
    root = tree.getroot()
    ns = {'m': 'http://maven.apache.org/POM/4.0.0'}
    ET.register_namespace('', ns['m'])

    build = root.find("m:build", ns)
    if build is None:
        print("No <build> section in pom.xml")
        return

    plugins = build.find("m:plugins", ns)
    if plugins is None:
        print("No <plugins> section in pom.xml")
        return

    to_remove = [
        ("org.apache.maven.plugins", "maven-javadoc-plugin"),
        ("org.moditect", "moditect-maven-plugin"),
    ]

    removed_any = False
    for plugin in plugins.findall("m:plugin", ns):
        gid = plugin.find("m:groupId", ns)
        aid = plugin.find("m:artifactId", ns)

        if gid is not None and aid is not None:
            for target_gid, target_aid in to_remove:
                if gid.text.strip() == target_gid and aid.text.strip() == target_aid:
                    print(f"Removing plugin: {target_gid}:{target_aid}")
                    plugins.remove(plugin)
                    removed_any = True
                    break

    if removed_any:
        tree.write(POM_FILE, encoding="utf-8", xml_declaration=True)
        print("Updated pom.xml successfully (removed Javadoc and Moditect plugins).")
    else:
        print("No matching plugins found to remove.")

if __name__ == "__main__":
    modify_pom(POM_FILE)
    print("pom.xml has been updated successfully.")
    pool2_path = "src/main/java/org/apache/commons/pool2/"
    if os.path.isdir(pool2_path):
        rename_tests_and_update_pool2()  # refactor pool2 to support AspectJ
    fastpfor_path = "src/main/java/me/lemire/"
    if os.path.isdir(fastpfor_path):
        rename_tests_and_update_fastpfor()  # refactor fastpfor to support AspectJ
    exec_path = "src/main/java/org/apache/commons/exec/"
    if os.path.isdir(exec_path):
        update_exec()  # refactor exec to support AspectJ
    jansi_path = "src/main/java/org/fusesource/jansi"
    if os.path.isdir(jansi_path):
        update_jansi()
