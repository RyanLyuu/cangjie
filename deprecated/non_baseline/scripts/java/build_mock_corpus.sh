#!/usr/bin/env bash
# 用法: build_mock_corpus.sh <project>
#
# 生成 mock 测试样本到 /tmp/cangjie_mock/<project>/，作为 translate_fragment.sh
# 执行前的一次性前置步骤。流程：
#   1. 复制 Java 项目到工作副本，注入 AspectJ + LoggingAspect
#   2. 优先读取 TRAM executed_tests JSON；没有 JSON 时再扫描 Java 测试
#   3. 逐个 mvn -Dtest=<FQCN>#<method>，解析日志 emit *_test.cj + *.workflow.json
#
# 之前的 mock.sh 把 TEST_CLASS 硬编码为单个测试类，本脚本自动扫描所有测试类。
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <project>" >&2
    exit 1
fi

PROJECT="$1"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ISOL="$ROOT/src/java/isolation_validation"
WORK="$ISOL/$PROJECT"
JAVA_SRC=""
for candidate in \
    "$ROOT/projects/java/cleaned_final_projects_evosuite_cleaned_base/$PROJECT" \
    "$ROOT/projects/java/cleaned_final_projects/$PROJECT" \
    "$ROOT/projects/java/original_projects/$PROJECT" \
    "$ROOT/../TRAM/java_projects/cleaned_final_projects/$PROJECT" \
    "$ROOT/../../TRAM/java_projects/cleaned_final_projects/$PROJECT" \
    "$ROOT/projects/java/cleaned_final_projects_decomposed_tests/$PROJECT" \
    "$ROOT/../TRAM/java_projects/cleaned_final_projects_decomposed_tests/$PROJECT" \
    "$ROOT/../../TRAM/java_projects/cleaned_final_projects_decomposed_tests/$PROJECT"; do
    if [[ -d "$candidate" ]]; then
        JAVA_SRC="$candidate"
        break
    fi
done
CJ_PROJECT="$ROOT/projects/cangjie/original_projects/$PROJECT"
CJPM_SRC="$CJ_PROJECT/cjpm.toml"
STAGING="/tmp/cangjie_mock/$PROJECT"
EXECUTED_TESTS_JSON=""
for candidate in \
    "$ROOT/src/java/isolation_validation/executed_tests/$PROJECT.json" \
    "$ROOT/../TRAM/src/isolated_validation/executed_tests/$PROJECT.json" \
    "$ROOT/../../TRAM/src/isolated_validation/executed_tests/$PROJECT.json"; do
    if [[ -f "$candidate" ]]; then
        EXECUTED_TESTS_JSON="$candidate"
        break
    fi
done

[[ -n "$JAVA_SRC" ]] || { echo "Java project not found for: $PROJECT" >&2; exit 1; }

JAVA_TESTS_DIR="$JAVA_SRC/src/test/java"
[[ -d "$JAVA_TESTS_DIR" ]] || { echo "Java tests not found: $JAVA_TESTS_DIR" >&2; exit 1; }

# 1. 准备工作区与 staging 目录
rm -rf "$WORK"
cp -r "$JAVA_SRC" "$WORK"
if [[ "$PROJECT" == "commons-cli" ]]; then
    find "$WORK/src/test/java" -name '*_ESTest.java' -delete
fi
rm -rf "$STAGING"
mkdir -p "$STAGING"
echo "=== Java source: $JAVA_SRC ==="
if [[ -n "$EXECUTED_TESTS_JSON" ]]; then
    echo "=== Executed tests JSON: $EXECUTED_TESTS_JSON ==="
else
    echo "=== Executed tests JSON not found; falling back to source scan ==="
fi

# 2. 注入 AspectJ 依赖 + 添加 LoggingAspect/CustomToStringConverter 到各包
for f in modify_pom.py add_java_files.py clean_evosuite_tests.py; do
    [[ -f "$ISOL/$f" ]] && cp "$ISOL/$f" "$WORK/"
done
(cd "$WORK" && python3 modify_pom.py && python3 add_java_files.py)

# 3. 拷贝 emitter 脚本与 cjpm.toml（让 detect_project_name 读到正确包名）
for f in script.py mock_helper.py log_parser.py reflection.py add_macro.py; do
    [[ -f "$ISOL/$f" ]] && cp "$ISOL/$f" "$WORK/"
done
[[ -f "$CJPM_SRC" ]] && cp "$CJPM_SRC" "$WORK/cjpm.toml"

# 4. 生成测试清单：优先使用 TRAM executed_tests JSON；否则做兼容性源码扫描
TEST_LIST=$(mktemp)
cleanup() {
    rm -f "$TEST_LIST"
}
trap cleanup EXIT

if [[ -n "$EXECUTED_TESTS_JSON" ]]; then
    python3 - "$EXECUTED_TESTS_JSON" "$JAVA_TESTS_DIR" > "$TEST_LIST" <<'PY'
import json
import re
import sys
from pathlib import Path

json_path = Path(sys.argv[1])
tests_root = Path(sys.argv[2])

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

