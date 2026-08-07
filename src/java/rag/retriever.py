"""
Hybrid search engine: vector search (ChromaDB) + BM25 + RRF fusion.
"""

import pickle
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from rank_bm25 import BM25Okapi

from src.java.rag.corpus_loader import Chunk


EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 1536


RRF_K = 60


class Retriever:
    """Hybrid search with RRF fusion."""

    def __init__(
        self,
        chroma_path: str = "data/java/rag/chromadb",
        bm25_path: str = "data/java/rag/bm25_index.pkl",
        collection_name: str = "cangjie_corpus_v1",
    ):
        self.chroma_path = str(Path(chroma_path).resolve())
        self.bm25_path = bm25_path
        self.collection_name = collection_name

        # Lazy init — indices loaded/connected on first search
        self._chroma_client: Optional[chromadb.Client] = None
        self._collection: Optional[chromadb.Collection] = None
        self._bm25: Optional[BM25Okapi] = None
        self._chunk_list: list[Chunk] = []

    def _ensure_chroma(self):
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(
                path=self.chroma_path,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._chroma_client.get_collection(self.collection_name)

    def _ensure_bm25(self):
        if self._bm25 is None and Path(self.bm25_path).exists():
            with open(self.bm25_path, "rb") as f:
                data = pickle.load(f)
                self._bm25 = data["bm25"]
                self._chunk_list = data["chunks"]

    def search(self, query: str, top_k: int = 3, category_filter: Optional[str] = None) -> list[Chunk]:
        """
        Hybrid search: vector + BM25 → RRF fusion → dedup → Top-K.
        """
        if not query.strip():
            return []

        vector_results = self._vector_search(query, top_k=10) if self._collection_exists() else []
        bm25_results = self._bm25_search(query, top_k=10) if self._bm25_available() else []

        # If one index is missing, use whatever we have
        if not vector_results and not bm25_results:
            return []

        # If only one result set, return its top-K directly
        if not vector_results:
            return bm25_results[:top_k]
        if not bm25_results:
            return vector_results[:top_k]

        # RRF fusion
        return self._rrf_fusion(vector_results, bm25_results, top_k, category_filter)

    def _collection_exists(self) -> bool:
        try:
            self._ensure_chroma()
            return True
        except Exception:
            return False

    def _bm25_available(self) -> bool:
        try:
            self._ensure_bm25()
            return self._bm25 is not None
        except Exception:
            return False

    def _vector_search(self, query: str, top_k: int) -> list[Chunk]:
        """Search ChromaDB and return results as Chunk list."""
        try:
            self._ensure_chroma()
        except Exception:
            return []

        if self._collection is None:
            return []

        try:
            # Embed query using same model as indexer for dimension compatibility
            client = OpenAI()
            response = client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=query,
                dimensions=EMBEDDING_DIM,
            )
            query_embedding = response.data[0].embedding

            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )
        except Exception:
            return []

        chunks: list[Chunk] = []
        if not results["metadatas"] or not results["metadatas"][0]:
            return chunks

        for i in range(len(results["metadatas"][0])):
            meta = results["metadatas"][0][i]
            content = results["documents"][0][i] if results["documents"] else ""
            chunk_id = results["ids"][0][i] if results["ids"] else ""
            chunk = Chunk(
                id=chunk_id,
                content=content,
                metadata=meta,
            )
            # Attach distance if available
            if results.get("distances") and results["distances"][0]:
                # Store distance for RRF ordering
                chunk.tokens = int(results["distances"][0][i] * 1000)
            chunks.append(chunk)

        return chunks

    def _bm25_search(self, query: str, top_k: int) -> list[Chunk]:
        """Search BM25 index and return results as Chunk list."""
        try:
            self._ensure_bm25()
        except Exception:
            return []

        if self._bm25 is None:
            return []

        tokenized_query = query.lower().split()
        scores = self._bm25.get_scores(tokenized_query)

        # Get top-k indices
        indexed_scores = list(enumerate(scores))
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        top_indices = [idx for idx, score in indexed_scores[:top_k] if score > 0]

        results: list[Chunk] = []
        for idx in top_indices:
            if idx < len(self._chunk_list):
                chunk = self._chunk_list[idx]
                results.append(chunk)

        return results

    def _rrf_fusion(
        self,
        vector_results: list[Chunk],
        bm25_results: list[Chunk],
        top_k: int,
        category_filter: Optional[str] = None,
    ) -> list[Chunk]:
        """
        Reciprocal Rank Fusion: merge and re-rank results.
        score(d) = 1/(RRF_K + rank_vector(d)) + 1/(RRF_K + rank_bm25(d))
        """
        # Build rank maps
        vec_ranks = {c.id: i for i, c in enumerate(vector_results)}
        bm25_ranks = {c.id: i for i, c in enumerate(bm25_results)}

        # Union of all chunk IDs
        all_ids = set(vec_ranks.keys()) | set(bm25_ranks.keys())

        # Calculate RRF scores
        scored: dict[str, float] = {}
        for chunk_id in all_ids:
            score = 0.0
            if chunk_id in vec_ranks:
                score += 1.0 / (RRF_K + vec_ranks[chunk_id])
            if chunk_id in bm25_ranks:
                score += 1.0 / (RRF_K + bm25_ranks[chunk_id])
            scored[chunk_id] = score

        # Sort by score descending
        ranked_ids = sorted(scored.keys(), key=lambda cid: scored[cid], reverse=True)

        # Build result list, deduplicate by source_file+section, apply category filter
        seen_source: set[str] = set()
        final: list[Chunk] = []
        for chunk_id in ranked_ids:
            # Find the chunk from either list
            chunk = next(
                (c for c in vector_results if c.id == chunk_id),
                next((c for c in bm25_results if c.id == chunk_id), None),
            )
            if chunk is None:
                continue

            # Category filter
            if category_filter and chunk.metadata.get("category") != category_filter:
                continue

            # Dedup by source path + title
            dedup_key = f"{chunk.metadata.get('path', '')}|{chunk.metadata.get('h2', '')}"
            if dedup_key in seen_source:
                continue
            seen_source.add(dedup_key)

            final.append(chunk)
            if len(final) >= top_k:
                break

        return final

    def get_category_filter(self, query: str) -> Optional[str]:
        """Auto-detect which category to filter by based on query keywords."""
        query_lower = query.lower()
        if any(w in query_lower for w in ["语法", "规范", "定义"]):
            return "manual"
        if any(w in query_lower for w in ["库", "api", "import", "包", "package"]):
            return None  # no filter — could be std or stdx
        return None
