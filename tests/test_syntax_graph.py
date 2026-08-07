"""Tests for the syntax-graph RAG signature extractor (Part 3).

Pure-unit: no network, no LLM, no Cangjie SDK. Validates that structural
signatures are produced for both Java and Cangjie snippets, that cross-lingual
similarity works on identical-control-flow pairs, and that the singleton
retriever degrades gracefully when no index exists.
"""

import os
import sys

# Make the repo importable from repo root (matches the project's pytest
# invocation documented in AGENTS.md: `PYTHONPATH=$(pwd) python -m pytest`).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.java.rag.syntax_graph import (  # noqa: E402
    _jaccard,
    infer_structural_signature,
    reset_syntax_graph_rag,
)


def test_signature_has_control_flow_tokens_for_loop_and_branch():
    java = (
        "public int sum(int[] xs) {\n"
        "  int total = 0;\n"
        "  for (int x : xs) { if (x > 0) total += x; }\n"
        "  return total;\n"
        "}"
    )
    sig = infer_structural_signature(java, "")
    assert "cf_if:1" in sig.shape_bag
    assert "cf_loop:1" in sig.shape_bag
    assert "cf_return:1" in sig.shape_bag
    # method calls (sum and nothing else) -> op_call bucket
    assert any(s.startswith("op_call:") for s in sig.shape_bag)


def test_cross_lingual_similarity_high_for_equivalent_structure():
    java = (
        "public int count(int[] xs) {\n"
        "  int n = 0;\n"
        "  for (int x : xs) { if (x > 0) n++; }\n"
        "  return n;\n"
        "}"
    )
    cangjie = (
        "public func count(xs: Array<Int64>): Int64 {\n"
        "  var n = 0\n"
        "  for (x in xs) { if (x > 0) { n += 1 } }\n"
        "  return n\n"
        "}"
    )
    sj = infer_structural_signature(java, "")
    sc = infer_structural_signature(cangjie, "")
    # Both have if/for/return at the same bucket counts; similarity should be high.
    assert _jaccard(sj.shape_bag, sc.shape_bag) >= 0.6


def test_signature_empty_for_blank_code():
    sig = infer_structural_signature("", "")
    assert sig.shape_bag == frozenset()
    assert sig.call_names == frozenset()
    assert sig.container_types == frozenset()


def test_singleton_returns_empty_when_no_index(tmp_path, monkeypatch):
    reset_syntax_graph_rag()
    from src.java.rag import syntax_graph as _sg

    # Rediect the default index path to a non-existent location and ensure the
    # corpus path also doesn't exist, so the lazy build path is skipped.
    monkeypatch.setattr(_sg, "_DEFAULT_INDEX_PATH", tmp_path / "no_index.pkl")
    monkeypatch.setattr(_sg, "_DEFAULT_CORPUS_ROOT", tmp_path / "no_corpus")
    rag = _sg.get_syntax_graph_rag()
    assert rag.retrieve("public void hello() { int x = 1; }", top_k=3) == []
    assert rag.format_for_prompt([]) == ""
    assert rag.inject("hello") == ""