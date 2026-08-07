"""
Part 3: Syntax-graph RAG (control-flow + data-flow structural retrieval).

Inspired by *CodeGRAG: Extracting Composed Syntax Graphs for Retrieval
Augmented Cross-Lingual Code Generation* (Huang et al., 2024). The original
CodeGRAG builds full CFG+DFG via a GNN and pretrained cross-lingual code
search model; that requires non-trivial infra. This module ships a *pragmatic
approximation*: a lightweight, regex-based structural fingerprint (set of
control-flow signature tokens + call site signature tokens + field-access
signature tokens) extracted both from Java fragments and from Cangjie corpus
snippets, plus a Jaccard-similarity retrieval over a pickled index.

Why this is enough for our use case:
  - We only need to nudge the translator toward *idiomatic Cangjie snippets
    whose structure roughly matches the Java fragment's structure* — we are not
    claiming exact isomorphism of CFGs.
  - Light extraction lets us index CangjieCorpus without a Cangjie tree-sitter
    grammar (which we do not have) and to query with Java fragments without
    rerolling the existing pipeline.

Actually building a Cangjie tree-sitter grammar, training a GNN, etc. is
out-of-scope; this module is intentionally non-ML so it can run offline, with
no CUDA / no extra deps beyond what environment.yaml already pins (pickle,
pathlib, datasketch).

Files written:
  data/java/rag/syntax_graph_index.pkl  (pickled dict: {signature -> [Chunk]})
  data/java/rag/syntax_graph_corpus.jsonl  (human-readable copy for debugging)

Public API:
    build_syntax_graph_index(corpus_root, out_path)  -> int  (chunks indexed)
    get_syntax_graph_rag() -> _SyntaxGraphRAG       (singleton retriever)
    infer_structural_signature(code) -> frozenset[str]
        Public so the prompt side can compute a Java fragment's signature.

Flag-driven: only invoked when `--use_syntax_rag true` is set, otherwise the
retriever short-circuits and returns "".
"""

from __future__ import annotations

import json
import os
import pickle
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from datasketch import MinHash, MinHashLSH
except Exception:  # datasketch is in environment.yaml; tolerate mis-imports at module load
    MinHash = None
    MinHashLSH = None


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

# syntax_graph.py is at <repo>/src/java/rag/syntax_graph.py, so parents[3] is the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_INDEX_PATH = _REPO_ROOT / "data" / "java" / "rag" / "syntax_graph_index.pkl"
_DEFAULT_CORPUS_ROOT = _REPO_ROOT / "misc" / "CangjieCorpus"


# Control-flow signature tokens — captured verbatim from the code, lowercased.
# We deliberately include both Java and Cangjie keyword forms so the *same*
# extractor works on either language; similarity becomes cross-lingual natively.
_CF_TOKENS = {
    "if", "else", "else if", "while", "for", "do", "switch", "case",
    "default", "break", "continue", "return", "throw", "try", "catch",
    "finally", "match", "return if", "loop", "when",
}

# Field-access / call-site signature tokens. We capture the *operator-level*
# shape (method-call, array-index, field-access, new/allocation, assignment,
# binary-op) rather than the specific identifier — structural, not lexical.
_CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
_INDEX_RE = re.compile(r"\[\s*[^]]+\s*\]")
_FIELD_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\.\s*([A-Za-z_]\w*)")
_NEW_RE = re.compile(r"\bnew\s+([A-Za-z_]\w*)")
_ASSIGN_RE = re.compile(r"=")
# Lambda / closure arrow forms — counted via `code.count()` below,
# not via this regex (which is kept for potential future use / introspection).
_LAMBDA_RE = re.compile(r"->|=>")

# Structural shape buckets — each captured occurrence increments a count; counts
# are normalised to relative ranks when computing similarity (see below).
_SHAPE_KEYS = (
    "cf_if", "cf_loop", "cf_switch_match", "cf_return", "cf_throw",
    "cf_try_catch", "op_call", "op_index", "op_field_access",
    "op_new_alloc", "op_assign", "op_lambda",
)


