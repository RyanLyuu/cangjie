"""
Generics Rule Library — Loading, matching, and application engine.

Provides two integration points for the Java → Cangjie translation pipeline:

1. Generics rule matching for language mechanisms that need model guidance.
2. Few-shot prompt injection for generic declarations, bounds, wildcards,
   raw-type recovery, generic arrays/construction, and semantic gaps.

Concrete type expressions such as List<String>, HashMap<Object, Integer>, and
Function<T, R> are resolved deterministically by
src.java.type_resolution.type_expression using fixed/java.base type maps.

Data directory:  generics_rule_lib/  (at repo root)
"""

import json
import os
import re
import threading
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

_RULE_LIB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    "generics_rule_lib",
)

_RULES_SUBDIR = os.path.join(_RULE_LIB_DIR, "rules")

_RULE_FILES = [
    "01_declaration.json",
    "02_constraint.json",
    "03_wildcard.json",
    "04_variance.json",
    "05_raw_type.json",
    "06_array_instantiation.json",
    "07_advanced.json",
    "08_semantic_gap.json",
    "09_container_smart.json",
]

# ---------------------------------------------------------------------------
# Singleton loader
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_instance: Optional["GenericsRuleLib"] = None


def get_generics_rule_lib() -> "GenericsRuleLib":
    """Return the singleton GenericsRuleLib instance (lazy-loaded, thread-safe)."""
    global _instance
    if _instance is not None:
        return _instance
    with _lock:
        if _instance is None:
            _instance = GenericsRuleLib()
        return _instance


# ---------------------------------------------------------------------------
# Core class
# ---------------------------------------------------------------------------


