import os
import argparse
import re
import json
import shutil
import subprocess
from collections import defaultdict, deque
from pathlib import Path

from src.java.utils.project_paths import resolve_java_project_root


REPO_ROOT = Path(__file__).resolve().parents[3]


def ensure_compiled_classes(
    project_dir, maven_executable="mvn", compile_timeout=900
):
    """Compile a checked-in cleaned project when ignored Maven outputs are absent."""
    project_dir = Path(project_dir)
    classes_dir = project_dir / "target/classes"
    if classes_dir.is_dir():
        return False

    pom = project_dir / "pom.xml"
    if not pom.is_file():
        raise FileNotFoundError(f"Maven project file not found: {pom}")
    maven = shutil.which(maven_executable) or (
        maven_executable if Path(maven_executable).is_file() else ""
    )
    if not maven:
        raise RuntimeError(
            f"Maven executable not found: {maven_executable}; install Maven or pass --maven"
        )

    command = [
        maven,
        "-q",
        "-DskipTests",
        "-Drat.skip",
        "-Dcheckstyle.skip",
        "-Dspotbugs.skip",
        "-Djapicmp.skip",
        "-Dmaven.javadoc.skip=true",
        "compile",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=compile_timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"Maven compile timed out after {compile_timeout}s: {project_dir}"
        ) from exc
    if completed.returncode != 0:
        diagnostic = "\n".join(
            part.strip() for part in (completed.stdout, completed.stderr) if part.strip()
        )
        raise RuntimeError(
            f"Maven compile failed for {project_dir}:\n{diagnostic[-8000:]}"
        )
    if not classes_dir.is_dir():
        raise RuntimeError(
            f"Maven compile succeeded but did not create {classes_dir}"
        )
    return True


def detect_and_remove_cycles(graph):
    # Calculate in-degrees of all nodes
    in_degree = defaultdict(int)
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1

    # Initialize a queue with nodes having zero in-degree
    queue = deque([node for node in graph if in_degree[node] == 0])

    topological_order = []
    while queue:
        current = queue.popleft()
        topological_order.append(current)

        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Check for cycles
    if len(topological_order) != len(graph):
        # There is a cycle; remove one edge from each cycle
        remaining_nodes = set(graph.keys()) - set(topological_order)
        for node in remaining_nodes:
            for neighbor in graph[node]:
                if neighbor in remaining_nodes:
                    graph[node].remove(neighbor)
                    return detect_and_remove_cycles(graph)

    topological_order.reverse()
    return topological_order


