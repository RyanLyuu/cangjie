"""
Query construction from Java source context, with term mapping.

Translates Java types, API calls, and keywords into Cangjie-idiomatic
search queries for optimal BM25 and vector retrieval.
"""

import re
from pathlib import Path

import yaml


class QueryBuilder:
    """Builds retrieval queries from Java translation context."""

    def __init__(self, term_dict_path: str = "configs/java_cangjie_terms.yaml"):
        self._java_to_cangjie: dict[str, list[str]] = {}
        self._load_term_dict(term_dict_path)

    def _load_term_dict(self, path: str):
        """Load term dictionary from YAML."""
        path = Path(path)
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        self._java_to_cangjie = {k.lower(): v for k, v in raw.items()}

    def build_fragment_query(self, java_code: str) -> str:
        """
        Build a query for fragment translation from Java source code.

        Extracts type names, API calls, and keywords from the Java fragment,
        maps them via the term dictionary, then composes the query.
        """
        types = self._extract_types(java_code)
        apis = self._extract_api_calls(java_code)
        keywords = self._extract_keywords(java_code)

        # Map all extracted terms
        mapped_terms: list[str] = []
        for t in types:
            mapped = self._java_to_cangjie.get(t.lower(), [])
            mapped_terms.extend(mapped)
            mapped_terms.append(t)

        for a in apis:
            mapped = self._java_to_cangjie.get(a.lower(), [])
            mapped_terms.extend(mapped)

        for k in keywords:
            mapped = self._java_to_cangjie.get(k.lower(), [])
            mapped_terms.extend(mapped)

        # Remove duplicates while preserving order
        seen: set[str] = set()
        unique_terms: list[str] = []
        for t in mapped_terms:
            if t not in seen:
                seen.add(t)
                unique_terms.append(t)

        terms_str = " ".join(unique_terms)
        return f"仓颉 {terms_str} 语法 示例"

    def build_error_query(self, error_message: str) -> str:
        """
        Build a query from a cjc compilation error message.

        Extracts error type and type/identifier names from the error.
        """
        # Common cjc error patterns
        error_types = re.findall(r"error:\s*(\w+)", error_message)
        identifiers = re.findall(r"'(\w+)'", error_message)

        terms = " ".join(error_types + identifiers)
        return f"仓颉 {terms} 错误 修复"

    @staticmethod
    def _extract_types(java_code: str) -> list[str]:
        """Extract likely type names from Java source code."""
        types: set[str] = set()
        # Match generic types: Map<K,V>, List<String>, Optional<T>
        generic_matches = re.findall(r'\b([A-Z][a-zA-Z0-9]*)\s*<', java_code)
        types.update(generic_matches)
        # Match type annotations in declarations: String name, int count
        decl_matches = re.findall(r'\b([A-Z][a-zA-Z0-9]*)\s+\w+\s*[=;)]', java_code)
        types.update(decl_matches)
        return list(types)

    @staticmethod
    def _extract_api_calls(java_code: str) -> list[str]:
        """Extract API calls: ClassName.methodName patterns."""
        apis = re.findall(r'\b([A-Z][a-zA-Z0-9]*\.[a-z][a-zA-Z0-9]*)', java_code)
        return list(set(apis))

    @staticmethod
    def _extract_keywords(java_code: str) -> list[str]:
        """Extract Java-specific keywords that have Cangjie counterparts."""
        java_keywords = {
            "instanceof", "synchronized", "implements", "extends",
            "throws", "try", "catch", "finally", "abstract",
            "interface", "enum", "@Override",
        }
        found = set()
        for kw in java_keywords:
            if kw in java_code:
                found.add(kw)
        return list(found)