class GenericsRuleLib:
    """Load and query the Java generics → Cangjie mapping rule library.

    Attributes:
        rules: flat list of prompt rules sorted by priority desc
        container_map: legacy/reference dict from type_container_map.json
        primitive_map: legacy/reference dict from primitive_map.json
    """

    def __init__(self, rule_dir: Optional[str] = None):
        self._rule_dir = rule_dir or _RULE_LIB_DIR
        self.rules: list = []
        self.container_map: dict = {}
        self.primitive_map: dict = {}
        self.functional_interface_map: dict = {}
        self.nested_class_map: dict = {}
        self._loaded = False

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _ensure_loaded(self):
        if self._loaded:
            return
        self._load_all()
        self._loaded = True

    def _load_all(self):
        """Load all JSON data files."""
        # rules
        self.rules = []
        for fname in _RULE_FILES:
            fpath = os.path.join(_RULES_SUBDIR, fname)
            if not os.path.exists(fpath):
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for rule in data.get("rules", []):
                rule["_category_file"] = fname
                self.rules.append(rule)

        # sort by priority descending, then by id ascending
        self.rules.sort(key=lambda r: (-r.get("priority", 0), r.get("id", "ZZ")))

        # container map
        cpath = os.path.join(self._rule_dir, "type_container_map.json")
        if os.path.exists(cpath):
            with open(cpath, "r", encoding="utf-8") as f:
                cdata = json.load(f)
            self.container_map = cdata.get("mappings", {})
            self.constraint_config = cdata.get("constraint_inference_rules", {})

        # primitive map
        ppath = os.path.join(self._rule_dir, "primitive_map.json")
        if os.path.exists(ppath):
            with open(ppath, "r", encoding="utf-8") as f:
                pdata = json.load(f)
            self.primitive_map = pdata.get("mappings", {})

        # functional interface map
        fpath = os.path.join(self._rule_dir, "functional_interface_map.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                fdata = json.load(f)
            self.functional_interface_map = fdata.get("mappings", {})

        # nested class map
        npath = os.path.join(self._rule_dir, "nested_class_map.json")
        if os.path.exists(npath):
            with open(npath, "r", encoding="utf-8") as f:
                ndata = json.load(f)
            self.nested_class_map = ndata.get("mappings", {})

    # ------------------------------------------------------------------
    # Legacy/reference container mapping
    # ------------------------------------------------------------------

    def get_container_cangjie(self, java_type_name: str) -> Optional[dict]:
        """Look up a Java container type in the container map.

        Returns the mapping dict (with cangjie, type_args, key_constraints, etc.),
        or None if not found.
        """
        self._ensure_loaded()
        # Try simple name first, then qualified
        short = java_type_name.split(".")[-1] if "." in java_type_name else java_type_name
        return self.container_map.get(short) or self.container_map.get(java_type_name)

    def is_hash_key_container(self, cangjie_type_name: str) -> bool:
        """Check if a Cangjie type requires Hashable key constraints."""
        self._ensure_loaded()
        containers = getattr(self, "constraint_config", {}).get("hash_key_containers", [])
        return cangjie_type_name in containers

    def is_hash_element_container(self, cangjie_type_name: str) -> bool:
        """Check if a Cangjie type requires Hashable element constraints."""
        self._ensure_loaded()
        containers = getattr(self, "constraint_config", {}).get("hash_element_containers", [])
        return cangjie_type_name in containers

    def is_comparable_container(self, cangjie_type_name: str) -> bool:
        """Check if a Cangjie type requires Comparable constraints."""
        self._ensure_loaded()
        containers = getattr(self, "constraint_config", {}).get("comparable_element_containers", [])
        return cangjie_type_name in containers

    def any_replacement_for(self, cangjie_type_name: str, position: str = "key") -> str:
        """Return the replacement type for Any in container type args.

        Args:
            cangjie_type_name: The Cangjie container type name (e.g. "HashMap")
            position: "key" or "element"

        Returns:
            The replacement type (e.g. "AnyHashable") or "Any" if no replacement.
        """
        self._ensure_loaded()
        mapping = self.container_map.get(cangjie_type_name)
        if mapping:
            if position == "key":
                return mapping.get("any_key_replacement", "Any")
            elif position == "element":
                return mapping.get("any_element_replacement", "Any")
        return "Any"

    def infer_constraints(self, cangjie_type_name: str) -> list:
        """Return the constraint list for a container type.

        E.g. HashMap -> ["K <: Hashable & Equatable<K>"]
        """
        self._ensure_loaded()
        mapping = self.container_map.get(cangjie_type_name)
        if mapping:
            return mapping.get("key_constraints", []) + mapping.get("element_constraints", [])
        return []

    # ------------------------------------------------------------------
    # Type translation with container awareness
    # ------------------------------------------------------------------

    def translate_container_type(self, java_type: str, existing_type_map: dict = None) -> Optional[str]:
        """Translate a Java generic container type to Cangjie, applying
        container mapping + Any→AnyHashable replacement.

        This is designed to be called from get_cangjie_type() BEFORE the
        existing fallback logic.

        Returns None if the type is not a known container (caller should
        fall through to existing logic).
        """
        self._ensure_loaded()
        if not java_type or "<" not in java_type:
            # Simple type — check container map for bare name
            short = java_type.split(".")[-1] if "." in java_type else java_type
            if short in self.container_map:
                mapping = self.container_map[short]
                return mapping["cangjie"]
            return None

        # Has generics:  e.g. HashMap<String, Object>
        base = java_type[: java_type.index("<")].strip()
        inner = java_type[java_type.index("<") + 1 : java_type.rindex(">")]

        # Split nested generics at depth 0
        parts = self._split_generic_args(inner)
        short_base = base.split(".")[-1] if "." in base else base

        mapping = self.container_map.get(short_base)
        if mapping is None:
            return None

        cangjie_base = mapping["cangjie"]

        # If the Cangjie base maps to a different type that has no generics
        if mapping.get("type_args", 1) == 0 and "<" not in cangjie_base:
            # Functional types like Function -> (T) -> R
            return cangjie_base  # already a full description

        # Resolve each type arg
        type_map = existing_type_map or {}
        resolved = []
        for i, part in enumerate(parts):
            part_cangjie = self._resolve_type_arg(part.strip(), type_map)
            # Apply Any→AnyHashable for hash containers
            if part_cangjie == "Any":
                if self.is_hash_key_container(cangjie_base) and i == 0:
                    part_cangjie = self.any_replacement_for(cangjie_base, "key")
                elif self.is_hash_element_container(cangjie_base) and i == 0:
                    part_cangjie = self.any_replacement_for(cangjie_base, "element")
            resolved.append(part_cangjie)

        return f"{cangjie_base}<{', '.join(resolved)}>"

    def _split_generic_args(self, inner: str) -> list:
        """Split comma-separated generic args at depth 0."""
        parts = []
        depth = 0
        current = ""
        for ch in inner:
            if ch == "<":
                depth += 1
                current += ch
            elif ch == ">":
                depth -= 1
                current += ch
            elif ch == "," and depth == 0:
                parts.append(current.strip())
                current = ""
            else:
                current += ch
        if current.strip():
            parts.append(current.strip())
        return parts

    def _resolve_type_arg(self, arg: str, type_map: dict) -> str:
        """Resolve a single type argument using primitive_map, then type_map."""
        arg = arg.strip()
        # Check primitive map first
        if arg in self.primitive_map:
            return self.primitive_map[arg]
        # Check supplied type map
        if arg in type_map:
            return type_map[arg]
        # Recurse for nested generics
        if "<" in arg and arg.endswith(">"):
            return self.translate_container_type(arg, type_map) or arg
        return arg

    # ------------------------------------------------------------------
    # Rule matching (integration point 2: translate_type_rag.py)
    # ------------------------------------------------------------------

    def match_rules(self, java_code: str, category: Optional[str] = None, top_k: int = 5) -> list:
        """Match Java code against generics rules using regex patterns.

        Args:
            java_code:  The Java source snippet to match against
            category:  Optional category filter (declaration, constraint, wildcard, etc.)
            top_k:  Maximum number of rules to return

        Returns:
            List of matching rule dicts, sorted by priority (highest first).
        """
        self._ensure_loaded()
        matches = []
        for rule in self.rules:
            if category and rule.get("category") != category:
                continue
            pattern = rule.get("java_regex_fallback", "")
            if not pattern:
                continue
            try:
                if re.search(pattern, java_code):
                    matches.append(rule)
            except re.error:
                continue
            if len(matches) >= top_k:
                break
        return matches

    def match_rules_for_type(self, java_type: str, top_k: int = 3) -> list:
        """Match a Java type string against generics rules.

        Convenience wrapper for type resolution scenarios.
        """
        return self.match_rules(java_type, top_k=top_k)

    # ------------------------------------------------------------------
    # Few-shot prompt generation (integration point 3: prompt_generator.py)
    # ------------------------------------------------------------------

    def format_rule_prompt(self, rules: list, max_rules: int = 3) -> str:
        """Format matched generics rules as a few-shot prompt section.

        Args:
            rules:  List of rule dicts (from match_rules())
            max_rules:  Maximum number of rules to include

        Returns:
            Formatted prompt text, or empty string if no rules.
        """
        if not rules:
            return ""

        sections = []
        for rule in rules[:max_rules]:
            ex = rule.get("example", {})
            java_ex = ex.get("java", "")
            cj_ex = ex.get("cangjie", "")
            note = ex.get("note", "")

            section = f"Rule {rule['id']} ({rule.get('name', '')}):\n"
            section += f"  Java:\n    {java_ex}\n"
            section += f"  Cangjie:\n    {cj_ex}\n"
            if note:
                section += f"  Note: {note}\n"

            constraints = rule.get("constraints", {})
            semantics = constraints.get("cangjie_semantics", "")
            action = constraints.get("action", "")
            if semantics:
                section += f"  Semantics: {semantics}\n"
            if action:
                section += f"  Action: {action}\n"

            sections.append(section)

        header = "### Applicable Generics Mapping Rules:\n"
        header += "The following rules from the Java→Cangjie generics mapping library apply to this code.\n"
        header += "Follow these patterns when translating generic constructs.\n\n"
        return header + "\n".join(sections)

    def build_generics_context(self, java_code: str, max_rules: int = 3) -> str:
        """Build a complete generics context prompt for injection.

        Convenience method: match rules + format prompt in one call.
        """
        self._ensure_loaded()
        rules = self.match_rules(java_code, top_k=max_rules)
        return self.format_rule_prompt(rules, max_rules=max_rules)

    # ------------------------------------------------------------------
    # Functional interface resolution (integration point 4: fallback_type_for)
    # ------------------------------------------------------------------

    def translate_functional_interface(self, java_type: str) -> Optional[str]:
        """Translate a Java functional interface type to a Cangjie function type.

        Handles both bare names (e.g. "Function") and parameterized names
        (e.g. "Function<String, Integer>") by looking up the base name in
        the functional_interface_map and resolving type parameters.

        Returns None if the type is not a known functional interface.
        """
        self._ensure_loaded()
        if not java_type:
            return None

        # Extract base name, stripping package qualifier
        base = java_type
        if '<' in java_type:
            base = java_type[:java_type.index('<')].strip()
        short = base.split('.')[-1] if '.' in base else base

        # Look up in functional_interface_map
        entry = self.functional_interface_map.get(short)
        if entry is None:
            entry = self.functional_interface_map.get(base)
        if entry is None:
            return None

        cangjie_template = entry.get("cangjie", "")
        type_params = entry.get("type_params", 0)

        # If no type parameters, return template directly
        if type_params == 0:
            return cangjie_template

        # If type parameters present but no generics in input, return template with type variables
        # e.g. Callable → "() -> V" (return with placeholder)
        if '<' not in java_type:
            return cangjie_template

        # Parse generic args from input
        inner = java_type[java_type.index('<') + 1:java_type.rindex('>')]
        args = self._split_generic_args(inner)
        resolved = []
        for arg in args:
            arg_cj = self._resolve_type_arg(arg.strip(), {})
            resolved.append(arg_cj)

        # Replace type variable placeholders in template
        # Templates use T, U, R, V, etc. — we map positional args
        result = cangjie_template
        # For Function<T, R>, map positionally
        java_params = entry.get("java_params", [])
        if len(resolved) >= len(java_params):
            # Replace type params from right to left to avoid partial matches
            for i in range(min(len(java_params), len(resolved)) - 1, -1, -1):
                # Qualified names: java_params[i] is the type variable name
                var_name = java_params[i]
                result = result.replace(var_name, resolved[i])
        elif resolved:
            # Fallback: use resolved args positionally in function type
            # e.g. Callable<T> → () -> V, with V=T
            for i, r in enumerate(resolved):
                # Replace remaining uppercase type variables
                result = re.sub(r'[A-Z](?![a-z])', r, result, count=1)

        return result

    # ------------------------------------------------------------------
    # Nested class resolution
    # ------------------------------------------------------------------

    def translate_nested_class(self, java_type: str) -> Optional[str]:
        """Look up a Java nested/inner class type in the nested_class_map.

        Tries exact match first, then short-name match.
        E.g. Map.Entry → MapEntry, AbstractMap.SimpleEntry → MapEntry.

        Returns None if not found.
        """
        self._ensure_loaded()
        if not java_type:
            return None

        # Exact match
        if java_type in self.nested_class_map:
            return self.nested_class_map[java_type]

        # Short name (after last dot)
        if '.' in java_type:
            # Try Outer.Inner pattern
            if java_type in self.nested_class_map:
                return self.nested_class_map[java_type]

        # Try all keys that end with the short name
        short = java_type.split('.')[-1] if '.' in java_type else java_type
        for key in self.nested_class_map:
            if key.split('.')[-1] == short and '.' in key:
                return self.nested_class_map[key]

        return None

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @property
    def rule_count(self) -> int:
        self._ensure_loaded()
        return len(self.rules)

    @property
    def container_count(self) -> int:
        self._ensure_loaded()
        return len(self.container_map)
