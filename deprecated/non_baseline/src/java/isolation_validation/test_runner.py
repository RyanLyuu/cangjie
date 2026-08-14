"""Per-fragment mock-test runner used by compositional_translation_validation.

Replaces the per-test loop previously living in run.sh. The build_mock_corpus.sh
script remains the one-shot prerequisite that emits *_test.cj / *.workflow.json
into /tmp/cangjie_mock/<project>/.

Per-translation-session lifecycle:
  - session_inject(skeleton_dir): write helper.cj + simple_ioc.cj into skeleton src/runtime
  - run_mock_tests_for_fragment(...): apply change_mode -> instrument -> cjpm test
                                      -> deinstrument -> restore change_mode
  - session_clean(skeleton_dir): remove helper.cj + simple_ioc.cj
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from src.java.isolation_validation import change_mode, runtime_support, side_effect
from src.java.isolation_validation.test_matcher import find_focal_tests


_FOCAL_RE = re.compile(r"//\s*focal call:\s*(\S+)")
_PKG_NAME_RE = re.compile(r'^\s*name\s*=\s*"([^"]+)"', re.MULTILINE)


def _read_package_name(cjpm_path: Path) -> str:
    text = cjpm_path.read_text(encoding="utf-8")
    m = _PKG_NAME_RE.search(text)
    if not m:
        raise RuntimeError(f"Cannot extract `name = \"...\"` from {cjpm_path}")
    return m.group(1)


def session_inject(skeleton_dir: Path) -> str:
    """Render helper.cj + simple_ioc.cj into <skeleton>/src/runtime using cjpm.toml package name."""
    cjpm_path = skeleton_dir / "cjpm.toml"
    pkg = _read_package_name(cjpm_path)
    runtime_support.inject(skeleton_dir / "src", pkg)
    return pkg


def session_clean(skeleton_dir: Path) -> None:
    runtime_support.clean(skeleton_dir / "src")


def _strip_to_simple(name: str) -> str:
    """Strip TRAM `start-end:` prefix to recover simple class/method identifier."""
    if ":" in name:
        name = name.rsplit(":", 1)[-1]
    return name


def _read_focal(test_cj: Path) -> Optional[tuple[str, str]]:
    try:
        text = test_cj.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        m = _FOCAL_RE.search(line)
        if m:
            focal = m.group(1).strip()
            owner, sep, method = focal.rpartition(".")
            if not sep or not owner or not method:
                return None
            class_name = owner.replace("$", ".").rsplit(".", 1)[-1]
            if method == "<init>":
                method = class_name
            return class_name, method
    return None


def _workflow_for(test_cj: Path) -> Path:
    name = test_cj.name
    if name.endswith("_test.cj"):
        stem = name[: -len("_test.cj")]
    else:
        stem = test_cj.stem
    return test_cj.parent / f"{stem}.workflow.json"


def find_matching_tests(
    staging_dir: Path,
    simple_class: str,
    simple_method: str,
    *,
    is_constructor: bool = False,
    parameters: Optional[list] = None,
    signature: Optional[str] = None,
) -> list[Path]:
    """Return _test.cj files whose normalized focal call matches the fragment."""
    fragment = {
        "class_name": simple_class,
        "fragment_name": simple_method,
        "is_constructor": is_constructor,
        "parameters": parameters,
        "signature": signature,
    }
    return [test_cj for test_cj, _workflow in find_focal_tests(fragment, staging_dir)]


def _tail_lines(text: str, n: int = 50) -> str:
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def run_mock_tests_for_fragment(
    fragment: dict,
    skeleton_dir: Path,
    staging_dir: Path,
) -> tuple[str, str]:
    """Run all mock tests whose focal method matches this fragment.

    Returns (status, message) where status is one of:
      - "no-tests": no matching _test.cj found
      - "not-independent": matched tests require unsupported independent replay
      - "success" : all matching tests passed
      - "failure" : at least one matching test failed (message = last 50 lines)
    """
    simple_class = _strip_to_simple(fragment["class_name"])
    simple_method = _strip_to_simple(fragment["fragment_name"])
    is_constructor = bool(fragment.get("is_constructor", False))

    matched = find_focal_tests(
        {
            "class_name": simple_class,
            "fragment_name": simple_method,
            "is_constructor": is_constructor,
            "parameters": fragment.get("parameters"),
            "signature": fragment.get("signature"),
        },
        staging_dir,
    )
    tests = [test_cj for test_cj, _workflow in matched]
    if not tests:
        return "no-tests", f"no _test.cj matches {simple_class}.{simple_method}"

    # >>> DEBUG_LOG_BEGIN
    print(
        f"[DEBUG_LOG] === mock test for {simple_class}.{simple_method}: "
        f"matched {len(tests)} test(s) {[t.name for t in tests]} ===",
        flush=True,
    )
    # <<< DEBUG_LOG_END

    cj_src = skeleton_dir / "src"
    cj_test_dir = cj_src / "test"
    cj_test_dir.mkdir(parents=True, exist_ok=True)

    change_mode.main(["apply", str(cj_src)])
    last_output = ""
    failed_tests: list[str] = []

    try:
        for test_cj in tests:
            workflow = _workflow_for(test_cj)
            staged_test = cj_test_dir / test_cj.name
            staged_workflow: Optional[Path] = None

            shutil.copy2(test_cj, staged_test)
            if workflow.exists():
                staged_workflow = cj_test_dir / workflow.name
                shutil.copy2(workflow, staged_workflow)
                try:
                    instrument_result = side_effect.instrument(
                        str(staged_test), str(staged_workflow), str(cj_src), structured=True
                    )
                    if instrument_result.get("status") == "not-independent":
                        staged_test.unlink(missing_ok=True)
                        if staged_workflow is not None:
                            staged_workflow.unlink(missing_ok=True)
                        return "not-independent", instrument_result.get("message", "mock test is not independently replayable")
                except Exception as e:
                    print(f"[mock] instrument failed for {test_cj.name}: {e}")

            proc = subprocess.run(
                ["cjpm", "test"],
                cwd=str(skeleton_dir),
                capture_output=True,
                text=True,
            )
            last_output = (proc.stdout or "") + (proc.stderr or "")

            # >>> DEBUG_LOG_BEGIN
            print(
                f"[DEBUG_LOG] --- cjpm test {test_cj.name} (rc={proc.returncode}) ---",
                flush=True,
            )
            print(last_output, flush=True)
            print(f"[DEBUG_LOG] --- end {test_cj.name} ---", flush=True)
            # <<< DEBUG_LOG_END

            try:
                side_effect.deinstrument(str(cj_src))
            except Exception as e:
                print(f"[mock] deinstrument failed: {e}")
            staged_test.unlink(missing_ok=True)
            if staged_workflow is not None:
                staged_workflow.unlink(missing_ok=True)

            if proc.returncode != 0:
                failed_tests.append(test_cj.name)
    finally:
        change_mode.main(["restore", str(cj_src)])

    if failed_tests:
        # TODO(mock-feedback): refine failure feedback shape — currently dumps
        # the last 50 lines of the final cjpm test invocation.
        message = _tail_lines(last_output, 50)
        return "failure", message

    return "success", f"{len(tests)} mock test(s) passed"
