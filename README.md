---
title: Pedor Lambengolmor Lore Oracle
emoji: 📚
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
---

# Pedor — Lambengolmor Lore Oracle

> *"The names of things are not merely labels — they are the shape of thought itself, pressed into sound."*

A local-first, voice-enabled AI lorekeeper built on Tolkien's world. Ask Pedor — an elvish scholar of the Lambengolmor order — about Middle-earth history, languages, and the Quest of Erebor. Speak or type; he answers in kind.

---

## What it does

- **Voice in, voice out** — speak a question; Whisper transcribes it, the answer is synthesized and played back automatically
- **RAG pipeline** — 1,238 lore chunks from 24 Tolkien Gateway articles, embedded locally with `nomic-embed-text` and stored in LanceDB
- **In-character persona** — analytical, slightly aloof elvish scholar with a thread of quiet wonder; responds grounded in retrieved lore
- **MCP tool** — expose `ask_gandalf` as an MCP server so Pedor can be called from Claude Desktop
- **Fully local** — no cloud API keys required; runs on Ollama + LanceDB

---

## Stack

| Layer | Technology |
|---|---|
| LLM | `llama3.1` via [Ollama](https://ollama.com) (local) |
| Embeddings | `nomic-embed-text` via Ollama |
| Vector store | [LanceDB](https://lancedb.com) (persistent, cosine similarity) |
| STT | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `base.en` |
| TTS | macOS `say -v Daniel` + `afconvert` to WAV |
| UI | [Chainlit](https://chainlit.io) 2.x with voice I/O |
| MCP | Custom stdio JSON-RPC server (no SDK) |
| Python | 3.12 |

---

## Setup

**Prerequisites:** macOS, Python 3.12, [Ollama](https://ollama.com)

```bash
# 1. Pull models
ollama pull llama3.1
ollama pull nomic-embed-text

# 2. Clone and install
git clone https://github.com/YOUR_USERNAME/the_one_ring_ai.git
cd the_one_ring_ai
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp .env.example .env   # defaults work as-is for local Ollama

# 4. Build the knowledge base
python scripts/scrape.py
python scripts/clean.py
python scripts/chunk.py
python -m rag.store

# 5. Run
chainlit run ui/app.py --watch
```

Open [http://localhost:8000](http://localhost:8000).

---

## Project structure

```
the_one_ring_ai/
├── agent/          # Persona prompt + RAG chain
├── mcp/            # MCP stdio server for Claude Desktop
├── public/         # Custom JS (VAD + auto-play)
├── rag/            # Embed, store, retrieve (LanceDB)
├── scripts/        # Scrape → clean → chunk pipeline
├── ui/             # Chainlit app
└── voice/          # Whisper STT + macOS TTS
```

---

## Claude Desktop integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pedor": {
      "command": "/path/to/.venv/bin/python",
      "args": ["/path/to/the_one_ring_ai/mcp/server.py"]
    }
  }
}
```

Then ask Claude: *"Use the ask_gandalf tool to tell me about the dragon Smaug."*

---

## Voice behaviour

| Feature | Detail |
|---|---|
| Auto-stop | Silence detection via Web Audio API AnalyserNode; stops after ~1.5 s of quiet |
| Auto-play | AudioContext unlocked on first mic press; response plays back immediately |
| TTS voice | Daniel (British English, macOS); rate 140 wpm; markdown stripped before synthesis |

Tune `SILENCE_THRESHOLD_DB`, `SILENCE_TIMEOUT_MS` in `public/auto_play.js` and `SAY_RATE` in `.env`.

---

## Notes

- `lance_db/`, `voice/output/`, and `.env` are gitignored — run the pipeline to regenerate locally
- Python 3.14 breaks pydantic v1 compat (ChromaDB) and anyio/starlette; use 3.12
- MCP server redirects stdout → stderr during imports to keep the JSON-RPC channel clean