def parse_dependencies(
    project_name,
    suffix,
    project_root="",
    jdeps_executable="jdeps",
    maven_executable="mvn",
    compile_timeout=900,
):
    dependencies_dir = REPO_ROOT / f"data/java/dependencies{suffix}" / project_name
    dependencies_dir.mkdir(parents=True, exist_ok=True)

    project_dir = resolve_java_project_root(project_name, suffix, project_root)

    class_dependencies = {}
    java_files = []
    for root, dirs, files in os.walk(project_dir / "src"):
        for file in files:
            if file.endswith(".java"):
                java_files.append(os.path.join(root, file))

    for dot_class_file in java_files:
        class_name = dot_class_file.split("/")[-1].split(".")[0]
        class_dependencies.setdefault(class_name, [])

    jdeps = shutil.which(jdeps_executable)
    if not jdeps:
        raise RuntimeError(
            f"jdeps executable not found: {jdeps_executable}; install a JDK or pass --jdeps"
        )
    ensure_compiled_classes(project_dir, maven_executable, compile_timeout)
    main_classes_dir = project_dir / "target/classes"
    subprocess.run(
        [jdeps, "-verbose", "-dotoutput", str(dependencies_dir), str(main_classes_dir)],
        check=True,
    )
    test_classes_dir = project_dir / "target/test-classes"
    if test_classes_dir.exists():
        subprocess.run(
            [jdeps, "-verbose", "-dotoutput", str(dependencies_dir), str(test_classes_dir)],
            check=True,
        )
    summary_path = dependencies_dir / "summary.dot"
    if summary_path.exists():
        summary_path.unlink()

    class_deps = os.listdir(dependencies_dir)
    for class_dep in class_deps:

        if not class_dep.endswith(".dot"):
            continue

        with open(dependencies_dir / class_dep, "r") as f:
            lines = f.readlines()
            for line in lines[2:-1]:

                candidate_line = line.strip()
                if (
                    "java.base" in candidate_line
                    or "java" in candidate_line
                    or "junit" in candidate_line
                ):
                    continue

                class_name_path = (
                    re.search(r"->\s(.*?)\s\(", candidate_line)
                    .group(1)
                    .replace('"', "")
                    .strip()
                )
                class_name = class_name_path.split(".")[-1].strip()

                current_class_path = candidate_line[
                    candidate_line.find('"')
                    + 1 : candidate_line.find('"', candidate_line.find('"') + 1)
                ]
                current_class = current_class_path.split(".")[-1].strip()

                if "$" in class_name:
                    if class_name.split("$")[-1].isdigit():
                        class_name = class_name.split("$")[0]
                        class_dependencies.setdefault(class_name, [])
                    else:
                        class_name = class_name.split("$")[0]
                        class_dependencies.setdefault(class_name, [])

                if "$" in current_class:
                    if current_class.split("$")[-1].isdigit():
                        current_class = current_class.split("$")[0]
                        class_dependencies.setdefault(current_class, [])
                    else:
                        current_class = current_class.split("$")[0]
                        class_dependencies.setdefault(current_class, [])

                class_dependencies.setdefault(class_name, [])
                class_dependencies.setdefault(current_class, [])

                if class_name == current_class:
                    continue

                if class_name in class_dependencies[current_class]:
                    continue

                if (class_name, class_name_path.split("$")[0]) in class_dependencies[
                    current_class
                ]:
                    continue

                class_dependencies[current_class].append(
                    (class_name, class_name_path.split("$")[0])
                )

    with open(dependencies_dir / "dependencies.json", "w") as f:
        json.dump(class_dependencies, f, indent=4)

    adjacency_list = defaultdict(list)
    for key, value in class_dependencies.items():
        adjacency_list[key] = []
        for pair in value:
            adjacency_list[key].append(pair[0])

    topological_order = detect_and_remove_cycles(adjacency_list)
    traversal_order = [
        class_name
        for class_name in topological_order
        if class_name not in ["package-info", "module-info"]
        and class_name in class_dependencies
    ]
    traversal = {i: class_name for i, class_name in enumerate(traversal_order)}

    with open(dependencies_dir / "traversal.json", "w") as f:
        json.dump(traversal, f, indent=4)


def main(args):
    function_name = args.function
    if function_name == "parse_dependencies":
        parse_dependencies(
            args.project_name,
            args.suffix,
            args.project_root,
            args.jdeps,
            args.maven,
            args.compile_timeout,
        )
    else:
        raise NotImplementedError(f"function {function_name} not implemented")


def parse_args():
    parser = argparse.ArgumentParser("utilities")
    parser.add_argument(
        "--project_name",
        type=str,
        default="java_projects",
        help="project name",
        required=True,
    )
    parser.add_argument(
        "--function",
        type=str,
        default="parse_dependencies",
        help="function name in utility",
        required=True,
    )
    parser.add_argument(
        "--suffix", type=str, default="", help="suffix for output files"
    )
    parser.add_argument(
        "--project_root", type=str, default="",
        help="root containing the preprocessed project (optional)",
    )
    parser.add_argument(
        "--jdeps", type=str, default="jdeps", help="jdeps executable path"
    )
    parser.add_argument(
        "--maven", type=str, default="mvn", help="Maven executable path"
    )
    parser.add_argument(
        "--compile-timeout", type=int, default=900,
        help="automatic Maven compile timeout in seconds",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        main(args)
    except (FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        raise SystemExit(str(exc)) from exc
