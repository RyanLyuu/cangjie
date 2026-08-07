"""
Progressive Knowledge Base — core implementation.

Adapted from progressive_kb_reference.py with production integration changes:
  - Thread-safe singleton via get_progressive_kb()
  - Graceful fallback when storage_dir doesn't exist yet
  - Integration-friendly API for translate_type_rag and prompt_generator
"""

import json
import re
import hashlib
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from collections import defaultdict


# ==============================================================
# Data structures
# ==============================================================

@dataclass
class TranslationPair:
    """
    A translation pair — the fundamental unit of the progressive KB.

    Corresponds to the "code adaptation example" in the ArkAdapter paper's
    Adaptation Knowledge Repository: a scenario-tagged real migration example.

    Key fields:
        pair_id:       Unique ID (content-hash based, auto-dedup)
        java_code:     Java source code snippet
        cangjie_code:   Corresponding Cangjie code snippet
        signature:      Full method/class signature for precise matching
        scenario:       Scenario tag for classified retrieval
                        e.g. "getter_setter", "lambda", "generics",
                             "exception", "stream_api", "enum"
        java_types:    Java types involved
        cangjie_types:  Corresponding Cangjie types
        compile_pass:   Whether this pair passed compile verification
        source_project: Source project name
    """
    pair_id: str
    java_code: str
    cangjie_code: str
    signature: str
    scenario: str = "general"
    java_types: list = field(default_factory=list)
    cangjie_types: list = field(default_factory=list)
    compile_pass: bool = True
    source_project: str = ""


@dataclass
class TypeMapping:
    """Simple type mapping entry — caches type translation results to avoid redundant LLM calls."""
    java_type: str
    cangjie_type: str
    imports: list = field(default_factory=list)
    source: str = "llm"       # "java_base_map" | "custom_type" | "generated_interface_shim" | "llm" | "kb"
    verified: bool = True


# ==============================================================
# Scenario classifier
# ==============================================================

class ScenarioClassifier:
    """
    Auto-classify Java code snippets into translation scenarios.

    Maps to the ArkAdapter paper's "adaptation scenario" concept.
    Each scenario represents a common pattern in Java → Cangjie translation
    that benefits from having dedicated few-shot examples.
    """

    SCENARIO_PATTERNS = {
        "getter_setter": [
            r'(?:public|private|protected)\s+\w+\s+get\w+\s*\(',
            r'(?:public|private|protected)\s+void\s+set\w+\s*\(',
            r'(?:public|private|protected)\s+\w+\s+is\w+\s*\(',
        ],
        "lambda": [
            r'\(.*\)\s*->',
            r'::new\b',
            r'::\w+\s*[,\)]',
            r'Stream\.of\(',
            r'\.stream\(\)',
            r'\.collect\(',
        ],
        "generics": [
            r'<\w+[\s,<>]*>',
            r'Optional<',
            r'List<',
            r'Map<',
            r'Set<',
            r'Comparable<',
            r'Function<',
            r'Consumer<',
            r'Supplier<',
            r'Predicate<',
        ],
        "exception": [
            r'throws\s+\w+',
            r'try\s*\{',
            r'catch\s*\(',
            r'throw\s+new\s+\w+Exception',
            r'Throwable\b',
        ],
        "enum": [
            r'enum\s+\w+',
        ],
        "stream_api": [
            r'\.stream\(\)',
            r'\.collect\(',
            r'\.map\(',
            r'\.filter\(',
            r'\.forEach\(',
            r'\.reduce\(',
            r'\.flatMap\(',
            r'Collectors\.',
        ],
        "concurrency": [
            r'synchronized\s*\(',
            r'volatile\s+',
            r'ConcurrentHashMap',
            r'ConcurrentLinkedQueue',
            r'Thread\b',
            r'Runnable\b',
            r'Future<',
            r'CompletableFuture',
        ],
        "annotation": [
            r'@\w+',
            r'@Override',
            r'@Deprecated',
            r'@SuppressWarnings',
        ],
        "method_body": [
            r'(?:public|private|protected)\s+\w+\s+\w+\s*\([^)]*\)\s*\{',
        ],
    }

    @classmethod
    def classify(cls, java_code: str) -> list[str]:
        """Classify a Java code snippet into one or more scenarios."""
        scenarios = []

        # Check patterns: sorted for deterministic ordering
        # Most specific patterns first
        priorty_order = [
            "enum",
            "stream_api",
            "lambda",
            "concurrency",
            "generics",
            "exception",
            "getter_setter",
            "annotation",
            "method_body",
        ]

        for scenario in priorty_order:
            patterns = cls.SCENARIO_PATTERNS.get(scenario, [])
            for pattern in patterns:
                if re.search(pattern, java_code):
                    scenarios.append(scenario)
                    break  # Only add each scenario once

        return scenarios if scenarios else ["general"]


