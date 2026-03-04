"""
Phase 3.10 — Retrieval pipeline using LanceDB.

Usage (terminal test):
    python rag/retrieve.py "What is the Arkenstone?"
"""

import os
import sys

import lancedb
from dotenv import load_dotenv

from rag.embed import embed_text

load_dotenv()

LANCE_DIR = os.getenv("LANCE_PERSIST_DIR", "./lance_db")
TABLE_NAME = os.getenv("LANCE_TABLE", "one_ring_lore")
TOP_K = 5


def get_table() -> lancedb.table.Table:
    db = lancedb.connect(LANCE_DIR)
    return db.open_table(TABLE_NAME)


def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Return the top-k most relevant chunks for a query."""
    table = get_table()
    query_vector = embed_text(query)

    results = (
        table.search(query_vector)
        .metric("cosine")
        .limit(k)
        .to_list()
    )

    return [
        {
            "text": r["text"],
            "metadata": {
                "source": r["source"],
                "title": r["title"],
                "url": r["url"],
                "slug": r["slug"],
                "chunk_index": r["chunk_index"],
                "total_chunks": r["total_chunks"],
            },
            "distance": r["_distance"],
        }
        for r in results
    ]


def format_context(chunks: list[dict]) -> str:
    """Concatenate retrieved chunks into a single context string."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk["metadata"].get("title", "Unknown")
        parts.append(f"[{i}] ({source})\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Who is Gandalf?"
    print(f"Query: {query}\n")
    chunks = retrieve(query)
    for i, c in enumerate(chunks, 1):
        print(f"--- Result {i} | dist={c['distance']:.4f} | {c['metadata']['title']} ---")
        print(c["text"][:300])
        print()
