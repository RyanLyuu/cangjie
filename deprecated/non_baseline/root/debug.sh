#!/usr/bin/env bash
# >>> DEBUG_LOG_BEGIN — temporary debug wrapper. Delete this file along with all
# DEBUG_LOG-marked blocks (`grep -rn DEBUG_LOG`) when no longer needed.
#
# Runs translate_fragment.sh and tees ALL output (including the cjpm test
# subprocess output that test_runner.py prints behind DEBUG_LOG markers) to
# ./translate_debug.log at the repo root. Each invocation overwrites the log.
#
# Usage: ./debug.sh <project> <model> <suffix> <temperature> [use_rag]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG="$ROOT/translate_debug.log"

bash "$ROOT/scripts/java/translate_fragment.sh" "$@" 2>&1 | tee "$LOG"
# <<< DEBUG_LOG_END
