# Setup

## Phase 1 — Foundation

### Step 1: Python environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: Copy env config
```bash
cp .env.example .env
# Edit .env if you want non-default values
```

### Step 3: Pull Ollama models ← **do this yourself**
```bash
# Make sure Ollama is running: https://ollama.com
ollama pull llama3.1
ollama pull nomic-embed-text

# Smoke test
ollama run llama3.1 "Say hello as Gandalf"
```

---

## Phase 2 — Data Pipeline
```bash
python scripts/scrape.py    # scrape tolkiengateway.net
python scripts/clean.py     # normalize text
python scripts/chunk.py     # split into retrieval chunks
```

## Phase 3 — Ingest into ChromaDB
```bash
python rag/store.py         # embed + store all chunks
python rag/retrieve.py "What is the Arkenstone?"  # test retrieval
```

## Phase 4 — Test the agent
```bash
python agent/chain.py "Why did Gandalf choose Bilbo?"
```

## Phase 5 — Launch chat UI
```bash
chainlit run ui/app.py --watch
```

## Phase 6 — Voice (install separately)
```bash
pip install faster-whisper
# For TTS choose Piper or Coqui — see voice/tts.py
```

## Phase 7 — MCP server
```bash
python mcp/server.py
# Then add to Claude Desktop config — see mcp/server.py docstring
```
