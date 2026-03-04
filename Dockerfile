FROM python:3.12-slim

# System deps: ffmpeg for faster-whisper audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Cloud backend env (overridden at runtime by HF Spaces secrets if needed)
ENV LLM_BACKEND=groq \
    EMBED_BACKEND=sentence-transformers \
    TTS_BACKEND=edge-tts \
    LANCE_PERSIST_DIR=/app/lance_db \
    LANCE_TABLE=one_ring_lore

# Pre-download the sentence-transformers model and build the vector store.
# This bakes the index into the image so cold starts are fast.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"
RUN python -m rag.store

# HF Spaces expects port 7860
EXPOSE 7860

CMD ["chainlit", "run", "ui/app.py", "--host", "0.0.0.0", "--port", "7860"]
