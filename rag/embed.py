"""
Phase 3.8 — Embed text using nomic-embed-text via Ollama (local)
            or sentence-transformers (cloud / HF Spaces).

Backend is selected by EMBED_BACKEND env var:
  - "ollama"               (default) — requires Ollama running locally
  - "sentence-transformers"          — pure Python, works anywhere

Usage:
    python rag/embed.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

EMBED_BACKEND = os.getenv("EMBED_BACKEND", "ollama")
EMBED_MODEL   = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# Lazy-loaded sentence-transformers singleton
_st_model = None


def _get_st_model():
    global _st_model
    if _st_model is None:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _st_model


def embed_text(text: str) -> list[float]:
    """Return embedding vector for a single text string."""
    if EMBED_BACKEND == "sentence-transformers":
        return _get_st_model().encode(text).tolist()
    # default: ollama
    import ollama
    response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
    return response["embedding"]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns list of embedding vectors."""
    if EMBED_BACKEND == "sentence-transformers":
        return _get_st_model().encode(texts).tolist()
    return [embed_text(t) for t in texts]


if __name__ == "__main__":
    sample = "In a hole in the ground there lived a hobbit."
    vec = embed_text(sample)
    print(f"Backend         : {EMBED_BACKEND}")
    print(f"Vector length   : {len(vec)}")
    print(f"First 5 values  : {vec[:5]}")
