"""
Offline index builder: corpus → chunk → embed → ChromaDB + BM25.
"""

import json
import pickle
import time
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
from rank_bm25 import BM25Okapi
from tqdm import tqdm

from src.java.rag.corpus_loader import CorpusLoader, Chunk
from src.java.rag.retriever import RRF_K


EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIM = 1536
BATCH_SIZE = 20


class Indexer:
    """Builds vector index (ChromaDB) + BM25 index from CangjieCorpus."""

    def __init__(
        self,
        corpus_root: str = "misc/CangjieCorpus",
        chroma_path: str = "data/java/rag/chromadb",
        bm25_path: str = "data/java/rag/bm25_index.pkl",
        chunks_json_path: str = "data/java/rag/chunks.json",
        collection_name: str = "cangjie_corpus_v1",
    ):
        self.corpus_root = corpus_root
        self.chroma_path = str(Path(chroma_path).resolve())
        self.bm25_path = bm25_path
        self.chunks_json_path = chunks_json_path
        self.collection_name = collection_name

        # Create directories
        Path(chroma_path).mkdir(parents=True, exist_ok=True)
        Path(bm25_path).parent.mkdir(parents=True, exist_ok=True)
        Path(chunks_json_path).parent.mkdir(parents=True, exist_ok=True)

        self._openai_client = OpenAI()

    def build(self):
        """Run the full indexing pipeline."""
        print("Step 1/4: Scanning and chunking corpus...")
        loader = CorpusLoader(self.corpus_root)
        chunks = loader.scan()
        print(f"  → {len(chunks)} chunks after dedup")

        print("Step 2/4: Generating embeddings via text-embedding-3-large...")
        self._embed_chunks(chunks)

        print(f"Step 3/4: Storing in ChromaDB ({self.chroma_path})...")
        self._store_chromadb(chunks)

        print("Step 4/4: Building BM25 index...")
        self._build_bm25(chunks)

        # Save chunks.json for inspection
        with open(self.chunks_json_path, "w", encoding="utf-8") as f:
            json.dump(
                [
                    {
                        "id": c.id,
                        "content_preview": c.content[:200],
                        "metadata": c.metadata,
                        "tokens": c.tokens,
                    }
                    for c in chunks
                ],
                f,
                ensure_ascii=False,
                indent=2,
            )

        print(f"✓ Indexing complete. {len(chunks)} chunks indexed.")
        print(f"  ChromaDB: {self.chroma_path}")
        print(f"  BM25:     {self.bm25_path}")
        print(f"  JSON:     {self.chunks_json_path}")

    def _embed_chunks(self, chunks: list[Chunk]):
        """Generate embeddings in batches using OpenAI API."""
        for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Embedding"):
            batch = chunks[i : i + BATCH_SIZE]
            texts = [c.content for c in batch]

            try:
                response = self._openai_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                    dimensions=EMBEDDING_DIM,
                )
                for j, embedding_data in enumerate(response.data):
                    if j < len(batch):
                        batch[j].embedding = embedding_data.embedding
            except Exception as e:
                print(f"  ⚠ Embedding batch {i//BATCH_SIZE} failed: {e}. Retrying once after delay...")
                time.sleep(5)
                try:
                    response = self._openai_client.embeddings.create(
                        model=EMBEDDING_MODEL,
                        input=texts,
                        dimensions=EMBEDDING_DIM,
                    )
                    for j, embedding_data in enumerate(response.data):
                        if j < len(batch):
                            batch[j].embedding = embedding_data.embedding
                except Exception as e2:
                    print(f"  ✗ Embedding batch {i//BATCH_SIZE} failed after retry: {e2}")
                    # Leave embedding as None — this chunk will only be BM25-searchable

            # Rate-limit: sleep 0.5s between batches
            time.sleep(0.5)

    def _store_chromadb(self, chunks: list[Chunk]):
        """Store embeddings and metadata in ChromaDB."""
        client = chromadb.PersistentClient(
            path=self.chroma_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Delete existing collection if it exists
        try:
            client.delete_collection(self.collection_name)
        except Exception:
            pass

        collection = client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Filter to chunks with embeddings
        embeddable = [c for c in chunks if c.embedding is not None]
        if not embeddable:
            print("  ⚠ No chunks with embeddings to store.")
            return

        for i in tqdm(range(0, len(embeddable), BATCH_SIZE), desc="ChromaDB insert"):
            batch = embeddable[i : i + BATCH_SIZE]
            ids = [c.id for c in batch]
            embeddings = [c.embedding for c in batch]
            metadatas = [c.metadata for c in batch]
            documents = [c.content for c in batch]

            try:
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents,
                )
            except Exception as e:
                print(f"  ⚠ ChromaDB batch {i//BATCH_SIZE} failed: {e}")

    def _build_bm25(self, chunks: list[Chunk]):
        """Build BM25 index from chunk content."""
        tokenized_corpus = [c.content.lower().split() for c in chunks]
        bm25 = BM25Okapi(tokenized_corpus)

        data = {
            "bm25": bm25,
            "chunks": chunks,
        }
        with open(self.bm25_path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def add_arguments(parser):
        """Add CLI arguments for the indexer script."""
        parser.add_argument(
            "--corpus-root",
            default="misc/CangjieCorpus",
            help="Path to CangjieCorpus directory",
        )
        parser.add_argument(
            "--chroma-path",
            default="data/java/rag/chromadb",
            help="Path for ChromaDB persistent storage",
        )
        parser.add_argument(
            "--bm25-path",
            default="data/java/rag/bm25_index.pkl",
            help="Path for BM25 pickle file",
        )
        parser.add_argument(
            "--reindex",
            action="store_true",
            help="Force full reindex (delete existing)",
        )
        return parser


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build RAG index from CangjieCorpus")
    Indexer.add_arguments(parser)
    args = parser.parse_args()

    indexer = Indexer(
        corpus_root=args.corpus_root,
        chroma_path=args.chroma_path,
        bm25_path=args.bm25_path,
    )
    indexer.build()


if __name__ == "__main__":
    main()