# ---------------------------------------------------------------------------
# Lightweight structural signature
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StructSig:
    """A structural fingerprint of a code snippet.

    Fields are frozensets / tuples so the dataclass is hashable and usable as
    a dict key / datasketch MinHash input.
    """
    # Bag-of-shape-counts: each element is "<shape>:N" where N is bucketed:
    # 0=absent, 1=single, 2=few (2-4), 3=many (>=5).
    shape_bag: frozenset[str]
    # Distinct method-call site names (lexical, but cross-lingual overlap on
    # idiomatic APIs like `println`, `add`, `put`, `get`, `size`, `length`,
    # `map`, `filter`, `forEach` — we keep them to encourage *idiomatic*
    # retrieval rather than purely structural).
    call_names: frozenset[str]
    # Distinct type names that look like containers (end with common suffixes).
    container_types: frozenset[str]
    # Source-path category label if known (e.g. "std", "manual"); "" if unknown.
    category: str = ""


def _bucket(count: int) -> str:
    if count <= 0:
        return "0"
    if count == 1:
        return "1"
    if count <= 4:
        return "2"
    return "3"


def _extract_container_types(code: str) -> set[str]:
    # Match `Identifier<...>` or `Identifier` after `:`-typed positions; we
    # only care about the *base* identifier, lowercased, and only keep the ones
    # that look like containers (contain a common collection suffix).
    out: set[str] = set()
    for m in re.finditer(r"\b([A-Za-z_]\w*)(?:\s*<[^>]*>)?\s*[:\[\]\.]", code):
        name = m.group(1).lower()
        if name in {
            "list", "array", "arraylist", "linkedlist", "vector",
            "map", "hashmap", "treemap", "linkedhashmap", "concurrenthashmap",
            "set", "hashset", "treeset", "linkedhashset",
            "queue", "deque", "arraydeque", "priorityqueue",
            "iterator", "iterable",
        }:
            out.add(name)
    return out


def _count_cf(code: str, keyword: str | tuple[str, ...]) -> int:
    if isinstance(keyword, tuple):
        return sum(len(re.findall(rf"\b{re.escape(k)}\b", code)) for k in keyword)
    return len(re.findall(rf"\b{re.escape(keyword)}\b", code))


def infer_structural_signature(code: str, category: str = "") -> StructSig:
    """Compute the structural fingerprint of a Java *or* Cangjie snippet.

    The extractor is intentionally language-agnostic: it merges Java and
    Cangjie keyword forms (`switch` + `match`, `for`/`while` both). This is
    what makes cross-lingual structural retrieval work without a separate
    Cangjie tree-sitter grammar.
    """
    if not code:
        return StructSig(frozenset(), frozenset(), frozenset(), category)
    code_lower = code  # keep original case for identifier extraction below

    shape_counts: dict[str, int] = {k: 0 for k in _SHAPE_KEYS}
    shape_counts["cf_if"] = _count_cf(code_lower, "if")
    shape_counts["cf_loop"] = _count_cf(code_lower, ("for", "while", "loop"))
    shape_counts["cf_switch_match"] = _count_cf(
        code_lower, ("switch", "case", "match", "when"))
    shape_counts["cf_return"] = _count_cf(code_lower, "return")
    shape_counts["cf_throw"] = _count_cf(
        code_lower, ("throw", "raise"))
    shape_counts["cf_try_catch"] = _count_cf(
        code_lower, ("try", "catch", "finally"))
    shape_counts["op_call"] = len(_CALL_RE.findall(code_lower))
    shape_counts["op_index"] = len(_INDEX_RE.findall(code_lower))
    shape_counts["op_field_access"] = len(_FIELD_RE.findall(code_lower))
    shape_counts["op_new_alloc"] = len(_NEW_RE.findall(code_lower)) + code.count(".of(") + code.count(".from(")
    shape_counts["op_assign"] = code.count("=")
    # Treat both Java `->` and Cangjie `=>` as a lambda/closure marker.
    shape_counts["op_lambda"] = code.count("->") + code.count("=>")

    shape_bag = frozenset(
        f"{k}:{_bucket(v)}" for k, v in shape_counts.items() if v > 0
    )

    call_names: set[str] = set()
    for m in _CALL_RE.findall(code_lower):
        n = m.lower()
        # Skip bare control keywords masquerading as calls (`if (`, `for (`).
        if n in _CF_TOKENS:
            continue
        call_names.add(n)

    container_types = _extract_container_types(code_lower)

    return StructSig(shape_bag, frozenset(call_names), frozenset(container_types), category)


