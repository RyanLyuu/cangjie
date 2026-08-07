#!/usr/bin/env bash

set -euo pipefail

MODEL="${MODEL:-deepseek-chat}"
TEMP="${TEMP:-0.0}"
SUFFIX="${SUFFIX:-_evosuite_cleaned_base}"
ANALYSIS_DIR="${ANALYSIS_DIR:-data/analysis}"
TRANSLATE_TESTS="${TRANSLATE_TESTS:-false}"

FRAGMENT_VIS_LOG="$ANALYSIS_DIR/525f.txt"
FULL_LOG="$ANALYSIS_DIR/525full.txt"

PROJECTS=(jansi commons-cli)

mkdir -p "$ANALYSIS_DIR"

cat > "$FRAGMENT_VIS_LOG" <<EOF
# 525 Fragment Visual Log

model=$MODEL
temperature=$TEMP
suffix=$SUFFIX
use_rag=$USE_RAG
skip_mock=$SKIP_MOCK
translate_tests=$TRANSLATE_TESTS
started_at=$(date -Is)

EOF

cat > "$FULL_LOG" <<EOF
# 525 Full Translation Log

model=$MODEL
temperature=$TEMP
suffix=$SUFFIX
use_rag=$USE_RAG
skip_mock=$SKIP_MOCK
translate_tests=$TRANSLATE_TESTS
started_at=$(date -Is)

EOF

append_header() {
  local file="$1"
  local title="$2"
  {
    echo
    echo "## $title"
    echo
    echo '```text'
  } >> "$file"
}

append_footer() {
  local file="$1"
  echo '```' >> "$file"
}

append_body_log() {
  local project="$1"
  local body_log="${project}_${MODEL}_body.log"

  append_header "$FULL_LOG" "$project fragment detail log: $body_log"
  if [ -f "$body_log" ]; then
    cat "$body_log" >> "$FULL_LOG"
  else
    echo "missing body log: $body_log" >> "$FULL_LOG"
  fi
  append_footer "$FULL_LOG"
}

run_skeleton_generation() {
  local project="$1"

  echo "[run] skeleton generation: $project"
  append_header "$FULL_LOG" "$project skeleton generation"
  bash scripts/java/create_skeleton.sh "$project" "$MODEL" "$SUFFIX" "$TEMP" "$TRANSLATE_TESTS" \
    >> "$FULL_LOG" 2>&1
  append_footer "$FULL_LOG"
}

run_fragment_translation() {
  local project="$1"
  local body_log="${project}_${MODEL}_body.log"

  echo "[run] fragment translation: $project"
  rm -f "$body_log"

  append_header "$FRAGMENT_VIS_LOG" "$project"
  append_header "$FULL_LOG" "$project fragment terminal output"

  set +e
  bash scripts/java/translate_fragment.sh "$project" "$MODEL" "$SUFFIX" "$TEMP" "$TRANSLATE_TESTS" \
    > >(tee -a "$FRAGMENT_VIS_LOG" >> "$FULL_LOG") \
    2> >(tee -a "$FULL_LOG" >&2)
  local status=$?
  set -e

  append_footer "$FRAGMENT_VIS_LOG"
  append_footer "$FULL_LOG"
  append_body_log "$project"

  return "$status"
}

for project in "${PROJECTS[@]}"; do
  {
    echo
    echo "## $project round"
    echo
    echo "started_at=$(date -Is)"
  } >> "$FULL_LOG"

  run_skeleton_generation "$project"
  run_fragment_translation "$project"

  {
    echo
    echo "finished_at=$(date -Is)"
  } >> "$FULL_LOG"
done

{
  echo
  echo "completed_at=$(date -Is)"
} >> "$FRAGMENT_VIS_LOG"

{
  echo
  echo "completed_at=$(date -Is)"
} >> "$FULL_LOG"

echo "[done] logs:"
echo "  $FRAGMENT_VIS_LOG"
echo "  $FULL_LOG"