json_classes = set(data)
methods_by_class = {}
for test_file in sorted(tests_root.rglob("*.java")):
    text = test_file.read_text(encoding="utf-8", errors="replace")
    pkg_match = re.search(r"^\s*package\s+([^;]+);", text, re.MULTILINE)
    package = pkg_match.group(1) if pkg_match else ""
    test_class = f"{package}.{test_file.stem}" if package else test_file.stem
    if test_class not in json_classes:
        continue
    methods = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "@Test" not in line and "@ParameterizedTest" not in line:
            continue
        for candidate in lines[i + 1:i + 40]:
            method_match = re.search(r"\bvoid\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", candidate)
            if method_match:
                methods.append(method_match.group(1))
                break
    methods_by_class[test_class] = methods

seen = set()
for test_class, methods in methods_by_class.items():
    for method in methods:
        spec = f"{test_class}#{method}"
        if spec not in seen:
            print(spec)
            seen.add(spec)
else:
    for test_class, methods in data.items():
        available = methods_by_class.get(test_class, [])
        for method in methods:
            if method in available:
                continue
            expanded = [name for name in available if name.startswith(f"{method}_")]
            if expanded:
                continue
            spec = f"{test_class}#{method}"
            print(f"warning: skipping {spec}; not present in selected Java source", file=sys.stderr)
PY
else
    python3 - "$JAVA_TESTS_DIR" > "$TEST_LIST" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
seen = set()
for test_file in sorted(root.rglob("*.java")):
    if not (test_file.name.endswith("Test.java") or test_file.name.endswith("Tests.java")):
        continue
    text = test_file.read_text(encoding="utf-8", errors="replace")
    pkg_match = re.search(r"^\s*package\s+([^;]+);", text, re.MULTILINE)
    package = pkg_match.group(1) if pkg_match else ""
    test_class = f"{package}.{test_file.stem}" if package else test_file.stem
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if "@Test" not in line and "@ParameterizedTest" not in line:
            continue
        for candidate in lines[i + 1:i + 40]:
            method_match = re.search(r"\bvoid\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", candidate)
            if method_match:
                spec = f"{test_class}#{method_match.group(1)}"
                if spec not in seen:
                    print(spec)
                    seen.add(spec)
                break
PY
fi

TEST_COUNT=$(grep -c . "$TEST_LIST" || true)
if [[ "$TEST_COUNT" -eq 0 ]]; then
    echo "No test methods found" >&2
    exit 1
fi

echo "=== Found $TEST_COUNT test method(s) ==="

TOTAL_RUN=0
TOTAL_OK=0
TOTAL_SKIP=0

emit_logs() {
    for LOG in "$WORK"/*.log; do
        [[ -f "$LOG" ]] || continue
        echo "  Emitting: $(basename "$LOG")"
        (cd "$WORK" && python3 script.py "$(basename "$LOG")" --output-dir "$STAGING") || true
        rm -f "$LOG"
    done
}

run_one() {
    local TEST_SPEC="$1"
    local TEST_CLASS="${TEST_SPEC%#*}"
    local METHOD="${TEST_SPEC#*#}"

    TOTAL_RUN=$((TOTAL_RUN + 1))
    echo "=== [$TOTAL_RUN/$TEST_COUNT] $TEST_CLASS#$METHOD ==="
    rm -f "$WORK"/*.log
    if (cd "$WORK" && mvn clean test \
            -Drat.skip -Dgpg.skip -Dmaven.javadoc.skip -Dmoditect.skip -Dcheckstyle.skip \
            "-Dtest=${TEST_CLASS}#${METHOD}" -q); then
        emit_logs
        TOTAL_OK=$((TOTAL_OK + 1))
    else
        echo "  SKIP (maven failed): $TEST_CLASS#$METHOD"
        rm -f "$WORK"/*.log
        TOTAL_SKIP=$((TOTAL_SKIP + 1))
    fi
}

run_batch() {
    local -a SPECS=("$@")
    local TEST_ARG
    TEST_ARG=$(IFS=,; echo "${SPECS[*]}")

    TOTAL_RUN=$((TOTAL_RUN + ${#SPECS[@]}))
    echo "=== [$TOTAL_RUN/$TEST_COUNT] batch (${#SPECS[@]} method(s)) ==="
    rm -f "$WORK"/*.log
    if (cd "$WORK" && mvn clean test \
            -Drat.skip -Dgpg.skip -Dmaven.javadoc.skip -Dmoditect.skip -Dcheckstyle.skip \
            "-Dtest=${TEST_ARG}" -q); then
        emit_logs
        TOTAL_OK=$((TOTAL_OK + ${#SPECS[@]}))
    else
        echo "  Batch failed; retrying method-by-method"
        TOTAL_RUN=$((TOTAL_RUN - ${#SPECS[@]}))
        rm -f "$WORK"/*.log
        for SPEC in "${SPECS[@]}"; do
            run_one "$SPEC"
        done
    fi
}

mapfile -t TEST_SPECS < "$TEST_LIST"
BATCH_SIZE="${MOCK_CORPUS_BATCH_SIZE:-25}"
for ((i = 0; i < ${#TEST_SPECS[@]}; i += BATCH_SIZE)); do
    CHUNK=("${TEST_SPECS[@]:i:BATCH_SIZE}")
    run_batch "${CHUNK[@]}"
done

CJ_COUNT=$(find "$STAGING" -maxdepth 1 -name '*.cj' | wc -l)
echo ""
echo "=== Summary ==="
echo "  test methods executed : $TOTAL_RUN"
echo "  successful            : $TOTAL_OK"
echo "  skipped (mvn failed)  : $TOTAL_SKIP"
echo "  generated _test.cj    : $CJ_COUNT  (in $STAGING)"