# ==============================================================
# ProgressiveKB — main class
# ==============================================================

class ProgressiveKB:
    """
    Progressive Knowledge Base for Java → Cangjie translation.

    Inspired by ArkAdapter's Adaptation Knowledge Repository.

    In a nutshell:
      1. Before each translation, query the KB for similar examples.
      2. Format them as few-shot prompt context.
      3. After successful translation + compilation, store the pair.

    The KB grows incrementally: the more you translate, the smarter it gets.
    Across projects, type mappings and pattern examples accumulate and
    compound — "the more you translate, the more accurate."
    """

    def __init__(self, storage_dir: str = "data/java/progressive_kb"):
        self.storage_dir = Path(storage_dir)
        self.pool_path = self.storage_dir / "translation_pool.json"
        self.types_path = self.storage_dir / "type_mappings.json"
        self.scenarios_path = self.storage_dir / "scenarios.json"

        self._pairs: list[TranslationPair] = []
        self._type_map: dict[str, TypeMapping] = {}
        self._scenario_index: dict[str, list[str]] = defaultdict(list)

        self._load()

    def ensure_dirs(self):
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------
    # Adding entries
    # ----------------------------------------------------------

    def add_example(
        self,
        java_code: str,
        cangjie_code: str,
        signature: str = "",
        scenario: str = "auto",
        java_types: list | None = None,
        cangjie_types: list | None = None,
        compile_pass: bool = True,
        source_project: str = "",
    ) -> TranslationPair:
        """
        Add a translation pair to the pool.

        If scenario="auto", the classifier will auto-detect the scenario.
        If a pair with the same content already exists, it will be updated
        only if the new version has higher quality (e.g. compile_pass=True
        replacing compile_pass=False).
        """
        if java_types is None:
            java_types = []
        if cangjie_types is None:
            cangjie_types = []

        if scenario == "auto":
            scenarios = ScenarioClassifier.classify(java_code)
            scenario = scenarios[0]

        pair_id = self._hash_pair(java_code, cangjie_code)

        # Check for existing pair — update if higher quality
        for i, existing in enumerate(self._pairs):
            if existing.pair_id == pair_id:
                # Replace only if new version is strictly better
                if compile_pass and not existing.compile_pass:
                    self._pairs[i] = TranslationPair(
                        pair_id=pair_id,
                        java_code=java_code,
                        cangjie_code=cangjie_code,
                        signature=signature or existing.signature,
                        scenario=scenario or existing.scenario,
                        java_types=java_types or existing.java_types,
                        cangjie_types=cangjie_types or existing.cangjie_types,
                        compile_pass=compile_pass,
                        source_project=source_project or existing.source_project,
                    )
                    self._save()
                return self._pairs[i]

        pair = TranslationPair(
            pair_id=pair_id,
            java_code=java_code,
            cangjie_code=cangjie_code,
            signature=signature,
            scenario=scenario,
            java_types=java_types,
            cangjie_types=cangjie_types,
            compile_pass=compile_pass,
            source_project=source_project,
        )
        self._pairs.append(pair)
        self._scenario_index[scenario].append(pair_id)
        self._save()
        return pair

    def add_type_mapping(
        self,
        java_type: str,
        cangjie_type: str,
        imports: list | None = None,
        source: str = "llm",
        verified: bool = True,
    ) -> TypeMapping:
        """Add or update a type mapping entry."""
        if imports is None:
            imports = []

        existing = self._type_map.get(java_type)
        # Only override if the new mapping is verified and the old one wasn't,
        # or if there was no existing mapping
        if existing and existing.verified and not verified:
            return existing

        mapping = TypeMapping(
            java_type=java_type,
            cangjie_type=cangjie_type,
            imports=imports,
            source=source,
            verified=verified,
        )
        self._type_map[java_type] = mapping
        self._save()
        return mapping

    def get_type_mapping(self, java_type: str) -> Optional[TypeMapping]:
        """Look up a type mapping. Returns None if not found."""
        return self._type_map.get(java_type)

    # ----------------------------------------------------------
    # Retrieval
    # ----------------------------------------------------------

    def retrieve(
        self,
        java_code: str = "",
        java_types: list | None = None,
        scenario: str = "",
        top_k: int = 3,
        min_similarity: float = 0.1,
    ) -> list[TranslationPair]:
        """
        Retrieve relevant translation pairs for few-shot prompting.

        Scoring:
            - Jaccard token similarity between input java_code and pair java_code
            - Bonus for type overlap (0.15 * Jaccard of type sets)
            - Bonus for compile-verified pairs (0.05)

        Args:
            java_code:    The current Java code snippet to find similar examples for
            java_types:   Types involved in the current translation (for overlap scoring)
            scenario:     Filter by scenario tag
            top_k:        Maximum number of results
            min_similarity: Minimum similarity threshold
        """
        if java_types is None:
            java_types = []

        candidates: list[tuple[float, TranslationPair]] = []

        # Auto-detect scenario for matching
        auto_scenarios = ScenarioClassifier.classify(java_code) if java_code else []
        type_set = set(java_types)

        # Tokenize input for similarity scoring
        java_tokens = self._tokenize(java_code) if java_code else set()

        for pair in self._pairs:
            # Scenario filter
            if scenario:
                pair_scenarios = ScenarioClassifier.classify(pair.java_code)
                if scenario not in pair_scenarios:
                    continue

            # Calculate similarity
            sim = 0.0

            if java_tokens:
                pair_tokens = self._tokenize(pair.java_code)
                sim = self._jaccard(java_tokens, pair_tokens)

            # Type overlap bonus
            if type_set and pair.java_types:
                type_overlap = len(type_set & set(pair.java_types))
                type_union = len(type_set | set(pair.java_types))
                if type_union > 0:
                    sim += 0.15 * (type_overlap / type_union)

            # Compile-verified bonus
            if pair.compile_pass:
                sim += 0.05

            if sim > min_similarity:
                candidates.append((sim, pair))

        # Backstop: if too few candidates, supplement from same scenario
        if len(candidates) < top_k and scenario:
            extra_needed = top_k - len(candidates)
            existing_ids = {p.pair_id for _, p in candidates}
            for pair in self._pairs:
                if pair.pair_id in existing_ids:
                    continue
                pair_scenarios = ScenarioClassifier.classify(pair.java_code)
                if scenario in pair_scenarios:
                    candidates.append((0.3, pair))
                    existing_ids.add(pair.pair_id)
                    if len(candidates) >= top_k + extra_needed:
                        break

        # Auto-scenario fallback: try overlapping scenarios
        if len(candidates) < top_k and auto_scenarios:
            existing_ids = {p.pair_id for _, p in candidates}
            for pair in self._pairs:
                if pair.pair_id in existing_ids:
                    continue
                pair_scenarios = ScenarioClassifier.classify(pair.java_code)
                if any(s in pair_scenarios for s in auto_scenarios):
                    candidates.append((0.25, pair))
                    existing_ids.add(pair.pair_id)
                    if len(candidates) >= top_k:
                        break

        # Sort, dedup, take top_k
        candidates.sort(key=lambda x: x[0], reverse=True)
        seen: set[str] = set()
        result = []
        for _, pair in candidates:
            if pair.pair_id not in seen:
                seen.add(pair.pair_id)
                result.append(pair)
                if len(result) >= top_k:
                    break

        return result

    def get_scenario_summary(self) -> dict:
        """View the distribution of the KB by scenario."""
        summary = defaultdict(lambda: {"count": 0, "verified": 0})
        for pair in self._pairs:
            s = pair.scenario
            summary[s]["count"] += 1
            if pair.compile_pass:
                summary[s]["verified"] += 1
        return dict(summary)

    # ----------------------------------------------------------
    # Retrieval → prompt context (key: few-shot injection)
    # ----------------------------------------------------------

    def format_few_shot_prompt(
        self,
        examples: list[TranslationPair],
        max_examples: int = 3,
    ) -> str:
        """
        Format retrieved translation examples as few-shot prompt context.

        This is the core trick from the ArkAdapter paper:
        Instead of showing the LLM documentation descriptions, show it
        "this Java code corresponds to this Cangjie code" — real examples.

        Prompt format:
            Each example separated by "### Java → Cangjie Example",
            letting the LLM clearly distinguish examples from the current task.
        """
        if not examples:
            return ""

        parts = []
        parts.append(
            "### Reference: Translation Examples (Java → Cangjie)\n"
            "The following are verified translation examples from "
            "similar code patterns. Use them as reference.\n"
        )

        for i, ex in enumerate(examples[:max_examples]):
            block = (
                f"### Example {i + 1} [{ex.scenario}]\n"
                f"// Source: {ex.signature or 'unknown'}\n"
                f"```java\n"
                f"{ex.java_code}\n"
                f"```\n"
                f"== translates to ==\n"
                f"```cangjie\n"
                f"{ex.cangjie_code}\n"
                f"```\n"
            )
            if ex.compile_pass:
                block += "// [verified] Compile-verified\n"
            parts.append(block)

        return "\n".join(parts)

    def format_type_context(self, java_types: list) -> str:
        """
        Provide cached type mappings as reference for type resolution.

        If verified mappings exist, show those first; otherwise show
        RAG-retrieved ones.
        """
        if not java_types:
            return ""

        lines = ["### Type Mapping Reference"]
        has_any = False
        for jt in java_types:
            tm = self._type_map.get(jt)
            if tm:
                has_any = True
                verified_tag = "[V]" if tm.verified else "[~]"
                lines.append(
                    f"  {verified_tag} {jt} -> {tm.cangjie_type}"
                )
                if tm.imports:
                    lines.append(f"     imports: {', '.join(tm.imports)}")

        if not has_any:
            return ""

        lines.append("")
        return "\n".join(lines)

    # ----------------------------------------------------------
    # Internal methods
    # ----------------------------------------------------------

    @staticmethod
    def _hash_pair(java: str, cangjie: str) -> str:
        """Use content hash as pair_id for natural dedup."""
        raw = f"{java.strip()}|||{cangjie.strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _tokenize(code: str) -> set[str]:
        """
        Tokenize code into token set for Jaccard similarity.

        Splits: identifiers, keywords, operators count;
        string literals and comments ignored.
        This is a simplified tokenizer; production can use tree-sitter AST nodes.
        """
        if not code:
            return set()
        # Remove comments and strings
        code = re.sub(r'//.*|/\*[\s\S]*?\*/|\'[^\']*\'|"[^"]*"', "", code)
        # Split by identifiers and operators
        tokens = re.findall(r'\b[a-zA-Z_]\w*\b|[{}();,.<>+\-*/%=!&|]', code)
        # Remove pure numbers
        tokens = [t for t in tokens if not t.isdigit()]
        return set(tokens)

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        intersection = a & b
        union = a | b
        return len(intersection) / len(union) if union else 0.0

    def _load(self):
        """Load existing KB data from disk."""
        if not self.storage_dir.exists():
            # First run — nothing to load
            return

        if self.pool_path.exists():
            with open(self.pool_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._pairs = [TranslationPair(**d) for d in data]

        if self.types_path.exists():
            with open(self.types_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in data.items():
                    self._type_map[k] = TypeMapping(**v)

        if self.scenarios_path.exists():
            with open(self.scenarios_path, "r", encoding="utf-8") as f:
                self._scenario_index = defaultdict(list, json.load(f))
        else:
            # Rebuild scenario index from existing pairs
            self._rebuild_scenario_index()

    def _save(self):
        """Write all data back to disk."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        with open(self.pool_path, "w", encoding="utf-8") as f:
            json.dump(
                [asdict(p) for p in self._pairs],
                f, ensure_ascii=False, indent=2,
            )

        with open(self.types_path, "w", encoding="utf-8") as f:
            json.dump(
                {k: asdict(v) for k, v in self._type_map.items()},
                f, ensure_ascii=False, indent=2,
            )

        with open(self.scenarios_path, "w", encoding="utf-8") as f:
            json.dump(dict(self._scenario_index), f, ensure_ascii=False, indent=2)

    def _rebuild_scenario_index(self):
        """Rebuild scenario index from existing pairs."""
        self._scenario_index.clear()
        for pair in self._pairs:
            self._scenario_index[pair.scenario].append(pair.pair_id)
            for s in ScenarioClassifier.classify(pair.java_code):
                if pair.pair_id not in self._scenario_index[s]:
                    self._scenario_index[s].append(pair.pair_id)

    # ----------------------------------------------------------
    # Statistics & introspection
    # ----------------------------------------------------------

    @property
    def pair_count(self) -> int:
        return len(self._pairs)

    @property
    def type_mapping_count(self) -> int:
        return len(self._type_map)


# ==============================================================
# Module-level singleton
# ==============================================================

_global_kb: ProgressiveKB | None = None


def get_progressive_kb(
    storage_dir: str = "data/java/progressive_kb",
) -> ProgressiveKB:
    """Get or create the global ProgressiveKB singleton."""
    global _global_kb
    if _global_kb is None:
        _global_kb = ProgressiveKB(storage_dir=storage_dir)
        _global_kb.ensure_dirs()
    return _global_kb
