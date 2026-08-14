#!/usr/bin/env python3
"""
Error analysis for Java → Cangjie translation results.

Covers sections 4.1–4.6 of the run_jansi_translation guide:
  4.1  Translation result statistics
  4.2  Compilation validation (cjpm build)
  4.3  Common error pattern classification
  4.4  Per-fragment error detail extraction
  4.5  Residual TODO check in .cj skeleton files
  4.6  Translation log tracking

Usage:
    python -m src.java.analysis.analyze_errors \
        --project <project> --model <model> --temperature <temp> \
        [--suffix <suffix>] [--output <file>] [--skip-build]

Or via the shell wrapper:
    bash scripts/java/analyze_errors.sh <project> <model> <temp> [suffix]
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Error pattern taxonomy (§4.3)
# ---------------------------------------------------------------------------

# (regex_pattern, category_name, description)
COMPILATION_ERROR_PATTERNS = [
    # Type / naming errors
    (r"undefined identifier|undeclared identifier|cannot find symbol|no such variable|variable .* not found", "undefined_identifier", "Referenced name not found in scope"),
    (r"type mismatch|type .* is not a subtype of|cannot convert", "type_mismatch", "Type assignment incompatibility"),
    (r"expected type .* found type", "type_mismatch", "Type assignment incompatibility"),
    (r"argument count mismatch|parameter count mismatch|too many arguments|too few arguments", "arg_count_mismatch", "Wrong number of function/method arguments"),
    (r"member .* not found in|no member named|cannot access member", "member_not_found", "Accessing non-existent member on a type"),
    (r"cannot .* override|override.*not allowed|nothing to override|function .* has overload conflicts", "override_error", "Override / overload conflict errors"),
    (r"redeclare|redefinition|duplicate definition|duplicate declaration", "duplicate_decl", "Duplicate declarations in same scope"),
    # Syntax errors
    (r"expected .* found .* keyword 'init'|expected a func name after keyword 'func', found keyword 'init'", "init_keyword", "Using 'init' as function name (Cangjie keyword)"),
    (r"unexpected class declaration in function body", "nested_class_error", "Class declaration inside function body"),
    (r"expected a func name|expected identifier|unexpected token", "syntax_error", "General syntax error"),
    (r"expected .* but got|expected .* found", "syntax_error", "General syntax error"),
    (r"unterminated|string literal|invalid escape", "syntax_error", "General syntax error"),
    (r"';' expected|expected ';' after", "syntax_error", "General syntax error"),
    # Import / package errors
    (r"import.*not found|cannot import|package .* not found|unresolved import", "import_error", "Missing or wrong import"),
    (r"ambiguous import|duplicate import", "import_error", "Missing or wrong import"),
    # Semantic errors
    (r"missing return|not all paths return", "missing_return", "Function missing return statement"),
    (r"unreachable code|dead code", "unreachable_code", "Unreachable code after return/throw"),
    (r"unused variable|unused import|unused parameter", "unused_warning", "Unused declarations (treated as error by -Woff unused)"),
    (r"cannot assign to|assign.*immutable|cannot modify immutable|value .* is not assignable", "mutability_error", "Assigning to immutable variable/let binding"),
    (r"throw.*not in try|uncaught exception|must be caught", "exception_error", "Unhandled exception / throw outside try"),
    (r"pattern match.*exhaustive|match.*not exhaustive", "match_error", "Non-exhaustive pattern matching"),
    (r"cycle.*detected|circular dependency|recursive type", "cycle_error", "Circular reference detected"),
    # Cangjie-specific
    (r"AnyHashable|Hashable.*not satisfied|Equatable.*not satisfied|not Hashable|does not conform to Hashable", "hashable_error", "HashMap/HashSet key type not satisfying Hashable/Equatable"),
    (r"func.*requires.*body|abstract.*cannot have body", "abstract_body_error", "Abstract vs concrete function body mismatch"),
    (r"constructor.*cannot.*return|init.*cannot.*return", "constructor_error", "Constructor (init) misused"),
    (r"open.*class.*cannot.*inherit|cannot extend.*final|cannot inherit from", "inheritance_error", "Inheritance restriction violation"),
    (r"enum.*not supported|undeclared type name 'Enum'", "enum_error", "Java Enum not mapped to Cangjie enum"),
    # CJPM build errors
    (r"cjpm build failed|failed to compile package", "build_error", "Package-level build failure"),
    (r"linker error|link.*failed|undefined reference", "link_error", "Link-time error"),
]

TEST_ERROR_PATTERNS = [
    (r"assert.*failed|assertion.*failed|assertEquals.*failed", "assertion_failure", "Test assertion did not hold"),
    (r"Exception|runtime error|panic|out of bounds|null pointer|IndexOutOfBoundsException", "runtime_exception", "Runtime crash / unhandled exception"),
    (r"timeout|timed out", "timeout", "Test execution timed out"),
]


def categorize_error(message: str, patterns: list) -> str:
    """Match an error message against known patterns; return category or 'other'."""
    if not message:
        return "empty_message"
    msg_lower = message.lower()
    for pattern, category, _desc in patterns:
        if re.search(pattern, msg_lower):
            return category
    return "other"


def extract_error_snippet(message: str, max_len: int = 300) -> str:
    """Extract the most relevant part of a compilation error message."""
    if not message:
        return ""
    lines = []
    for line in message.split("\n"):
        stripped = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        if stripped and not stripped.startswith("error: failed to compile") and not stripped.startswith("error: cjpm build failed"):
            lines.append(stripped)
    # Find lines that start with 'error:' or contain ==> (file location)
    error_lines = [l for l in lines if l.startswith("error:") or " ==> " in l or "unexpected" in l.lower() or "expected" in l.lower()]
    if error_lines:
        return "\n".join(error_lines[:3])[:max_len]
    return "\n".join(lines[:3])[:max_len]


# ---------------------------------------------------------------------------
# §4.1 Translation result statistics + §4.4 Per-fragment error detail
# ---------------------------------------------------------------------------

def analyze_project(translation_dir: str, project: str) -> dict:
    """
    Scan all schema JSON files for *project* under *translation_dir* and
    return a structured analysis dict.
    """
    project_dir = Path(translation_dir) / project
    if not project_dir.is_dir():
        print(f"[WARN] Directory not found: {project_dir}", file=sys.stderr)
        return {}

    stats = {
        "project": project,
        "total_fragments": 0,
        "by_type": Counter(),
        "by_status": Counter(),
        "compilation": Counter(),
        "test_execution": Counter(),
        "compilation_error_examples": defaultdict(list),
        "test_error_examples": defaultdict(list),
        "elapsed_time_total": 0.0,
        "elapsed_by_status": {"completed": 0.0, "failed": 0.0, "other": 0.0},
        "fragments": [],
    }

    json_files = sorted(project_dir.glob("*.json"))
    if not json_files:
        print(f"[WARN] No JSON files found in {project_dir}", file=sys.stderr)
        return {}

    for json_path in json_files:
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load {json_path.name}: {e}", file=sys.stderr)
            continue

        schema_name = json_path.stem
        classes = schema.get("classes", {})

        for class_key, class_info in classes.items():
            for frag_type in ("methods", "fields", "static_initializers"):
                fragments = class_info.get(frag_type, {})
                if not isinstance(fragments, dict):
                    continue
                for frag_key, frag_data in fragments.items():
                    if not isinstance(frag_data, dict):
                        continue

                    stats["total_fragments"] += 1
                    stats["by_type"][frag_type] += 1

                    t_status = frag_data.get("translation_status", "pending")
                    stats["by_status"][t_status] += 1

                    # Compilation status
                    comp = frag_data.get("cangjie_compilation", "pending")
                    if isinstance(comp, dict):
                        outcome = comp.get("outcome", "unknown")
                        message = comp.get("message", "")
                        if outcome == "success":
                            stats["compilation"]["success"] += 1
                        elif outcome == "error":
                            cat = categorize_error(message, COMPILATION_ERROR_PATTERNS)
                            stats["compilation"][cat] += 1
                            snippet = extract_error_snippet(message)
                            stats["compilation_error_examples"][cat].append({
                                "schema": schema_name,
                                "class": class_key,
                                "fragment": frag_key,
                                "type": frag_type,
                                "snippet": snippet,
                                "full_message": message[:500],
                            })
                        else:
                            stats["compilation"][outcome] += 1
                    else:
                        stats["compilation"][str(comp)] += 1

                    # Test execution status
                    test = frag_data.get("test_execution", "pending")
                    if isinstance(test, dict):
                        t_outcome = test.get("outcome", "unknown")
                        t_message = test.get("message", "")
                        if t_outcome in ("success", "no-tests", "not-exercised"):
                            stats["test_execution"][t_outcome] += 1
                        else:
                            cat = categorize_error(t_message, TEST_ERROR_PATTERNS + COMPILATION_ERROR_PATTERNS)
                            stats["test_execution"][cat] += 1
                            snippet = extract_error_snippet(t_message)
                            stats["test_error_examples"][cat].append({
                                "schema": schema_name,
                                "class": class_key,
                                "fragment": frag_key,
                                "type": frag_type,
                                "snippet": snippet,
                            })
                    else:
                        stats["test_execution"][str(test)] += 1

                    # Elapsed time
                    elapsed = frag_data.get("elapsed_time", 0) or 0
                    stats["elapsed_time_total"] += elapsed
                    if t_status == "completed":
                        stats["elapsed_by_status"]["completed"] += elapsed
                    elif isinstance(comp, dict) and comp.get("outcome") != "success":
                        stats["elapsed_by_status"]["failed"] += elapsed
                    else:
                        stats["elapsed_by_status"]["other"] += elapsed

                    # Per-fragment row
                    frag_row = {
                        "schema": schema_name,
                        "class": class_key,
                        "fragment": frag_key,
                        "type": frag_type.rstrip("s"),
                        "translation_status": t_status,
                        "compilation_outcome": comp.get("outcome") if isinstance(comp, dict) else str(comp),
                        "test_outcome": test.get("outcome") if isinstance(test, dict) else str(test),
                        "elapsed_time": elapsed,
                        "compilation_message": "",
                        "test_message": "",
                    }
                    if isinstance(comp, dict):
                        frag_row["compilation_message"] = comp.get("message", "")[:200]
                    if isinstance(test, dict):
                        frag_row["test_message"] = test.get("message", "")[:200]
                    stats["fragments"].append(frag_row)

    return stats


# ---------------------------------------------------------------------------
# §4.2 Compilation validation (cjpm build)
# ---------------------------------------------------------------------------

def run_cjpm_build(skeleton_dir: str) -> str:
    """Run cjpm build in skeleton_dir and return the output."""
    if not Path(skeleton_dir).is_dir():
        return f"[SKIP] Skeleton directory not found: {skeleton_dir}"

    try:
        result = subprocess.run(
            ["cjpm", "build"],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=skeleton_dir,
        )
        output = result.stdout + "\n" + result.stderr
        return output.strip() if output.strip() else "(no output)"
    except FileNotFoundError:
        return "[SKIP] cjpm not found on PATH"
    except subprocess.TimeoutExpired:
        return "[TIMEOUT] cjpm build timed out after 300s"


# ---------------------------------------------------------------------------
# §4.5 Residual TODO check in .cj skeleton files
# ---------------------------------------------------------------------------

def count_todos_in_skeletons(skeleton_dir: str) -> dict:
    """Count throw Exception('TODO') occurrences in .cj files under skeleton_dir."""
    skeleton_path = Path(skeleton_dir)
    if not skeleton_path.is_dir():
        return {"total_todos": 0, "files_with_todos": 0, "details": []}

    todo_pattern = re.compile(r"throw Exception\('TODO'\)")
    details = []
    total_todos = 0

    for cj_file in sorted(skeleton_path.rglob("*.cj")):
        try:
            content = cj_file.read_text(encoding="utf-8")
            count = len(todo_pattern.findall(content))
            if count > 0:
                rel_path = cj_file.relative_to(skeleton_path)
                details.append({"file": str(rel_path), "count": count})
                total_todos += count
        except Exception:
            continue

    return {
        "total_todos": total_todos,
        "files_with_todos": len(details),
        "details": details,
    }


# ---------------------------------------------------------------------------
# §4.6 Translation log tracking
# ---------------------------------------------------------------------------

def find_translation_logs(project: str, model: str) -> list:
    """Find translation log files matching the project + model pattern."""
    logs = []
    for pattern in [f"{project}_{model}_*.log", f"{project}_{model}_description.log"]:
        logs.extend(Path(".").glob(pattern))
    return sorted(set(logs), key=lambda p: p.stat().st_mtime, reverse=True)


def summarize_log(log_path: Path) -> dict:
    """Parse a translation log file for key events."""
    summary = {
        "path": str(log_path),
        "size_bytes": log_path.stat().st_size,
        "compile_pass": 0,
        "compile_fail": 0,
        "test_pass": 0,
        "test_fail": 0,
        "errors": [],
    }
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        # Count ✅ and ❌ in compile/test lines
        for line in content.splitlines():
            if "compile" in line.lower():
                if "✅" in line:
                    summary["compile_pass"] += 1
                elif "❌" in line:
                    summary["compile_fail"] += 1
            elif "test" in line.lower():
                if "✅" in line:
                    summary["test_pass"] += 1
                elif "❌" in line:
                    summary["test_fail"] += 1
            # Collect ERROR/FAILURE lines
            if "ERROR" in line or "FAILURE" in line:
                summary["errors"].append(line.strip()[:200])
    except Exception as e:
        summary["errors"].append(f"[Failed to read log: {e}]")
    return summary


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_report(stats: dict, cjpm_output: str, todo_info: dict, log_summaries: list) -> str:
    """Format analysis stats into a human-readable report string."""
    if not stats:
        return "No data found.\n"

    lines = []
    total = stats["total_fragments"]
    project = stats["project"]

    lines.append("=" * 80)
    lines.append(f"  TRANSLATION ERROR ANALYSIS REPORT: {project}")
    lines.append("=" * 80)

    # === TRANSLATION RESULT STATISTICS ===
    lines.append("")
    lines.append("=" * 80)
    lines.append("  TRANSLATION RESULT STATISTICS")
    lines.append("=" * 80)
    lines.append(f"  Total fragments:    {total}")
    by_status = stats["by_status"]
    for status in ("completed", "attempted", "out_of_context", "pending"):
        cnt = by_status.get(status, 0)
        if cnt:
            pct = cnt / total * 100 if total else 0
            lines.append(f"  {status:<22} {cnt:>5}  ({pct:5.1f}%)")

    if stats["elapsed_time_total"] > 0:
        lines.append(f"\n  Total elapsed time:  {stats['elapsed_time_total']:.1f}s")
        comp_time = stats["elapsed_by_status"]["completed"]
        fail_time = stats["elapsed_by_status"]["failed"]
        lines.append(f"    Completed:         {comp_time:.1f}s")
        lines.append(f"    Failed:            {fail_time:.1f}s")

    # === COMPILATION VALIDATION ===
    lines.append("")
    lines.append("=" * 80)
    lines.append("  COMPILATION VALIDATION (cjpm build)")
    lines.append("=" * 80)
    # Parse cjpm output for error lines
    cjpm_error_lines = []
    for line in cjpm_output.split("\n"):
        stripped = line.strip()
        if stripped.startswith("error:") or stripped.startswith("Error:"):
            cjpm_error_lines.append(stripped[:150])
    if "BUILD SUCCESS" in cjpm_output or "Compilation successful" in cjpm_output:
        lines.append("  ✅ cjpm build: SUCCESS")
    elif "BUILD FAILURE" in cjpm_output or cjpm_error_lines:
        lines.append("  ❌ cjpm build: FAILED")
        lines.append(f"  Total build errors: {len(cjpm_error_lines)}")
        for el in cjpm_error_lines[:10]:
            lines.append(f"    {el}")
        if len(cjpm_error_lines) > 10:
            lines.append(f"    ... and {len(cjpm_error_lines) - 10} more")
    else:
        lines.append(f"  {cjpm_output[:200]}")

    # === COMPILATION ERROR CATEGORIES ===
    lines.append("")
    lines.append("=" * 80)
    lines.append("  COMPILATION ERROR CATEGORIES")
    lines.append("=" * 80)
    comp = stats["compilation"]
    comp_total = sum(v for k, v in comp.items() if k != "pending")
    for cat, cnt in comp.most_common():
        pct = cnt / comp_total * 100 if comp_total else 0
        lines.append(f"  {cat:<28} {cnt:>5}  ({pct:5.1f}%)")

    # === Error category detail ===
    error_cats = {k: v for k, v in comp.items() if k not in ("success", "pending")}
    if error_cats:
        lines.append("")
        lines.append("=" * 80)
        lines.append("  TOP COMPILATION ERROR CATEGORIES (with examples)")
        lines.append("=" * 80)
        sorted_cats = sorted(error_cats.items(), key=lambda x: x[1], reverse=True)
        for cat, cnt in sorted_cats:
            examples = stats["compilation_error_examples"].get(cat, [])
            lines.append(f"")
            lines.append(f"  [{cat}] ×{cnt}")
            desc = next((d for p, c, d in COMPILATION_ERROR_PATTERNS if c == cat), "Uncategorized")
            lines.append(f"    Description: {desc}")
            for ex in examples[:5]:
                lines.append(f"    Example: {ex['schema']} / {ex['fragment']}")
                for line in ex["snippet"].split("\n")[:2]:
                    lines.append(f"      {line[:140]}")

    # === PER-FRAGMENT ERROR DETAIL ===
    lines.append("")
    lines.append("=" * 80)
    lines.append("  PER-FRAGMENT ERROR DETAIL")
    lines.append("=" * 80)
    failed_frags = [f for f in stats["fragments"] if f["compilation_outcome"] == "error"]
    if failed_frags:
        lines.append(f"  Failed fragments: {len(failed_frags)} / {total}")
        for f in failed_frags[:50]:
            msg_preview = f.get("compilation_message", "")[:100]
            lines.append(f"  {f['schema']} | {f['class'].split(':')[-1] if ':' in f['class'] else f['class']}.{f['fragment'].split(':')[-1] if ':' in f['fragment'] else f['fragment']} ({f['type']}) | {msg_preview}")
        if len(failed_frags) > 50:
            lines.append(f"  ... and {len(failed_frags) - 50} more")
    else:
        lines.append("  No failed fragments found.")

    # === RESIDUAL TODO IN .cj FILES ===
    lines.append("")
    lines.append("=" * 80)
    lines.append("  RESIDUAL TODO IN .cj FILES")
    lines.append("=" * 80)
    lines.append(f"  Total TODO placeholders:  {todo_info['total_todos']}")
    lines.append(f"  Files with TODOs:         {todo_info['files_with_todos']}")
    if todo_info["details"]:
        lines.append("")
        lines.append(f"  {'File':<55} {'TODOs':>5}")
        lines.append(f"  {'─' * 55} {'─' * 5}")
        for d in todo_info["details"][:30]:
            lines.append(f"  {d['file']:<55} {d['count']:>5}")
        if len(todo_info["details"]) > 30:
            lines.append(f"  ... and {len(todo_info['details']) - 30} more files")

    # === TRANSLATION LOG TRACKING ===
    lines.append("")
    lines.append("=" * 80)
    lines.append("  TRANSLATION LOG TRACKING")
    lines.append("=" * 80)
    if log_summaries:
        for ls in log_summaries:
            lines.append(f"  Log: {ls['path']}")
            lines.append(f"    Size: {ls['size_bytes'] / 1024:.1f} KB")
            lines.append(f"    Compile: ✅{ls['compile_pass']} ❌{ls['compile_fail']}  "
                         f"Test: ✅{ls['test_pass']} ❌{ls['test_fail']}")
            if ls["errors"]:
                lines.append(f"    Errors ({len(ls['errors'])}):")
                for e in ls["errors"][:5]:
                    lines.append(f"      {e[:150]}")
                if len(ls["errors"]) > 5:
                    lines.append(f"      ... and {len(ls['errors']) - 5} more")
    else:
        lines.append("  No translation log files found.")

    # === PER-FRAGMENT DATA (CSV) ===
    lines.append("")
    lines.append("=" * 80)
    lines.append("  PER-FRAGMENT DATA (CSV)")
    lines.append("=" * 80)
    lines.append("schema,class,fragment,type,translation_status,compilation_outcome,test_outcome,elapsed_time")
    for f in stats["fragments"]:
        lines.append(
            f"{f['schema']},{f['class']},{f['fragment']},{f['type']},"
            f"{f['translation_status']},{f['compilation_outcome']},{f['test_outcome']},{f['elapsed_time']:.2f}"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyze translation errors in schema JSON files (§4.1-4.6)"
    )
    parser.add_argument("--project", required=True, help="Project name (e.g. jansi)")
    parser.add_argument("--model", required=True, help="Model name (e.g. gpt-4o-2024-11-20)")
    parser.add_argument("--temperature", required=True, help="Temperature (e.g. 0.0)")
    parser.add_argument("--suffix", default="", help="Schema suffix (default: empty)")
    parser.add_argument("--output", default=None, help="Output file path (default: auto-generated)")
    parser.add_argument("--skip-build", action="store_true", help="Skip cjpm build validation (§4.2)")
    args = parser.parse_args()

    translation_dir = f"data/java/schemas{args.suffix}/{args.model}/{args.temperature}"
    if not Path(translation_dir).is_dir():
        print(f"Error: Translation directory not found: {translation_dir}", file=sys.stderr)
        sys.exit(1)

    # §4.1 + §4.4 Analyze schema JSON
    stats = analyze_project(translation_dir, args.project)
    if not stats:
        print("No data to analyze.", file=sys.stderr)
        sys.exit(1)

    # Compilation validation — prefer translations dir (actual translated files),
    # fall back to skeleton dir if translations don't exist
    skeleton_dir = f"data/java/skeletons/{args.project}"
    trans_skeleton_dir = f"data/java/skeletons/translations/{args.model}/{args.temperature}/{args.project}"
    build_dir = trans_skeleton_dir if Path(trans_skeleton_dir).is_dir() else skeleton_dir
    if args.skip_build:
        cjpm_output = "[SKIPPED] --skip-build flag set"
    else:
        cjpm_output = run_cjpm_build(build_dir)

    # Residual TODO — check both skeleton and translations dirs
    todo_info = count_todos_in_skeletons(skeleton_dir)
    if Path(trans_skeleton_dir).is_dir():
        trans_todo = count_todos_in_skeletons(trans_skeleton_dir)
        todo_info["translations_total_todos"] = trans_todo["total_todos"]
        todo_info["translations_files_with_todos"] = trans_todo["files_with_todos"]
        todo_info["details"].extend(
            {**d, "file": f"translations/{d['file']}"} for d in trans_todo["details"]
        )
        todo_info["total_todos"] += trans_todo["total_todos"]
        todo_info["files_with_todos"] += trans_todo["files_with_todos"]

    # §4.6 Log tracking
    log_summaries = []
    for log_path in find_translation_logs(args.project, args.model):
        log_summaries.append(summarize_log(log_path))

    # Format report
    report = format_report(stats, cjpm_output, todo_info, log_summaries)

    # Output
    output_path = args.output
    if not output_path:
        output_dir = Path("data/java/analysis")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{args.project}_{args.model}_{args.temperature}{args.suffix}_errors.txt")
    else:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"\nReport saved to: {output_path}")


if __name__ == "__main__":
    main()