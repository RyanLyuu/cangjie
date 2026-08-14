#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: bash run.sh <project>" >&2
  exit 2
fi

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

PROJECT="$1"
SCHEMA_MODEL="${SCHEMA_MODEL:-codex-baseline}"
TEMPERATURE="${TEMPERATURE:-0.0}"
SUFFIX="${SUFFIX:-_evosuite_cleaned_base}"
PROJECT_ROOT="${PROJECT_ROOT:-projects/cleaned_final_projects_evosuite_cleaned_base}"
TRANSLATE_TESTS="${TRANSLATE_TESTS:-false}"
AGENT_MODEL="${AGENT_MODEL:-}"
AGENT_TRANSPORT="${AGENT_TRANSPORT:-app-server}"
MAX_BUILDS="${MAX_BUILDS:-3}"

if [[ ! -d "$PROJECT_ROOT/$PROJECT" ]]; then
  echo "Project not found: $PROJECT_ROOT/$PROJECT" >&2
  exit 1
fi

export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

bash scripts/java/create_schema.sh \
  "$PROJECT" "$SCHEMA_MODEL" "$TEMPERATURE" "$SUFFIX" "$PROJECT_ROOT"

bash scripts/java/get_dependencies.sh \
  "$PROJECT" "$SUFFIX" "$PROJECT_ROOT"

bash scripts/java/create_skeleton.sh \
  "$PROJECT" "$SCHEMA_MODEL" "$SUFFIX" "$TEMPERATURE" \
  "$TRANSLATE_TESTS" "$AGENT_MODEL"

bash scripts/java/translate_fragment.sh \
  "$PROJECT" "$SCHEMA_MODEL" "$SUFFIX" "$TEMPERATURE" \
  "$TRANSLATE_TESTS" "$AGENT_MODEL" "$AGENT_TRANSPORT" "$MAX_BUILDS"
