"""Tests for the ablation-analysis module.

Pure-unit: no network, no LLM, no Cangjie SDK. Validates:
  - Fisher's exact two-sided computes sensible p-values for trivial tables
    (the all-pass vs all-fail edge cases, a balanced 50/50 with no effect)
  - stats_to_metrics flattens an analyze_project-style stats dict without
    crashing and produces the expected rate keys
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.java.analysis.ablation_compare import (  # noqa: E402
    fisher_exact_2x2,
    stats_to_metrics,
)
from collections import Counter


def test_fisher_identity_table_p_is_one():
    # Identical distributions ⇒ p_two = 1.0
    table = ((5, 5), (5, 5))
    or_val, p = fisher_exact_2x2(table)
    assert abs(p - 1.0) < 1e-6, p
    assert abs(or_val - 1.0) < 1e-6, or_val


def test_fisher_maximal_split_is_significant():
    # All baseline fail, all alternative pass ⇒ strongly significant
    table = ((0, 4), (4, 0))
    or_val, p = fisher_exact_2x2(table)
    assert p < 0.05
    assert or_val > 1.0


def test_fisher_all_fail_returns_one():
    table = ((0, 4), (0, 4))
    or_val, p = fisher_exact_2x2(table)
    # Both rows identical (all-fail) ⇒ p_two == 1.0
    assert abs(p - 1.0) < 1e-6, p


def test_stats_to_metrics_flattens_fields():
    fake_stats = {
        "total_fragments": 10,
        "by_status": {"completed": 7, "attempted": 2, "out_of_context": 1, "pending": 0},
        "compilation": {"success": 8, "syntax_error": 1, "undefined_identifier": 1},
        "test_execution": {"success": 5, "no-tests": 2, "not-exercised": 1, "failure": 0},
        "elapsed_time_total": 123.4,
        "elapsed_by_status": {"completed": 100.0, "failed": 20.0, "other": 3.4},
    }
    row = stats_to_metrics(fake_stats, todo_info={"total_todos": 3, "files_with_todos": 2})
    assert row["total_fragments"] == 10
    assert row["completed"] == 7
    assert row["completed_rate"] == 0.7
    assert row["compiled_pass"] == 8
    assert row["compiled_pass_rate"] == 0.8
    # test_pass = 5 + 2 (no-tests) + 1 (not-exercised) = 8
    assert row["test_pass"] == 8
    assert abs(row["elapsed_mean_s"] - 12.34) < 1e-6
    assert row["residual_todos"] == 3
    assert abs(row["residual_todos_per_file"] - 1.5) < 1e-6


def test_stats_to_metrics_empty_stats():
    row = stats_to_metrics({})
    assert row["total_fragments"] == 0
    assert row["completed_rate"] == 0.0
    assert row["compiled_pass_rate"] == 0.0
    assert row["elapsed_mean_s"] == 0.0


def test_generate_markdown_report_smoke():
    """End-to-end-ish smoke: build 2 synthetic rows + report, assert headers."""
    from src.java.analysis.ablation_compare import generate_markdown_report

    rows = [
        {
            "run_tag": "baseline", "flag_label": "(none)",
            "total_fragments": 20,
            "completed": 10, "compiled_pass": 12, "test_pass": 8,
            "attempted": 6, "out_of_context": 2, "pending": 2,
            "completed_rate": 0.5, "compiled_pass_rate": 0.6,
            "test_pass_rate_of_compiled": 0.667, "test_pass_rate_of_total": 0.4,
            "elapsed_total_s": 200.0, "elapsed_mean_s": 10.0,
            "residual_todos": 5, "residual_todos_per_file": 1.0,
        },
        {
            "run_tag": "pseudo", "flag_label": "+Part1",
            "total_fragments": 20,
            "completed": 14, "compiled_pass": 16, "test_pass": 12,
            "attempted": 4, "out_of_context": 1, "pending": 1,
            "completed_rate": 0.7, "compiled_pass_rate": 0.8,
            "test_pass_rate_of_compiled": 0.75, "test_pass_rate_of_total": 0.6,
            "elapsed_total_s": 250.0, "elapsed_mean_s": 12.5,
            "residual_todos": 2, "residual_todos_per_file": 0.5,
        },
    ]
    sig = [
        {"run_tag": "pseudo", "metric": "compiled_pass", "baseline_pass": 12,
         "baseline_total": 20, "alt_pass": 16, "alt_total": 20,
         "odds_ratio": 3.0, "p_value": 0.04},
    ]
    md = generate_markdown_report(rows, sig, "jansi", "deepseek-chat", "0.0", "")
    assert "# Fragment Translation Ablation Report" in md
    assert "Deltas vs baseline" in md
    assert "Fisher" in md
    assert "Per-part isolated effect" in md
    assert "baseline" in md and "pseudo" in md
    assert "pp" in md  # percentage-point deltas