"""
Phase 7.20 — Wrap the Pedor (Lambengolmor) agent as an MCP server.

Exposes a single tool: ask_gandalf (internal name retained for compatibility)
Claude Desktop connects to this via stdio transport.

Usage:
    python mcp/server.py

MCP config for Claude Desktop (~/.claude/claude_desktop_config.json):
{
  "mcpServers": {
    "pedor": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["/absolute/path/to/mcp/server.py"]
    }
  }
}
"""

import json
import sys
from pathlib import Path

# ── stdout guard ─────────────────────────────────────────────────────────────
# The MCP stdio transport uses stdout exclusively for JSON-RPC.
# Any stray print() from libraries (LanceDB, Ollama, dotenv, etc.) would
# corrupt the stream. Redirect stdout → stderr before importing anything.
_real_stdout = sys.stdout
sys.stdout = sys.stderr

sys.path.insert(0, str(Path(__file__).parent.parent))
from agent.chain import ask_gandalf

sys.stdout = _real_stdout
# ─────────────────────────────────────────────────────────────────────────────


def _ok(req_id, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def _err(req_id, code: int, message: str) -> dict:
    # MCP spec: id must be string | number | null; keep null only when truly unknown
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


def handle_request(request: dict) -> dict | None:
    method  = request.get("method")
    req_id  = request.get("id")

    # Notifications (no id) must not receive a response
    if req_id is None and not method:
        return None

    if method == "initialize":
        return _ok(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "pedor-lore", "version": "1.0.0"},
        })

    if method == "notifications/initialized":
        return None  # server-bound notification; no reply

    if method == "tools/list":
        return _ok(req_id, {
            "tools": [
                {
                    "name": "ask_gandalf",
                    "description": (
                        "Ask Pedor, a Lambengolmor elvish lorekeeper, a question "
                        "about Middle-earth lore, languages, The Hobbit, or the Quest "
                        "of Erebor. Returns an in-character response grounded in "
                        "retrieved lore."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The lore question to ask Pedor.",
                            }
                        },
                        "required": ["question"],
                    },
                }
            ]
        })

    if method == "tools/call":
        tool_name = request.get("params", {}).get("name")
        args      = request.get("params", {}).get("arguments", {})

        if tool_name == "ask_gandalf":
            question = args.get("question", "")
            try:
                answer = ask_gandalf(question)
                return _ok(req_id, {
                    "content": [{"type": "text", "text": answer}],
                    "isError": False,
                })
            except Exception as e:
                return _ok(req_id, {
                    "content": [{"type": "text", "text": f"Error: {e}"}],
                    "isError": True,
                })

        return _err(req_id, -32602, f"Unknown tool: {tool_name}")

    # Unknown method
    return _err(req_id, -32601, f"Method not found: {method}")


def run_stdio_server():
    """Run the MCP server over stdio (line-delimited JSON-RPC)."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request  = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as e:
            err = _err(None, -32700, f"Parse error: {e}")
            sys.stdout.write(json.dumps(err) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
