"""
Chunk-to-prompt formatting with source annotation and category ordering.
"""

from src.java.rag.corpus_loader import Chunk, CATEGORY_LABELS


# Priority order for chunk injection: manual first, then std, then extra/samples
CATEGORY_PRIORITY = {
    "manual": 0,   # Language manual — definitions, grammar
    "std": 1,      # Standard library — API signatures
    "stdx": 2,     # Extended library — API signatures
    "tools": 3,    # Toolchain docs
    "ohos": 4,     # Platform-specific
    "extra": 5,    # Quick reference
    "other": 6,
}


class Injector:
    """Formats retrieved chunks into LLM prompt context."""

    @staticmethod
    def format_chunks(chunks: list[Chunk]) -> str:
        """
        Format a list of chunks into a string for prompt injection.

        Chunks are ordered by category priority (manual → std → extra),
        then by title_chain alphabetically within same category.
        Each chunk includes its category source annotation.
        """
        if not chunks:
            return ""

        # Sort by category priority, then by title chain
        sorted_chunks = sorted(
            chunks,
            key=lambda c: (
                CATEGORY_PRIORITY.get(c.metadata.get("category", "other"), 99),
                c.metadata.get("title_chain", ""),
            ),
        )

        parts: list[str] = []
        for chunk in sorted_chunks:
            category = chunk.metadata.get("category", "other")
            source_label = CATEGORY_LABELS.get(category, category)
            title_chain = chunk.metadata.get("title_chain", "")

            block = f"### Reference [Source: {source_label}]\n"
            if title_chain:
                block += f"[Context: {title_chain}]\n"
            block += f"{chunk.content}\n"

            parts.append(block)

        return "\n".join(parts)

    @staticmethod
    def format_for_fragment_translation(chunks: list[Chunk]) -> str:
        """Format chunks specifically for fragment translation prompts."""
        formatted = Injector.format_chunks(chunks)
        if not formatted:
            return ""
        return (
            "### Reference Cangjie documentation:\n"
            f"{formatted}"
        )

    @staticmethod
    def format_for_error_feedback(chunks: list[Chunk]) -> str:
        """Format chunks for compilation error feedback."""
        formatted = Injector.format_chunks(chunks)
        if not formatted:
            return ""
        return (
            "### Corrective Reference:\n"
            "The translation above failed Cangjie compilation.\n"
            "Relevant documentation:\n"
            f"{formatted}"
        )
