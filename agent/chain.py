"""
Phase 4.12 — RAG chain: retrieve → format → generate.

LLM backend is selected by LLM_BACKEND env var:
  - "ollama"  (default) — requires Ollama running locally
  - "groq"              — Groq cloud API, fast free tier

Usage (terminal test):
    python agent/chain.py "Why did Gandalf choose Bilbo for the quest?"
"""
# Note: function is named ask_gandalf for historical reasons; persona is now Pedor.

import os
import sys

from dotenv import load_dotenv

from agent.prompt import GANDALF_SYSTEM_PROMPT
from rag.retrieve import retrieve, format_context

load_dotenv()

LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")
LLM_MODEL   = os.getenv("OLLAMA_LLM_MODEL", "llama3.1")
GROQ_MODEL  = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
TOP_K       = int(os.getenv("RETRIEVAL_TOP_K", 5))


def _generate(messages: list[dict]) -> str:
    """Call the configured LLM and return the response string."""
    if LLM_BACKEND == "groq":
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        resp = client.chat.completions.create(model=GROQ_MODEL, messages=messages)
        return resp.choices[0].message.content
    # default: ollama
    import ollama
    resp = ollama.chat(model=LLM_MODEL, messages=messages)
    return resp["message"]["content"]


def ask_gandalf(question: str, history: list[dict] | None = None) -> str:
    """
    Full RAG pipeline:
      1. Retrieve relevant lore chunks for the question.
      2. Format them into context.
      3. Call the LLM with Pedor (Lambengolmor) system prompt + context.
      4. Return the response string.
    """
    chunks  = retrieve(question, k=TOP_K)
    context = format_context(chunks)

    system_content = GANDALF_SYSTEM_PROMPT.format(context=context)
    messages = [{"role": "system", "content": system_content}]

    if history:
        messages.extend(history)

    messages.append({"role": "user", "content": question})

    return _generate(messages)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Who are you?"
    print(f"Q: {question}\n")
    answer = ask_gandalf(question)
    print(f"Pedor: {answer}")
