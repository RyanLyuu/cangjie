"""RAG engine for fragment translation."""

from typing import Any


class RagEngine:
    """
    Unified RAG interface for the translation pipeline.

    Usage:
        rag = RagEngine()
        rag.ensure_index()  # builds index if missing

        # Fragment translation
        rag.inject_fragment_context(java_code)  # → prompt string or None

        # Compilation error feedback
        rag.inject_error_context(error_msg)  # → prompt string or None
    """

    def __init__(
        self,
        corpus_root: str = "misc/CangjieCorpus",
        chroma_path: str = "data/java/rag/chromadb",
        bm25_path: str = "data/java/rag/bm25_index.pkl",
    ):
        self.corpus_root = corpus_root
        self.chroma_path = chroma_path
        self.bm25_path = bm25_path

        self._retriever: Any = None
        self._query_builder: Any = None
        self._injector: Any = None

    def _lazy_init(self):
        if self._query_builder is None:
            from src.java.rag.injector import Injector
            from src.java.rag.query_builder import QueryBuilder
            from src.java.rag.retriever import Retriever

            self._query_builder = QueryBuilder()
            self._injector = Injector()
            self._retriever = Retriever(
                chroma_path=self.chroma_path,
                bm25_path=self.bm25_path,
            )

    def ensure_index(self):
        """Build index if it doesn't exist yet."""
        import os

        if os.path.exists(self.bm25_path):
            return
        from src.java.rag.indexer import Indexer

        print("RAG index not found. Building...")
        indexer = Indexer(
            corpus_root=self.corpus_root,
            chroma_path=self.chroma_path,
            bm25_path=self.bm25_path,
        )
        indexer.build()

    def inject_fragment_context(self, java_code: str) -> str | None:
        """
        Retrieve and format context for fragment translation.
        Returns None if no relevant context found.
        """
        self._lazy_init()
        if self._query_builder is None or self._retriever is None or self._injector is None:
            return None

        query = self._query_builder.build_fragment_query(java_code)
        chunks = self._retriever.search(query, top_k=3)
        if not chunks:
            return None
        return self._injector.format_for_fragment_translation(chunks)

    def inject_error_context(self, error_msg: str) -> str | None:
        """
        Retrieve and format context from a compilation error message.
        Returns None if no relevant context found.
        """
        self._lazy_init()
        if self._query_builder is None or self._retriever is None or self._injector is None:
            return None

        query = self._query_builder.build_error_query(error_msg)
        chunks = self._retriever.search(query, top_k=3)
        if not chunks:
            return None
        return self._injector.format_for_error_feedback(chunks)


# Module-level singleton for reuse
_global_engine: RagEngine | None = None


def get_rag_engine(corpus_root: str = "misc/CangjieCorpus") -> RagEngine:
    """Get or create the global RAG engine singleton."""
    global _global_engine
    if _global_engine is None:
        _global_engine = RagEngine(corpus_root=corpus_root)
        _global_engine.ensure_index()
    return _global_engine
