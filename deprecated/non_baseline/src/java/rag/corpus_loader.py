"""
Corpus scanning, Markdown parsing, and chunking engine.

Splits CangjieCorpus .md files into semantically self-contained chunks
at ## heading boundaries, with code-block integrity protection,
title-chain prefix injection, and MinHash deduplication.
"""

import os
import re
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterator

from datasketch import MinHash, MinHashLSH


@dataclass
class Chunk:
    id: str                    # sha256(content) for dedup
    content: str               # [Context: {title_chain}]\n\n{section_text}
    metadata: dict             # {path, category, h1, h2, h3, language}
    embedding: list[float] | None = None  # 1536-dim, set later by indexer
    tokens: int = 0


CATEGORY_LABELS = {
    "manual": "Language Manual",
    "std": "Standard Library",
    "stdx": "Extended Library",
    "extra": "Quick Reference",
    "tools": "Toolchain Docs",
    "ohos": "OpenHarmony Docs",
}

LANGUAGE_EXTENSIONS = {
    "zh-cn": "zh",
    "zh_CN": "zh",
    "en": "en",
}


class CorpusLoader:
    """Scans CangjieCorpus directory, parses .md files, yields Chunks."""

    def __init__(self, corpus_root: str = "misc/CangjieCorpus", min_hash_threshold: float = 0.85):
        self.corpus_root = Path(corpus_root).resolve()
        self.min_hash_threshold = min_hash_threshold
        self._lsh = MinHashLSH(threshold=min_hash_threshold, num_perm=128)
        self._seen_hashes: set[str] = set()

    def scan(self) -> list[Chunk]:
        """Scan the corpus directory, parse all .md files, return deduplicated chunks."""
        all_chunks: list[Chunk] = []
        for md_file in sorted(self.corpus_root.rglob("*.md")):
            # Skip hidden files, .git directory
            if any(part.startswith(".") for part in md_file.parts):
                continue
            chunks = self._parse_file(md_file)
            all_chunks.extend(chunks)
        return self._deduplicate(all_chunks)

    def _parse_file(self, file_path: Path) -> list[Chunk]:
        """Parse a single .md file into chunks."""
        relative_path = file_path.relative_to(self.corpus_root)
        category = self._detect_category(relative_path)
        language = self._detect_language(relative_path)

        text = file_path.read_text(encoding="utf-8")

        sections = self._split_by_headings(text)
        chunks: list[Chunk] = []

        h1 = ""
        h2 = ""
        h3 = ""

        for heading_level, heading_text, section_content in sections:
            # Update current heading context
            if heading_level == 1:
                h1 = heading_text
                h2 = ""
                h3 = ""
            elif heading_level == 2:
                h2 = heading_text
                h3 = ""
            elif heading_level >= 3:
                if heading_level == 3:
                    h3 = heading_text
                # merge deeper headings under h3 without updating

            # Build title chain
            title_parts = [p for p in [h1, h2, h3] if p]
            title_chain = " > ".join(title_parts)

            # Build chunk content with title chain prefix
            prefix = f"[Context: {title_chain}]"
            content = f"{prefix}\n\n{section_content.strip()}"

            metadata = {
                "path": str(relative_path),
                "category": category,
                "h1": h1,
                "h2": h2,
                "h3": h3,
                "title_chain": title_chain,
                "language": language,
            }

            chunk = Chunk(
                id=hashlib.sha256(content.encode()).hexdigest()[:16],
                content=content,
                metadata=metadata,
            )
            chunks.append(chunk)

        return chunks

    def _split_by_headings(self, text: str) -> list[tuple[int, str, str]]:
        """
        Split markdown text by ## headings, preserving code block integrity.

        Returns list of (heading_level, heading_text, section_content).
        Level-1 headings (#) start the document context; level-2 headings (##)
        are the primary split points; level-3+ headings (###) are merged into
        the preceding ## section.
        """
        lines = text.split("\n")
        sections: list[tuple[int, str, str]] = []
        current_level = 0
        current_heading = ""
        current_lines: list[str] = []
        in_code_block = False

        def flush():
            if current_lines:
                sections.append((current_level, current_heading, "\n".join(current_lines)))

        for line in lines:
            # Track code fence state
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                current_lines.append(line)
                continue

            if in_code_block:
                current_lines.append(line)
                continue

            # Check for headings only outside code blocks
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                if level >= 2:
                    # Flush previous section and start new one
                    flush()
                    current_lines = []
                    current_level = level
                    current_heading = heading_text
                else:
                    # # h1 heading — start of document context
                    if level == 1:
                        flush()
                        current_lines = []
                        current_level = level
                        current_heading = heading_text
                    else:
                        current_lines.append(line)
            else:
                current_lines.append(line)

        flush()
        return sections

    def _detect_category(self, relative_path: Path) -> str:
        """Detect document category from path."""
        for part in relative_path.parts:
            if part in CATEGORY_LABELS:
                return part
        return "other"

    def _detect_language(self, relative_path: Path) -> str:
        """Detect language from path segments."""
        for part in relative_path.parts:
            if part in LANGUAGE_EXTENSIONS:
                return LANGUAGE_EXTENSIONS[part]
        return "en"  # default to English

    def _deduplicate(self, chunks: list[Chunk]) -> list[Chunk]:
        """Remove near-duplicate chunks using MinHash LSH."""
        unique: list[Chunk] = []
        for chunk in chunks:
            chunk_id = chunk.id
            if chunk_id in self._seen_hashes:
                continue

            # MinHash signature from content
            mh = MinHash(num_perm=128)
            for word in chunk.content.split():
                mh.update(word.encode("utf-8"))

            # Check for near-duplicates
            if self._lsh.query(mh):
                continue

            self._lsh.insert(chunk_id, mh)
            self._seen_hashes.add(chunk_id)
            unique.append(chunk)

        return unique
