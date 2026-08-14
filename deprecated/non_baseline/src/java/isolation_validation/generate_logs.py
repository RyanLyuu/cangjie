#!/usr/bin/env python3
"""为 java2cangjie isolated validation 流程批量生成日志并落盘仓颉测试。

和原版 `generate_logs.py` 的职责相同：
1. 准备 Java 项目副本；
2. 运行单测生成日志；
3. 对每个 `.log` 调用 java2cangjie 版本的 emitter；
4. 把输出放到 `<project>-cangjie/` 工作目录中。

与原版相比，这里不再生成 Python mock 测试，而是：
- 使用 `script.py` 把日志转换成 `.cj` + `.workflow.json`。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired
from typing import Union


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, check: bool = True) -> None:
    echo = " ".join(str(c) for c in cmd)
    print(f"+ {echo}" if cwd is None else f"+ (cd {cwd}) {echo}")
    subprocess.run(cmd, cwd=cwd, env=env, check=check)


def run_cmd(
    test_class: str,
    test_method: Union[str, Path],
    project: Path,
    *,
    timeout: int = 100,
) -> None:
    cwd = project
    cmd = [
        str(Path(__file__).parent / "run_maven.sh"),
        test_class,
        str(test_method),
    ]
    print(f"Running command: {cmd}")

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
    )

    try:
        proc.wait(timeout=timeout)
    except TimeoutExpired:
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            proc.wait()
        raise

    if proc.returncode != 0:
        raise CalledProcessError(proc.returncode, cmd)


def run_emitter(log_file: Path, workdir: Path, script_name: str, timeout: int, output_dir: Path | None = None) -> None:
    cmd = [sys.executable, script_name, log_file.name]
    if output_dir is not None:
        cmd += ["--output-dir", str(output_dir)]
    print(f"Running emitter: {cmd} (cwd={workdir})")
    subprocess.run(cmd, cwd=workdir, timeout=timeout, check=True)


def ensure_sdk(java_version: str = "8.0.432-kona") -> None:
    sdkman_dir = Path.home() / ".sdkman"
    java_candidate = sdkman_dir / "candidates" / "java" / java_version
    if not java_candidate.exists():
        sys.stderr.write(
            f"⚠️  Could not find SDKMAN java candidate at {java_candidate}\n"
            "   Is that version installed? Try `sdk list java`.\n"
        )
        sys.exit(1)

    os.environ["JAVA_HOME"] = str(java_candidate)
    os.environ["PATH"] = str(java_candidate / "bin") + os.pathsep + os.environ.get("PATH", "")


def copy_project_tree(project: str) -> None:
    src = Path("../../java_projects/cleaned_final_projects") / project
    dst = Path(project)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def save_state(project: str, executed_tests: dict[str, object], json_dir: Path) -> None:
    path = json_dir / f"{project}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(executed_tests, f, indent=4, ensure_ascii=False)


def copy_emitter_bundle(target_dir: Path, *, emitter_script: str) -> None:
    this_dir = Path(__file__).parent
    shutil.copy(this_dir / emitter_script, target_dir / emitter_script)
    shutil.copy(this_dir / "mock_helper.py", target_dir / "mock_helper.py")
    shutil.copy(this_dir / "log_parser.py", target_dir / "log_parser.py")
    shutil.copy(this_dir / "reflection.py", target_dir / "reflection.py")
    shutil.copy(this_dir / "add_macro.py", target_dir / "add_macro.py")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Cangjie replay tests from isolated-validation logs.")
    parser.add_argument("project", help="Project directory name")
    parser.add_argument("timeout", type=int, default=100, help="Timeout for each test method")
    parser.add_argument("json_fname", help="Directory containing executed-tests JSON files")
    parser.add_argument("mock_evosuite", type=bool, default=False, help="Kept for compatibility; currently unused")
    parser.add_argument("--emitter-script", default="script.py", help="Python emitter that converts one log to Cangjie tests")
    parser.add_argument("--output-suffix", default="-cangjie", help="Suffix of the per-project work directory")
    args = parser.parse_args()

    project = args.project
    json_dir = Path(args.json_fname)
    state_path = json_dir / f"{project}.json"

    ensure_sdk("8.0.432-kona")
    copy_project_tree(project)

    run([sys.executable, "clean_evosuite_tests.py", f"../../java_projects/cleaned_final_projects_evosuite/{project}", project])
    cleaned_base = Path("../../java_projects/cleaned_final_projects_evosuite_cleaned")
    cleaned_base.mkdir(parents=True, exist_ok=True)
    src_dir = Path(project)
    dst_dir = cleaned_base / project
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    shutil.copy("modify_pom.py", src_dir)
    run([sys.executable, "modify_pom.py"], cwd=src_dir)
    shutil.copy("remove_benchmark.py", src_dir)
    run([sys.executable, "remove_benchmark.py"], cwd=src_dir)
    shutil.copytree(src_dir, dst_dir)
    run([
        "mvn", "clean", "install", "-Drat.skip", "-Dgpg.skip", "-Dmoditect.skip",
        "-Dcheckstyle.skip", "-Dmaven.javadoc.skip"
    ], cwd=src_dir, check=False)
    run([sys.executable, "extract_executed_tests.py", str(src_dir)])
    executed_tests: dict[str, dict[str, dict[str, object]]] = json.loads(state_path.read_text(encoding="utf-8"))

    for helper in ("modify_pom.py", "add_java_files.py"):
        shutil.copy(helper, project)
    run([sys.executable, "add_java_files.py"], cwd=src_dir)

    for p in src_dir.glob("*.log"):
        p.unlink()

    cangjie_dir = Path(f"{project}{args.output_suffix}")
    cangjie_dir.mkdir(exist_ok=True)
    copy_emitter_bundle(cangjie_dir, emitter_script=args.emitter_script)

    # 仓颉端测试输出目录：<cangjie_root>/projects/cangjie/original_projects/<project>/src/test
    cangjie_root = Path(__file__).parent.parent.parent
    cj_test_output = cangjie_root / "projects" / "cangjie" / "original_projects" / project / "src" / "test"

    # 把仓颉项目的 cjpm.toml 复制进 emitter 目录，使 detect_project_name 得到正确包名
    cjpm_src = cangjie_root / "projects" / "cangjie" / "original_projects" / project / "cjpm.toml"
    if cjpm_src.exists():
        shutil.copy(cjpm_src, cangjie_dir / "cjpm.toml")

    for test_class, methods in executed_tests.items():
        for test_method, info in methods.items():
            info.setdefault("mocked", False)
            info.setdefault("timeout", False)
            info.setdefault("mock_duration", None)

            if info["mocked"] or info["timeout"]:
                continue

            start = time.time()
            parts = test_class.split(".")
            if parts and parts[-1].startswith("Test"):
                parts[-1] = parts[-1][4:] + "Test"
            actual_class = ".".join(parts)

            try:
                run_cmd(actual_class, test_method, src_dir, timeout=args.timeout)
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                info["timeout"] = True
                info["mock_duration"] = time.time() - start
                save_state(project, executed_tests, json_dir)
                for p in src_dir.glob("*.log"):
                    p.unlink()
                continue

            # 拷贝日志到仓颉工作区
            for log_path in src_dir.glob("*.log"):
                shutil.copy(log_path, cangjie_dir / log_path.name)

            # 针对每个日志生成仓颉测试
            for log_file in cangjie_dir.glob("*.log"):
                try:
                    run_emitter(log_file, cangjie_dir, args.emitter_script, args.timeout, output_dir=cj_test_output)
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                    pass

            # 清理日志，但保留生成的 .cj / .workflow.json
            for p in cangjie_dir.glob("*.log"):
                p.unlink()
            for p in src_dir.glob("*.log"):
                p.unlink()

            info["mocked"] = True
            info["mock_duration"] = time.time() - start
            save_state(project, executed_tests, json_dir)


if __name__ == "__main__":
    main()
