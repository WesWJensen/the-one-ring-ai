"""
Phase 2.7 — Chunk cleaned documents into retrieval-friendly sizes.

Usage:
    python scripts/chunk.py

Reads from data/cleaned/, writes chunk JSON to data/chunks/.
Each chunk carries metadata for tracing back to source.
"""

import json
import uuid
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

INPUT_DIR = Path("data/cleaned")
OUTPUT_DIR = Path("data/chunks")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Tunable — adjust during Phase 4 tuning
CHUNK_SIZE = 512        # characters (roughly 100–150 tokens with nomic-embed-text)
CHUNK_OVERLAP = 64      # keep context across chunk boundaries


splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


def chunk_document(doc: dict) -> list[dict]:
    chunks = splitter.split_text(doc["text"])
    return [
        {
            "id": str(uuid.uuid4()),
            "text": chunk,
            "metadata": {
                "source": doc.get("source", "unknown"),
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "slug": doc.get("slug", ""),
                "chunk_index": i,
                "total_chunks": len(chunks),
            },
        }
        for i, chunk in enumerate(chunks)
    ]


def chunk_all():
    all_chunks = []

    for json_file in sorted(INPUT_DIR.glob("*.json")):
        doc = json.loads(json_file.read_text(encoding="utf-8"))
        chunks = chunk_document(doc)
        print(f"  {json_file.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    out_path = OUTPUT_DIR / "all_chunks.json"
    out_path.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    print(f"\nTotal chunks: {len(all_chunks)} → {out_path}")


if __name__ == "__main__":
    chunk_all()