# ---------------------------------------------------------------------------
# Corpus scanning — CangjieCorpus .cj examples (and .cangjie, .cj.txt aliases)
# ---------------------------------------------------------------------------

_CANGJIE_CODE_EXTS = (".cj", ".cangjie", ".cj.txt")
_FENCE_RE = re.compile(r"```(?:cangjie|cj|cangjie-lang)?\s*\n(.*?)```", re.DOTALL)


@dataclass
class SyntaxChunk:
    sig: StructSig
    code: str
    source: str   # path relative to corpus_root, plus a "#snippet-N" suffix


def _iter_cangjie_code_blocks(corpus_root: Path):
    """Yield (code, source_descriptor) pairs from the corpus."""
    # 1. Standalone .cj files
    for ext in _CANGJIE_CODE_EXTS:
        for f in corpus_root.rglob(f"*{ext}"):
            try:
                txt = f.read_text(encoding="utf-8")
            except Exception:
                continue
            # Split into functions/blocks at top-level `func ` boundaries so
            # the index has multiple smaller chunks rather than one huge file.
            for i, block in enumerate(re.split(r"\n(?=func |class |interface |enum )", txt)):
                block = block.strip()
                if len(block) < 40 or "func " not in block and "class " not in block:
                    continue
                rel = f.relative_to(corpus_root).as_posix()
                yield block, f"{rel}#top-{i}"
    # 2. Fenced code blocks inside Markdown docs in the corpus
    for f in corpus_root.rglob("*.md"):
        try:
            txt = f.read_text(encoding="utf-8")
        except Exception:
            continue
        for i, m in enumerate(_FENCE_RE.finditer(txt)):
            block = m.group(1).strip()
            if len(block) < 40:
                continue
            rel = f.relative_to(corpus_root).as_posix()
            yield block, f"{rel}#md-{i}"


def build_syntax_graph_index(
    corpus_root: str | Path | None = None,
    out_path: str | Path | None = None,
) -> int:
    """Scan CangjieCorpus and persist a structural-signature index.

    Returns the number of chunks indexed.
    """
    corpus_root = Path(corpus_root) if corpus_root else _DEFAULT_CORPUS_ROOT
    out_path = Path(out_path) if out_path else _DEFAULT_INDEX_PATH
    out_path.parent.mkdir(parents=True, exist_ok=True)

    chunks: list[SyntaxChunk] = []
    for code, source in _iter_cangjie_code_blocks(corpus_root):
        # Categorise by directory root under corpus — gives a coarse signal
        # about std/manual/etc.
        first_seg = source.split("/", 1)[0].lower()
        cat = ""
        if "std" in first_seg:
            cat = "std"
        elif "manual" in first_seg:
            cat = "manual"
        elif "tutorial" in first_seg or "quickstart" in first_seg:
            cat = "extra"
        sig = infer_structural_signature(code, cat)
        chunks.append(SyntaxChunk(sig=sig, code=code, source=source))

    with open(out_path, "wb") as f:
        pickle.dump(
            {"chunks": [{"sig": {"shape": list(c.sig.shape_bag),
                                 "calls": list(c.sig.call_names),
                                 "containers": list(c.sig.container_types),
                                 "category": c.sig.category},
                          "code": c.code, "source": c.source} for c in chunks]},
            f,
        )
    # Human-readable mirror, useful when debugging retrieval quality.
    mirror = out_path.with_suffix(".jsonl")
    with open(mirror, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(
                {"source": c.source,
                 "shape": sorted(c.sig.shape_bag),
                 "calls": sorted(c.sig.call_names),
                 "containers": sorted(c.sig.container_types),
                 "category": c.sig.category},
                ensure_ascii=False) + "\n")
    return len(chunks)


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


