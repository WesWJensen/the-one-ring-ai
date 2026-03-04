"""
Phase 3.9 — Store and index embeddings in LanceDB.

Usage:
    python rag/store.py

Reads data/chunks/all_chunks.json, embeds each chunk, upserts into LanceDB.
"""

import json
import os
from pathlib import Path

import lancedb
import pyarrow as pa
from dotenv import load_dotenv

from rag.embed import embed_batch, embed_text

load_dotenv()

LANCE_DIR = os.getenv("LANCE_PERSIST_DIR", "./lance_db")
TABLE_NAME = os.getenv("LANCE_TABLE", "one_ring_lore")
CHUNKS_PATH = Path("data/chunks/all_chunks.json")
BATCH_SIZE = 50


def get_table(db: lancedb.DBConnection) -> lancedb.table.Table:
    """Get or create the lore table with the correct schema."""
    if TABLE_NAME in db.table_names():
        return db.open_table(TABLE_NAME)

    # Infer embedding dimension from a test call
    sample_vec = embed_text("test")
    dim = len(sample_vec)

    schema = pa.schema([
        pa.field("id", pa.string()),
        pa.field("text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), dim)),
        pa.field("source", pa.string()),
        pa.field("title", pa.string()),
        pa.field("url", pa.string()),
        pa.field("slug", pa.string()),
        pa.field("chunk_index", pa.int32()),
        pa.field("total_chunks", pa.int32()),
    ])
    return db.create_table(TABLE_NAME, schema=schema)


def ingest_chunks():
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    db = lancedb.connect(LANCE_DIR)
    table = get_table(db)

    print(f"Ingesting {len(chunks)} chunks into '{TABLE_NAME}'...")

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c["text"] for c in batch]
        embeddings = embed_batch(texts)

        rows = [
            {
                "id": c["id"],
                "text": c["text"],
                "vector": [float(v) for v in emb],
                "source": c["metadata"].get("source", ""),
                "title": c["metadata"].get("title", ""),
                "url": c["metadata"].get("url", ""),
                "slug": c["metadata"].get("slug", ""),
                "chunk_index": c["metadata"].get("chunk_index", 0),
                "total_chunks": c["metadata"].get("total_chunks", 0),
            }
            for c, emb in zip(batch, embeddings)
        ]

        table.add(rows)
        print(f"  Upserted batch {i // BATCH_SIZE + 1} ({len(batch)} chunks)")

    print(f"\nDone. Table size: {table.count_rows()} documents")


if __name__ == "__main__":
    ingest_chunks()
