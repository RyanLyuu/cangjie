#!/bin/bash
# Build the Part-3 syntax-graph RAG index from CangjieCorpus.
#
# Usage:
#   bash scripts/java/build_syntax_graph_index.sh [corpus_root]
#
# Reads .cj / .cangjie / .cj.txt files (and fenced code blocks in .md docs) under
# <corpus_root> (default misc/CangjieCorpus), extracts control-flow + data-flow
# structural fingerprints, and persists a pickled index + a human-readable JSONL
# mirror under data/java/rag/.
#
# Run once after cloning CangjieCorpus. Re-run when the corpus is updated.
# The retriever (src/java/rag/syntax_graph.py) will lazily build the index on
# first use if this script has not been run, but it's much faster to pre-build it.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

CORPUS="${1:-misc/CangjieCorpus}"
export PYTHONPATH="$(pwd)"

python3 - <<PY
from src.java.rag.syntax_graph import build_syntax_graph_index
n = build_syntax_graph_index(corpus_root="${CORPUS}")
print(f"Indexed {n} Cangjie corpus chunks into data/java/rag/syntax_graph_index.pkl")
PY