class _SyntaxGraphRAG:
    """Singleton retriever. Loads the pickled index on first .retrieve() call."""

    def __init__(self, index_path: str | Path | None = None):
        self.index_path = Path(index_path) if index_path else _DEFAULT_INDEX_PATH
        self._chunks: Optional[list[dict]] = None
        self._lock = threading.Lock()

    def _ensure_loaded(self):
        if self._chunks is not None:
            return
        with self._lock:
            if self._chunks is not None:
                return
            if not self.index_path.exists():
                # Build the index transparently on first use if corpus is present.
                if _DEFAULT_CORPUS_ROOT.exists():
                    try:
                        build_syntax_graph_index(_DEFAULT_CORPUS_ROOT, self.index_path)
                    except Exception:
                        self._chunks = []
                        return
                else:
                    self._chunks = []
                    return
            try:
                with open(self.index_path, "rb") as f:
                    data = pickle.load(f)
                self._chunks = data.get("chunks", [])
            except Exception:
                self._chunks = []

    def retrieve(self, java_code: str, top_k: int = 3) -> list[dict]:
        """Return up to `top_k` corpus chunks whose structure resembles java_code."""
        self._ensure_loaded()
        if not java_code or not self._chunks:
            return []
        q = infer_structural_signature(java_code, "")
        scored = []
        for c in self._chunks:
            sig_shapes = frozenset(c["sig"]["shape"])
            sig_calls = frozenset(c["sig"]["calls"])
            sig_ctn = frozenset(c["sig"]["containers"])
            shape_sim = _jaccard(q.shape_bag, sig_shapes)
            call_sim = _jaccard(q.call_names, sig_calls)
            ctn_sim = _jaccard(q.container_types, sig_ctn)
            score = 0.6 * shape_sim + 0.25 * call_sim + 0.15 * ctn_sim
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        # Drop near-zero overlaps so we only inject genuinely-similar snippets.
        return [c for s, c in scored[:top_k] if s >= 0.05]

    def format_for_prompt(self, chunks: list[dict]) -> str:
        if not chunks:
            return ""
        parts = []
        for i, c in enumerate(chunks, 1):
            src = c.get("source", "?")
            cat = c.get("sig", {}).get("category", "")
            tag = f"[{cat}] " if cat else ""
            parts.append(
                f"-- example {i} ({tag}{src}) --\n```\n{c['code'][:1200]}\n```"
            )
        return (
            "### Structural Examples (retrieved from CangjieCorpus)\n"
            "The following Cangjie snippets have control-flow / data-flow graphs "
            "that are structurally similar to the Java fragment being translated. "
            "Use them as idiomatic templates for HOW to render the logic in Cangjie "
            "— particularly the surrounding class skeleton, the function signature "
            "form, and the idiomatic use of match / let / for-in. Do NOT copy them "
            "verbatim; adapt to the actual types and API calls.\n\n"
            + "\n\n".join(parts)
        )

    def inject(self, java_code: str, top_k: int = 3) -> str:
        """Retrieve + format. Returns "" if disabled / no index / no matches."""
        if not java_code:
            return ""
        chunks = self.retrieve(java_code, top_k=top_k)
        return self.format_for_prompt(chunks)


# ---------------------------------------------------------------------------
# Singleton accessor — keeps import side-effects minimal
# ---------------------------------------------------------------------------

_singleton: Optional[_SyntaxGraphRAG] = None
_singleton_lock = threading.Lock()


def get_syntax_graph_rag() -> _SyntaxGraphRAG:
    global _singleton
    if _singleton is None:
        with _singleton_lock:
            if _singleton is None:
                _singleton = _SyntaxGraphRAG()
    return _singleton


def reset_syntax_graph_rag() -> None:
    """Reset the singleton — used by tests."""
    global _singleton
    _singleton = None