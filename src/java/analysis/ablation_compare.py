"""
Ablation analysis for the three fragment-translation enhancements (Part 1/2/3).

This module compares the translation pass-rate, compilation pass-rate,
test-execution pass-rate, residual-TODO rate, and average elapsed time across
the 2^3 = 8 combinations of the enhancement flags:

    baseline   (none)
    +pseudo    (use_pseudocode)
    +grammar   (use_grammar_prompt)
    +syntax    (use_syntax_rag)
    +pseudo+grammar
    +pseudo+syntax
    +grammar+syntax
    +all       (pseudo+grammar+syntax)

It REUSES the existing stats extractor from `analyze_errors.py` — it does NOT
modify that file — by importing `analyze_project`. Each run (combination) is
expected to have been produced ahead of time by invoking
`translate_fragment.sh` with the corresponding position-9/10/11 flags. Because
translate_fragment.sh writes its schema updates (translation_status /
compilation / test_outcome) back into the schema JSON directory
`data/java/schemas{suffix}/{model}/{temp}/{project}/`, the run results are
read by inspecting that directory per *run-tag*.

However, the existing schema JSON files for a project all live under the same
single directory: each translate_fragment.sh *overwrites* the same schema JSON
files between runs. Therefore, in order to do an ablation you must either:

  (a) copy the schema directory to a distinct run-tagged subdirectory after
      each translate_fragment.sh run, OR
  (b) pass --output from translate_fragment (which uses
      translate_fragment.sh, not the schema JSON path) — the schema JSON path
      is fixed in code; therefore (a) is the supported workflow.

This module supports (a) by accepting a `--base-schemas-root` directory
specifier. The recommended run-tag naming convention is:

    data/java/ablation/<project>_<model>_<temp><suffix>/baseline/
    data/java/ablation/<project>_<model>_<temp><suffix>/pseudo/
    data/java/ablation/<project>_<model>_<temp><suffix>/grammar/
    data/java/ablation/<project>_<model>_<temp><suffix>/syntax/
    data/java/ablation/<project>_<model>_<temp><suffix>/pseudo+grammar/
    data/java/ablation/<project>_<model>_<temp><suffix>/pseudo+syntax/
    data/java/ablation/<project>_<model>_<temp><suffix>/grammar+syntax/
    data/java/ablation/<project>_<model>_<temp><suffix>/all/

Each subdirectory must contain the per-schema JSON files (= the contents of
data/java/schemas<suffix>/<model>/<temp>/<project>/ after a translate_fragment
run with the indicated flags).

You can either manually `cp -r` the schema dir into each tag subdir, or use
the convenience wrapper `scripts/java/run_ablation.sh` which runs the 8
translate_fragment invocations and snapshots the schemas between each.

CLI:

    python -m src.java.analysis.ablation_compare \
        --project jansi \
        --model deepseek-chat \
        --temperature 0.0 \
        --suffix _evosuite_cleaned_base \
        --ablation-root data/java/ablation/jansi_deepseek-chat_0.0_evosuite_cleaned_base \
        [--skeleton-snapshots-root data/java/ablation/skeletons] \
        [--output data/java/ablation/jansi_deepseek-chat_0.0_evosuite_cleaned_base/report.md] \
        [--csv data/java/ablation/jansi_deepseek-chat_0.0_evosuite_cleaned_base/metrics.csv] \
        [--skip-significance]   # skip Fisher exact test if too few fragments
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Reuse the existing per-project stats extractor WITHOUT modifying it.
from src.java.analysis.analyze_errors import analyze_project
from src.java.analysis.analyze_errors import count_todos_in_skeletons


# ---------------------------------------------------------------------------
# Run-tag definitions — keep in sync with scripts/java/run_ablation.sh
# ---------------------------------------------------------------------------

RUN_TAGS: list[str] = [
    "baseline",
    "pseudo",
    "grammar",
    "syntax",
    "pseudo+grammar",
    "pseudo+syntax",
    "grammar+syntax",
    "all",
]

FLAG_LABELS: dict[str, str] = {
    "baseline": "(none)",
    "pseudo": "+Part1",
    "grammar": "+Part2",
    "syntax": "+Part3",
    "pseudo+grammar": "+Part1+2",
    "pseudo+syntax": "+Part1+3",
    "grammar+syntax": "+Part2+3",
    "all": "+Part1+2+3",
}


# ---------------------------------------------------------------------------
# Metric extraction — convert stats dict to a flat metrics row
# ---------------------------------------------------------------------------

def stats_to_metrics(stats: dict, todo_info: Optional[dict] = None) -> dict:
    """Flatten the analyze_project() stats dict into ablation metrics.

    Keys returned (all numeric; rates are fractions in [0,1]):
      total_fragments, completed, compiled_pass, test_pass, attempted,
      out_of_context, pending,
      completed_rate, compiled_pass_rate, test_pass_rate,
      elapsed_total_s, elapsed_mean_s,
      residual_todos, residual_todo_rate
    """
    total = stats.get("total_fragments", 0) or 0
    by_status = stats.get("by_status", {})
    compilation = stats.get("compilation", {})
    test_exec = stats.get("test_execution", {})
    elapsed_total = stats.get("elapsed_time_total", 0.0) or 0.0

    completed = by_status.get("completed", 0)
    attempted = by_status.get("attempted", 0)
    out_of_context = by_status.get("out_of_context", 0)
    pending = by_status.get("pending", 0)

    # Compiled-pass = fragments whose cangjie_compilation outcome == "success".
    compiled_pass = compilation.get("success", 0)
    compiled_fail = 0
    for k, v in compilation.items():
        if k != "success":
            compiled_fail += v

    # Test-pass = success / not-exercised / no-tests. The pool of fragments
    # that had at least a chance to pass tests is "compiled_pass" minus the
    # not-attempted, but for simplicity and BI parity we report test_pass as
    # "the count of test outcomes in the success/no-tests/not-exercised set"
    # and rate as test_pass / compiled_pass (compile is a precondition).
    test_pass = (
        test_exec.get("success", 0)
        + test_exec.get("no-tests", 0)
        + test_exec.get("not-exercised", 0)
    )
    test_fail = sum(v for k, v in test_exec.items() if k not in ("success", "no-tests", "not-exercised"))

    elapsed_mean = elapsed_total / total if total else 0.0

    row = {
        "total_fragments": total,
        "completed": completed,
        "compiled_pass": compiled_pass,
        "compiled_fail": compiled_fail,
        "test_pass": test_pass,
        "test_fail": test_fail,
        "attempted": attempted,
        "out_of_context": out_of_context,
        "pending": pending,
        "completed_rate": (completed / total) if total else 0.0,
        "compiled_pass_rate": (compiled_pass / total) if total else 0.0,
        "test_pass_rate_of_compiled": (test_pass / compiled_pass) if compiled_pass else 0.0,
        "test_pass_rate_of_total": (test_pass / total) if total else 0.0,
        "elapsed_total_s": round(elapsed_total, 2),
        "elapsed_mean_s": round(elapsed_mean, 2),
        "residual_todos": 0,
        "residual_todo_rate": 0.0,
    }

    # Optional: residual TODO rate per run. The caller passes a per-run
    # skeleton snapshot dir; we count TODOs across all .cj snapshots in the
    # snapshot subdirectory for this run-tag (graceful 0 if not provided).
    if todo_info is not None:
        row["residual_todos"] = int(todo_info.get("total_todos", 0) or 0)
        # rate relative to total fragments is not meaningful; use absolute
        # count (lower = better). Also provide a per-file mean as reference.
        n_files = int(todo_info.get("files_with_todos", 0) or 0)
        if n_files:
            row["residual_todos_per_file"] = round(row["residual_todos"] / n_files, 2)
        else:
            row["residual_todos_per_file"] = 0.0

    return row


# ---------------------------------------------------------------------------
# Fisher exact test — pure Python (2x2), no scipy dependency
# ---------------------------------------------------------------------------

def _log_factorial(n: int) -> float:
    """ln(n!) for non-negative integers — precomputed cache via math.lgamma."""
    import math
    if n <= 1:
        return 0.0
    return math.lgamma(n + 1)


def fisher_exact_2x2(table: tuple[tuple[int, int], tuple[int, int]]) -> tuple[float, float]:
    """Fisher's exact test for a 2x2 table.

    Table layout::

        [[a, b],
         [c, d]]

    Returns `(odds_ratio, two_sided_p_value)`. Pure-python enumeration over the
    hypergeometric distribution (no scipy dependency). Accurate for any table
    size but O(min(r,col)) — perfect for fragment counts here.

    Uses lgamma for the log-probabilities to keep numerical stability for
    large counts.
    """
    import math

    (a, b), (c, d) = table
    n = a + b + c + d
    r = a + c       # row 0 total
    col = a + b     # col 0 total

    # Feasible x range
    x_min = max(0, r + col - n)
    x_max = min(r, col)

    if x_max < x_min:
        return float("nan"), 1.0

    def log_hyper_pmf(x: int) -> float:
        return (
            _log_factorial(r)
            + _log_factorial(n - r)
            + _log_factorial(col)
            + _log_factorial(n - col)
            - _log_factorial(x)
            - _log_factorial(max(0, r - x))
            - _log_factorial(max(0, col - x))
            - _log_factorial(max(0, n - r - col + x))
            - _log_factorial(n)
        )

    log_probs = [log_hyper_pmf(x) for x in range(x_min, x_max + 1)]

    # Two-sided p: sum of probabilities <= the observed probability.
    observed_idx = a - x_min
    if not (0 <= observed_idx < len(log_probs)):
        return float("nan"), 1.0
    observed_lp = log_probs[observed_idx]
    max_lp = max(log_probs)
    p_two = 0.0
    for lp in log_probs:
        if lp <= observed_lp + 1e-12:
            p_two += math.exp(lp - max_lp)
    p_two *= math.exp(max_lp)
    if p_two > 1.0:
        p_two = 1.0

    # Alternative-vs-baseline odds ratio. Apply the Haldane-Anscombe 0.5
    # correction when a cell is 0 so complete separation remains finite.
    a_f, b_f, c_f, d_f = float(a), float(b), float(c), float(d)
    if 0 in (a, b, c, d):
        a_f, b_f, c_f, d_f = a_f + 0.5, b_f + 0.5, c_f + 0.5, d_f + 0.5
    odds_ratio = (b_f * c_f) / (a_f * d_f)

    return odds_ratio, p_two


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

HEADER_FIELDS = [
    "run_tag", "flag_label",
    "total_fragments", "completed", "completed_rate",
    "compiled_pass", "compiled_pass_rate",
    "test_pass", "test_pass_rate_of_compiled",
    "attempted", "out_of_context", "pending",
    "elapsed_total_s", "elapsed_mean_s",
    "residual_todos", "residual_todos_per_file",
]


def _fmt_pct(frac: float) -> str:
    return f"{frac * 100:.1f}%"


def _fmt_delta(cur: float, base: float, is_rate: bool = False) -> str:
    """Format 'cur - base' as a human-readable delta string.

    For rates (is_rate=True): format as a percentage-point delta.
    For counts: format as +N / -N / (=0).
    """
    diff = cur - base
    if is_rate:
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff * 100:.1f}pp"
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:.0f}"


def _load_run(ablation_root: Path, run_tag: str) -> Optional[dict]:
    """Load run-tag stats from <ablation_root>/<run_tag>/ and return metrics.

    Returns None if run-tag directory does not exist (caller skips it).
    Each run-tag directory must contain a `*.json` schema-set (the contents
    of data/java/schemas<suffix>/<model>/<temp>/<project>/ for that run).
    Optional: a sibling `skeletons/` subdir under <run_tag> containing the
    .cj snapshot is used to compute residual-TODO metric.
    """
    run_dir = ablation_root / run_tag
    if not run_dir.is_dir():
        return None

    # analyze_project expects (translation_dir, project). The `project` arg
    # is only used to append to translation_dir, so we pass the run_dir
    # itself BUT analyze_project does `Path(translation_dir) / project`.
    # We therefore construct the parent + project-name mapping manually:
    # Easiest: copy the contents up one level: pass translation_dir =
    # str(run_dir.parent) and project = run_dir.name. works as long as
    # run_dir.name == project passed to analyze_project (the run-tag, NOT
    # the actual project) — which is exactly what we want.
    stats = analyze_project(str(run_dir.parent), run_dir.name)
    if not stats:
        return None

    # Optional: residual-TODO snapshot under <run_tag>/skeletons
    skel_dir = run_dir / "skeletons"
    todo_info = None
    if skel_dir.is_dir():
        todo_info = count_todos_in_skeletons(str(skel_dir))

    metrics = stats_to_metrics(stats, todo_info)
    metrics["run_tag"] = run_tag
    metrics["flag_label"] = FLAG_LABELS.get(run_tag, run_tag)
    return metrics


def generate_markdown_report(
    rows: list[dict],
    significance_rows: list[dict],
    project: str,
    model: str,
    temperature: str,
    suffix: str,
) -> str:
    """Render a Markdown ablation-comparison report.

    `rows` MUST include the baseline row first; otherwise percentages are
    computed against whichever row has run_tag == "baseline".
    """
    if not rows:
        return "No ablation data found.\n"

    by_tag = {r["run_tag"]: r for r in rows}
    base = by_tag.get("baseline", rows[0])

    lines: list[str] = []
    lines.append(f"# Fragment Translation Ablation Report")
    lines.append("")
    lines.append(
        f"- Project: `{project}`  |  Model: `{model}`  |  Temperature: `{temperature}`  |  Suffix: `{suffix!r}`"
    )
    lines.append(f"- Total runs compared: {len(rows)}")
    baseline_coverage = "✓ present" if "baseline" in by_tag else "✗ MISSING (using {0} as reference)".format(
        base["run_tag"]
    )
    lines.append(f"- Baseline coverage: {baseline_coverage}")
    lines.append("")
    lines.append("## Metrics summary")
    lines.append("")
    lines.append("")
    lines.append("| Run tag | Flags | Total | Completed | % | Compiled | % | Test pass | Tests/Compiled | TODOs | TODOs/file | Elapsed mean(s) |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    for r in rows:
        lines.append(
            f"| `{r['run_tag']}` | {r['flag_label']} | "
            f"{r['total_fragments']} | {r['completed']} | {_fmt_pct(r['completed_rate'])} | "
            f"{r['compiled_pass']} | {_fmt_pct(r['compiled_pass_rate'])} | "
            f"{r['test_pass']} | {_fmt_pct(r['test_pass_rate_of_compiled'])} | "
            f"{r['residual_todos']} | {r.get('residual_todos_per_file', 0.0):.2f} | "
            f"{r['elapsed_mean_s']:.2f} |"
        )

    lines.append("")
    lines.append("## Deltas vs baseline")
    lines.append("")
    lines.append(
        "| Run tag | Δ Completed | Δ Completed rate | Δ Compiled | Δ Compiled rate | "
        "Δ Test pass | Δ Test pass rate | Δ TODOs | Δ Elapsed mean(s) |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")

    for r in rows:
        if r["run_tag"] == "baseline":
            continue
        lines.append(
            f"| `{r['run_tag']}` | "
            f"{_fmt_delta(r['completed'], base['completed'])} | "
            f"{_fmt_delta(r['completed_rate'], base['completed_rate'], is_rate=True)} | "
            f"{_fmt_delta(r['compiled_pass'], base['compiled_pass'])} | "
            f"{_fmt_delta(r['compiled_pass_rate'], base['compiled_pass_rate'], is_rate=True)} | "
            f"{_fmt_delta(r['test_pass'], base['test_pass'])} | "
            f"{_fmt_delta(r['test_pass_rate_of_compiled'], base['test_pass_rate_of_compiled'], is_rate=True)} | "
            f"{_fmt_delta(r['residual_todos'], base['residual_todos'])} | "
            f"{_fmt_delta(r['elapsed_mean_s'], base['elapsed_mean_s'])} |"
        )

    # Part-wise pairs (for each Part alone vs baseline)
    lines.append("")
    lines.append("## Per-part isolated effect (single-Part runs vs baseline)")
    lines.append("")
    for tag in ("pseudo", "grammar", "syntax"):
        r = by_tag.get(tag)
        if not r:
            continue
        lines.append(f"### {tag} (`{r['flag_label']}`)")
        lines.append("")
        lines.append(
            f"- Completed: {base['completed']} → {r['completed']} "
            f"({_fmt_delta(r['completed'], base['completed'])}, "
            f"rate {base['completed_rate']:.1%} → {r['completed_rate']:.1%})"
        )
        lines.append(
            f"- Compiled pass: {base['compiled_pass']} → {r['compiled_pass']} "
            f"({_fmt_delta(r['compiled_pass'], base['compiled_pass'])}, "
            f"rate {base['compiled_pass_rate']:.1%} → {r['compiled_pass_rate']:.1%})"
        )
        lines.append(
            f"- Test pass (of compiled): {base['test_pass']} → {r['test_pass']} "
            f"({_fmt_delta(r['test_pass'], base['test_pass'])}, "
            f"rate {base['test_pass_rate_of_compiled']:.1%} → {r['test_pass_rate_of_compiled']:.1%})"
        )
        lines.append(
            f"- Residual TODOs: {base['residual_todos']} → {r['residual_todos']} "
            f"({_fmt_delta(r['residual_todos'], base['residual_todos'])})"
        )
        lines.append("")

    # Significance table
    if significance_rows:
        lines.append("## Significance (Fisher's exact two-sided p, vs baseline)")
        lines.append("")
        lines.append(
            "| Run tag | Metric | baseline | alternative | odds-ratio | p-value | significant (p<0.05) |"
        )
        lines.append("|---|---|---:|---:|---:|---:|:---:|")
        for sr in significance_rows:
            sig = "✓" if sr["p_value"] is not None and sr["p_value"] < 0.05 else "—"
            pval = f"{sr['p_value']:.4f}" if sr["p_value"] is not None else "n/a"
            orval = f"{sr['odds_ratio']:.2f}" if sr["odds_ratio"] is not None else "n/a"
            lines.append(
                f"| `{sr['run_tag']}` | {sr['metric']} | "
                f"{sr['baseline_pass']}/{sr['baseline_total']} | "
                f"{sr['alt_pass']}/{sr['alt_total']} | {orval} | {pval} | {sig} |"
            )

    # Per-Part additivity sanity
    pairs_two = ("pseudo+grammar", "pseudo+syntax", "grammar+syntax")
    if "baseline" in by_tag and all(p in by_tag for p in pairs_two):
        lines.append("")
        lines.append("## Pairwise ablation (two-Part combinations)")
        lines.append("")
        lines.append("| Run tag | Δ Completed | Δ Compiled | Δ Test pass | Δ TODOs | Δ Elapsed(s) |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for tag in pairs_two:
            r = by_tag[tag]
            lines.append(
                f"| `{r['run_tag']}` | "
                f"{_fmt_delta(r['completed'], base['completed'])} | "
                f"{_fmt_delta(r['compiled_pass'], base['compiled_pass'])} | "
                f"{_fmt_delta(r['test_pass'], base['test_pass'])} | "
                f"{_fmt_delta(r['residual_todos'], base['residual_todos'])} | "
                f"{_fmt_delta(r['elapsed_mean_s'], base['elapsed_mean_s'])} |"
            )

    # Notes section
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append("- **completed** = translation_status == 'completed' (compile + test-validation passed if enabled).")
    lines.append("- **compiled_pass** = cangjie_compilation.outcome == 'success'.")
    lines.append("- **test_pass** = test_execution.outcome in ('success','no-tests','not-exercised'); "
                 "rate computed **of compiled-pass pool** (compile is a precondition for tests).")
    lines.append("- **residual_todos** = count of `throw Exception('TODO')` in the run's .cj snapshot; "
                 "lower is better. Available only if `--skeleton-snapshots` was passed during run.")
    lines.append("- **elapsed_mean_s** = average elapsed_time per fragment across this run.")
    lines.append("- **Δ vs baseline** — deltas use absolute counts for integer metrics, and "
                 "**percentage-point (pp)** deltas for rate metrics.")
    lines.append("- **Significance**: Fisher's exact two-sided p (pure-python hypergeometric; "
                 "no scipy required). Marked ✓ when p < 0.05. The 2x2 table is "
                 "[pass, fail] x [baseline, alternative], with totals row/column fixed.")
    lines.append("- **Ablation runs MUST each be a separate copy of the schema dir** because "
                 "translate_fragment.sh overwrites the same schema JSON files between runs. Use "
                 "`scripts/java/run_ablation.sh` to snapshot automatically; see "
                 "`docs/fragment_translation_enhancements.md` for the full procedure.")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Significance: run Fisher's exact pass-rate test for each non-baseline run
# ---------------------------------------------------------------------------

def _significance_table(pass_count: int, fail_count: int, base_pass: int, base_fail: int):
    """Given pass/fail counts for the alternative run and the baseline,
    perform Fisher's exact 2x2 test. `fail_count` here means
    total - pass_count (so 'pending'/'out_of_context' / compile-fail all count as failures).

    Returns (odds_ratio, p_value, base_total, alt_total) — a 4-tuple that
    the caller unpacks uniformly. Returns (None, None, base_total, alt_total)
    if degenerate; (nan, 1.0, base_total, alt_total) on internal error.
    """
    base_total = base_pass + base_fail
    alt_total = pass_count + fail_count
    if base_total == 0 or alt_total == 0:
        return None, None, base_total, alt_total
    try:
        # 2x2 table convention:
        #   row 0 = baseline (pass, fail)
        #   row 1 = alternative (pass, fail)
        or_ratio, p_two = fisher_exact_2x2(
            ((base_pass, base_fail), (pass_count, fail_count))
        )
    except Exception:
        return float("nan"), 1.0, base_total, alt_total
    return or_ratio, p_two, base_total, alt_total


def compute_significance(rows: list[dict], metric_keys: list[tuple[str, str]]) -> list[dict]:
    """For each (run_tag, metric) pair test against baseline using Fisher's exact.

    `metric_keys` is a list of (run_tag, metric_field) pairs to test. The
    baseline is the row with run_tag == 'baseline'.

    For each metric (counts), `pass_count` = the metric value, `fail_count` =
    `total_fragments - pass_count`. Test result is captured in the report.
    """
    by_tag = {r["run_tag"]: r for r in rows}
    base = by_tag.get("baseline")
    if not base:
        return []
    base_total = base.get("total_fragments", 0) or 0
    if base_total == 0:
        return []

    out = []
    for run_tag, metric in metric_keys:
        r = by_tag.get(run_tag)
        if not r:
            continue
        alt_pass = r.get(metric, 0) or 0
        alt_total = r.get("total_fragments", 0) or 0
        alt_fail = alt_total - alt_pass
        base_pass = base.get(metric, 0) or 0
        base_fail = base_total - base_pass
        or_val, p_val, bt, at = _significance_table(
            alt_pass, alt_fail, base_pass, base_fail
        )
        out.append({
            "run_tag": run_tag,
            "metric": metric,
            "baseline_pass": base_pass,
            "baseline_total": bt,
            "alt_pass": alt_pass,
            "alt_total": at,
            "odds_ratio": or_val,
            "p_value": p_val,
        })
    return out


# ---------------------------------------------------------------------------
# CSV writer
# ---------------------------------------------------------------------------

def write_csv(rows: list[dict], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=HEADER_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Ablation comparison for Part 1/2/3 enhancement flags."
    )
    parser.add_argument("--project", required=True, help="Project name (e.g. jansi)")
    parser.add_argument("--model", required=True, help="Model name (e.g. deepseek-chat)")
    parser.add_argument("--temperature", required=True, help="Temperature (e.g. 0.0)")
    parser.add_argument("--suffix", default="", help="Schema suffix (default: empty)")
    parser.add_argument(
        "--ablation-root",
        required=True,
        help="Subdirectory containing run-tag subdirs (baseline/, pseudo/, grammar/, syntax/, "
        "pseudo+grammar/, pseudo+syntax/, grammar+syntax/, all/)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Markdown report output path (default: <ablation-root>/report.md)",
    )
    parser.add_argument(
        "--csv",
        default=None,
        help="CSV metrics output path (default: <ablation-root>/metrics.csv)",
    )
    parser.add_argument(
        "--skip-significance",
        action="store_true",
        help="Skip Fisher's exact significance test (use when fragment counts are very small)",
    )
    args = parser.parse_args()

    ablation_root = Path(args.ablation_root)
    if not ablation_root.is_dir():
        print(f"Error: ablation root not found: {ablation_root}", file=sys.stderr)
        sys.exit(1)

    rows: list[dict] = []
    missing_tags: list[str] = []
    present_tags: list[str] = []
    for tag in RUN_TAGS:
        metrics = _load_run(ablation_root, tag)
        if metrics is None:
            missing_tags.append(tag)
        else:
            present_tags.append(tag)
            rows.append(metrics)

    if not rows:
        print(f"Error: no run-tag subdirectories found under {ablation_root}", file=sys.stderr)
        sys.exit(1)

    if missing_tags:
        print(f"[WARN] Missing run tags: {', '.join(missing_tags)}", file=sys.stderr)

    # Significance test — compare each single-Part run / pairwise / all vs baseline
    significance_rows: list[dict] = []
    if not args.skip_significance and "baseline" in {r["run_tag"] for r in rows}:
        # Build (run_tag, metric) test list; only test compile and test pass-rate
        # (well-defined binary outcomes). Doesn't test TODOs / elapsed (continuous).
        test_plan = []
        for tag in RUN_TAGS:
            if tag == "baseline":
                continue
            for metric in ("compiled_pass", "test_pass", "completed"):
                test_plan.append((tag, metric))
        significance_rows = compute_significance(rows, test_plan)

    md = generate_markdown_report(
        rows,
        significance_rows,
        args.project,
        args.model,
        args.temperature,
        args.suffix,
    )

    out_md = Path(args.output) if args.output else ablation_root / "report.md"
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    print(f"✓ Markdown report written to: {out_md}")

    out_csv = Path(args.csv) if args.csv else ablation_root / "metrics.csv"
    write_csv(rows, out_csv)
    print(f"✓ CSV metrics written to:   {out_csv}")

    if significance_rows:
        sig_path = ablation_root / "significance.csv"
        with open(sig_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(
                f,
                fieldnames=["run_tag", "metric", "baseline_pass", "baseline_total",
                            "alt_pass", "alt_total", "odds_ratio", "p_value"],
            )
            w.writeheader()
            for sr in significance_rows:
                w.writerow(sr)
        print(f"✓ Significance CSV written to: {sig_path}")


if __name__ == "__main__":
    main()
