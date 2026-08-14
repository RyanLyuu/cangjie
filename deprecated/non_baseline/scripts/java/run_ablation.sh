#!/usr/bin/env bash
# Run a full ablation sweep (2^3 = 8 combinations of Part 1/2/3 enhancement
# flags) for a single <project>. After each translate_fragment.sh run, the
# schema JSON directory is snapshotted into a per-run-tag subdirectory so
# that `ablation_compare.py` can compare pass-rates across configurations.
#
# Usage:
#   bash scripts/java/run_ablation.sh <project> <model> <suffix> <temperature> \
#       [use_rag] [skip_mock] [translate_tests] [use_progressive_kb]
#
# Example:
#   bash scripts/java/run_ablation.sh jansi deepseek-chat _evosuite_cleaned_base 0.0 \
#       true true false true
#
# Outputs:
#   data/java/ablation/<project>_<model>_<temp><suffix>/<run-tag>/   (schema JSON snapshot)
#   data/java/ablation/<project>_<model>_<temp><suffix>/<run-tag>/skeletons/  (.cj files *optional*)
#   data/java/ablation/<project>_<model>_<temp><suffix>/report.md
#   data/java/ablation/<project>_<model>_<temp><suffix>/metrics.csv
#   data/java/ablation/<project>_<model>_<temp><suffix>/significance.csv
#
# Tip: pass `--skip-build` separately if cjpm is unavailable — but
# translate_fragment.sh still relies on compile validation, so removing only
# the mock-test phase requires `skip_mock=true` rather than --skip-build.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$(pwd)"

if [ $# -lt 4 ]; then
  echo "Usage: $0 <project> <model> <suffix> <temperature> [use_rag] [skip_mock] [translate_tests] [use_progressive_kb]"
  exit 1
fi

project="$1"
model="$2"
suffix="$3"
temp="$4"
use_rag="${5:-true}"
skip_mock="${6:-true}"
translate_tests="${7:-false}"
use_progressive_kb="${8:-true}"

schema_dir="data/java/schemas${suffix}/${model}/${temp}/${project}"
if [ ! -d "$schema_dir" ]; then
  echo "Aborting: schema dir not found: $schema_dir"
  exit 1
fi

out_root="data/java/ablation/${project}_${model}_${temp}${suffix}"
rm -rf "$out_root"
mkdir -p "$out_root"

# Special baseline tag uses all enhancement flags = false, then snapshots
# the schema dir; this provides the comparator. Note: each run starts from the
# SAME baseline skeleton+schema directory. translate_fragment.sh does NOT
# reset these (only the user calls _reset_translation_skeletons_from_baseline
# or similar before each run). For a clean sweep, you should also recreate
# the .cj skeletons before each run — this script re-runs create_skeleton.sh
# before every translate_fragment.sh to guarantee a clean baseline each round.

recreate_skeletons() {
  echo "[ablation] regenerating skeleton for $project ..."
  bash scripts/java/create_skeleton.sh "$project" "$model" "$suffix" "$temp" "$translate_tests" >/dev/null 2>&1
}

snapshot_schema() {
  local tag="$1"
  local dst="$out_root/$tag"
  rm -rf "$dst"
  mkdir -p "$dst"
  cp -r "$schema_dir"/* "$dst"/ 2>/dev/null || true

  # Optional: snapshot the resulting .cj files for TODO-count comparison.
  local sk_src="data/java/skeletons/translations/${model}/${temp}/${project}"
  if [ -d "$sk_src" ]; then
    mkdir -p "$dst/skeletons"
    cp -r "$sk_src"/* "$dst/skeletons"/ 2>/dev/null || true
  fi
}

run_one() {
  local tag="$1"; shift
  local pseudo="$1"; shift
  local grammar="$1"; shift
  local syntax="$1"; shift
  echo "=========================================================="
  echo "[ablation] RUN: $tag"
  echo "  use_pseudocode=$pseudo use_grammar_prompt=$grammar use_syntax_rag=$syntax"
  echo "=========================================================="
  recreate_skeletons
  bash scripts/java/translate_fragment.sh "$project" "$model" "$suffix" "$temp" \
    "$use_rag" "$skip_mock" "$translate_tests" "$use_progressive_kb" \
    "$pseudo" "$grammar" "$syntax" || true
  snapshot_schema "$tag"
}

run_one "baseline"           false false false
run_one "pseudo"             true  false false
run_one "grammar"            false true  false
run_one "syntax"             false false true
run_one "pseudo+grammar"     true  true  false
run_one "pseudo+syntax"     true  false true
run_one "grammar+syntax"    false true  true
run_one "all"                true  true  true

echo "[ablation] all runs complete; generating comparison report ..."
python3 -m src.java.analysis.ablation_compare \
    --project "$project" \
    --model "$model" \
    --temperature "$temp" \
    --suffix "$suffix" \
    --ablation-root "$out_root"

echo "[done] report: $out_root/report.md"
