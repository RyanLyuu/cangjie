"""Tests for the Part-2 grammar prompt module.

Validates that the grammar prompt block loads from configs/prompt_templates.yaml
(or falls back to the inline excerpt when the config is unreachable), is cached
across calls, and contains the expected EBNF marker text.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.java.translation import grammar_prompt  # noqa: E402


def test_build_grammar_prompt_returns_nonempty_block_with_ebnf_marker():
    text = grammar_prompt.build_grammar_prompt()
    assert isinstance(text, str)
    assert text.strip()
    # The authoritative template lives in configs/prompt_templates.yaml; both
    # that and the fallback inline excerpt lead with the EBNF-excerpt header.
    assert "Grammar Reference" in text or "var_decl" in text


def test_get_grammar_prompt_is_cached():
    grammar_prompt.reset_cache()
    grammar_prompt._instance = None  # noqa: SLF001
    first = grammar_prompt.get_grammar_prompt()
    second = grammar_prompt.get_grammar_prompt()
    assert first == second
    assert isinstance(first, str) and first.strip()


def test_cache_reset_reloads(monkeypatch):
    grammar_prompt.reset_cache()
    monkeypatch.setattr(
        grammar_prompt,
        "_FALLBACK_GRAMMAR",
        "### STUB FALLBACK GRAMMAR\nvar_decl ::= \"let\" IDENT \":\" TYPE",
    )
    # Force the cache loader to return an empty templates dict so the fallback is used.
    monkeypatch.setattr(grammar_prompt, "_load_templates", lambda: {})
    grammar_prompt._instance = None  # noqa: SLF001
    text = grammar_prompt.get_grammar_prompt()
    assert "STUB FALLBACK GRAMMAR" in text
    grammar_prompt.reset_cache()