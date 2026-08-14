"""Java 端 mock 日志一次性采集 → /tmp/cangjie_mock/<project>/。

行为对应原 mock.sh，但：
  - 直接对 `projects/java/cleaned_final_projects/<project>/` 原地修改（用户已确认 #不开副本）；
  - 自动枚举所有 `*Test.java` 中带 `@Test` 的方法（不再硬编码 AppTest）；
  - 缓存：staging 目录里只要存在 `*_test.cj` 就视为已生成、直接复用。

modify_pom.py + add_java_files.py 必须在此处执行（主流程其余阶段并不会跑它们）。
为了不破坏 add_java_files.py 中 `SOURCE_FILES = ["../LoggingAspect.java", ...]` 的相对路径，
临时把这两个 Java 文件拷到 `cleaned_final_projects/` 下，结束时清理。
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import script as _emitter  # type: ignore  # noqa: E402  emitter 自己依赖同级 helpers


_TEST_METHOD_RE = re.compile(
    r"@Test\b[^@{};]*?(?:public\s+|protected\s+|private\s+|static\s+)*\s*"
    r"(?:[\w<>\[\],\s?]+?\s+)?(\w+)\s*\(",
    flags=re.DOTALL,
)
_PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", flags=re.MULTILINE)
_TEST_CLASS_SUFFIXES = ("Test", "Tests", "IT", "ITCase")


def _java_project(project: str) -> Path:
    java_proj = Path("projects/java/cleaned_final_projects") / project
    if not java_proj.is_dir():
        raise FileNotFoundError(
            f"Java project not found at '{java_proj}'. "
            f"Run scripts/java/build_original_projects.sh first, or check project name."
        )
    return java_proj


def _read_cangjie_project_name(cj_project_root: Path) -> str:
    cjpm = cj_project_root / "cjpm.toml"
    if not cjpm.is_file():
        raise FileNotFoundError(f"cjpm.toml missing at {cjpm}")
    text = cjpm.read_text(encoding="utf-8")
    m = re.search(r'^\s*name\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if not m:
        raise RuntimeError(f"failed to extract package name from {cjpm}")
    return m.group(1).strip()


def _enumerate_tests(java_project: Path) -> list[tuple[str, str]]:
    """返回 [(FQCN, methodName)]，跨整个 src/test/java 枚举所有 @Test。"""
    test_root = java_project / "src" / "test" / "java"
    if not test_root.is_dir():
        return []

    pairs: list[tuple[str, str]] = []
    for java_file in sorted(test_root.rglob("*.java")):
        if not any(java_file.stem.endswith(suf) for suf in _TEST_CLASS_SUFFIXES):
            continue
        text = java_file.read_text(encoding="utf-8", errors="ignore")
        pkg_m = _PACKAGE_RE.search(text)
        package = pkg_m.group(1) if pkg_m else ""
        fqcn = f"{package}.{java_file.stem}" if package else java_file.stem
        for m in _TEST_METHOD_RE.finditer(text):
            pairs.append((fqcn, m.group(1)))
    return pairs


def _setup_aspectj(java_project: Path) -> None:
    """在 cleaned_final_projects/<P>/ 上原地跑 modify_pom.py + add_java_files.py。

    对应原 mock.sh 第 2 步。两个脚本都是幂等的：
      - modify_pom.py 在添加依赖前会先检查；
      - add_java_files.py 单纯覆盖拷贝。
    """
    parent = java_project.parent
    aspect_temps: list[Path] = []
    for src_name in ("LoggingAspect.java", "CustomToStringConverter.java"):
        src = _THIS_DIR / src_name
        if not src.is_file():
            raise FileNotFoundError(f"Missing aspect source: {src}")
        target = parent / src_name
        shutil.copy2(src, target)
        aspect_temps.append(target)

    try:
        subprocess.run(
            ["python3", str(_THIS_DIR / "modify_pom.py")],
            cwd=java_project,
            check=True,
        )
        subprocess.run(
            ["python3", str(_THIS_DIR / "add_java_files.py")],
            cwd=java_project,
            check=True,
        )
    finally:
        for tmp in aspect_temps:
            if tmp.is_file():
                tmp.unlink()


def _run_one_mvn_test(java_project: Path, fqcn: str, method: str) -> bool:
    cmd = [
        "mvn", "clean", "install",
        "-Drat.skip", "-Dgpg.skip", "-Dmaven.javadoc.skip",
        f"-Dtest={fqcn}#{method}",
        "-q",
    ]
    try:
        result = subprocess.run(cmd, cwd=java_project, capture_output=True, text=True)
    except FileNotFoundError:
        raise RuntimeError("mvn not found in PATH; install Maven before running mock setup.")
    if result.returncode != 0:
        for log in java_project.glob("*.log"):
            log.unlink()
        return False
    return True


def _emit_logs(java_project: Path, staging: Path, project_name: str) -> int:
    """消费 `cleaned_final_projects/<P>/*.log`，emit `_test.cj` + `.workflow.json` 到 staging。"""
    emitted = 0
    for log in sorted(java_project.glob("*.log")):
        try:
            generated = _emitter.process_test_log(
                str(log),
                output_dir=staging,
                project_name=project_name,
            )
            emitted += sum(1 for p in generated if p.name.endswith("_test.cj"))
        finally:
            try:
                log.unlink()
            except OSError:
                pass
    return emitted


def staging_dir_for(project: str) -> Path:
    return Path("/tmp/cangjie_mock") / project


def staging_is_populated(project: str) -> bool:
    staging = staging_dir_for(project)
    return staging.is_dir() and any(staging.glob("*_test.cj"))


def ensure_java_mock_logs(project: str, cj_project_root: Path) -> Path:
    """主流程入口。如果 staging 已有内容则直接返回；否则跑全流程并返回 staging Path。

    Raises:
        FileNotFoundError: cleaned_final_projects/<P> 缺失。
        RuntimeError:      mvn 一个测试都没采集到 / aspectj 注入失败 / cjpm.toml 缺失。
    """
    staging = staging_dir_for(project)

    if staging_is_populated(project):
        print(f"[mock] reusing cached staging at {staging}")
        return staging

    java_project = _java_project(project)  # raises if missing
    project_name = _read_cangjie_project_name(cj_project_root)

    staging.mkdir(parents=True, exist_ok=True)

    print(f"[mock] preparing AspectJ instrumentation in {java_project} (in-place)")
    _setup_aspectj(java_project)

    test_pairs = _enumerate_tests(java_project)
    if not test_pairs:
        raise RuntimeError(
            f"No JUnit @Test methods discovered under {java_project}/src/test/java; "
            f"cannot proceed with mock setup."
        )

    print(f"[mock] running {len(test_pairs)} test method(s) under mvn to capture logs")
    total_emitted = 0
    skipped = 0
    for fqcn, method in test_pairs:
        ok = _run_one_mvn_test(java_project, fqcn, method)
        if not ok:
            skipped += 1
            continue
        total_emitted += _emit_logs(java_project, staging, project_name)

    if total_emitted == 0:
        raise RuntimeError(
            f"mvn ran {len(test_pairs)} tests for project '{project}' but emitted 0 mock samples; "
            f"check AspectJ instrumentation / pom modifications / Java compile errors."
        )

    print(f"[mock] staged {total_emitted} _test.cj files at {staging} "
          f"(skipped {skipped} mvn-failed tests)")
    return staging


def _cli() -> None:
    import argparse
    parser = argparse.ArgumentParser(
        description="Generate mock test samples by running Java JUnit tests with AspectJ logging.",
    )
    parser.add_argument("--project", required=True, help="project name")
    parser.add_argument("--model", required=True, help="model name (used to locate cangjie skeleton)")
    parser.add_argument("--temperature", required=True, help="sampling temperature")
    parser.add_argument("--suffix", default="", help="schema suffix")
    parser.add_argument("--force", action="store_true", help="ignore cache and regenerate")
    args = parser.parse_args()

    if args.force:
        staging = staging_dir_for(args.project)
        if staging.is_dir():
            shutil.rmtree(staging)

    cj_root = Path(f"data/java/skeletons{args.suffix}/translations/{args.model}/{args.temperature}/{args.project}")
    if not cj_root.is_dir():
        raise FileNotFoundError(
            f"cangjie translation skeleton missing at {cj_root}; "
            f"run scripts/java/create_skeleton.sh first."
        )

    ensure_java_mock_logs(args.project, cj_root)


if __name__ == "__main__":
    _cli()
