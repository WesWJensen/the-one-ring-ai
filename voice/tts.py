"""
Phase 6.18 — Text-to-speech output (deep voice for Gandalf).

Default backend: macOS `say` with the Daniel voice (deep British male).
  - Requires nothing extra — built into macOS.
  - Upgrade path: set PIPER_MODEL_PATH in .env and switch backend to "piper".

Piper upgrade:
  1. pip install piper-tts
  2. Download en_US-ryan-high.onnx from https://huggingface.co/rhasspy/piper-voices
  3. Set PIPER_MODEL_PATH=voice/models/en_US-ryan-high.onnx in .env

Usage:
    python voice/tts.py "In my experience, there is no such thing as luck."
"""

import os
import re
import sys
import subprocess
import tempfile
from pathlib import Path

MAC_VOICE  = os.getenv("SAY_VOICE", "Daniel")       # Daniel = deep British male
MAC_RATE   = int(os.getenv("SAY_RATE", "140"))      # words/min; default ~175 is too fast for Pedor
EDGE_VOICE = os.getenv("EDGE_VOICE", "en-GB-RyanNeural")  # edge-tts British male voice


def _clean_for_tts(text: str) -> str:
    """Strip markdown and other symbols that `say` would speak literally."""
    # Bold / italic markers
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'_{1,3}', '', text)
    # Inline code and code blocks
    text = re.sub(r'`+[^`]*`+', '', text, flags=re.DOTALL)
    # Headings
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # Blockquotes
    text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
    # Links: keep display text, drop URL
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Horizontal rules
    text = re.sub(r'^[-*_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Collapse excess whitespace / blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
PIPER_MODEL = os.getenv("PIPER_MODEL_PATH", "voice/models/en_US-ryan-high.onnx")
OUTPUT_DIR = Path("voice/output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def speak_mac(text: str, output_path: Path | None = None) -> Path:
    """
    Synthesize speech with macOS `say` + `afconvert` to WAV.
    Returns the path to the generated WAV file.
    """
    if output_path is None:
        output_path = OUTPUT_DIR / "response.wav"

    aiff_path = output_path.with_suffix(".aiff")

    clean = _clean_for_tts(text)
    # say → AIFF (with controlled speaking rate for a deliberate, wizardly pace)
    subprocess.run(
        ["say", "-v", MAC_VOICE, "-r", str(MAC_RATE), "-o", str(aiff_path), clean],
        check=True,
    )
    # AIFF → WAV, 44.1 kHz for smoother playback quality
    subprocess.run(
        ["afconvert", str(aiff_path), str(output_path),
         "-d", "LEI16@44100", "-f", "WAVE", "-c", "1"],
        check=True,
    )
    aiff_path.unlink(missing_ok=True)
    return output_path


def speak_piper(text: str, output_path: Path | None = None) -> Path:
    """
    Synthesize speech using Piper TTS (subprocess).
    Requires: pip install piper-tts and a downloaded .onnx voice model.
    Returns the path to the generated WAV file.
    """
    if output_path is None:
        output_path = OUTPUT_DIR / "response.wav"

    cmd = ["piper", "--model", PIPER_MODEL, "--output_file", str(output_path)]
    proc = subprocess.run(cmd, input=text, text=True, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Piper TTS failed: {proc.stderr}")
    return output_path


def speak_edge(text: str, output_path: Path | None = None) -> Path:
    """
    Synthesize speech using edge-tts (Microsoft Edge TTS, free, cross-platform).
    Requires: pip install edge-tts
    Returns the path to the generated MP3 file (playable by Chainlit).

    Runs in a dedicated thread with its own event loop so it works both
    standalone and inside Chainlit's already-running async event loop.
    """
    import asyncio
    import threading
    import edge_tts

    if output_path is None:
        output_path = OUTPUT_DIR / "response.mp3"

    clean = _clean_for_tts(text)
    error: list[Exception] = []

    def _run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _synthesize():
                communicate = edge_tts.Communicate(clean, EDGE_VOICE)
                await communicate.save(str(output_path))
            loop.run_until_complete(_synthesize())
        except Exception as exc:
            error.append(exc)
        finally:
            loop.close()

    t = threading.Thread(target=_run_in_thread, daemon=True)
    t.start()
    t.join()

    if error:
        raise error[0]
    return output_path


def speak(text: str, backend: str | None = None) -> Path:
    """
    Synthesize speech and return the audio file path.

    Args:
        text:    Text to synthesize.
        backend: "mac" (default), "piper", or "edge-tts".

    Returns:
        Path to generated audio file.
    """
    if backend is None:
        backend = os.getenv("TTS_BACKEND", "mac")

    if backend == "mac":
        return speak_mac(text)
    elif backend == "piper":
        return speak_piper(text)
    elif backend == "edge-tts":
        return speak_edge(text)
    else:
        raise ValueError(f"Unknown TTS backend: {backend!r}")


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "You shall not pass!"
    wav = speak(text)
    print(f"Saved to {wav}")
    subprocess.run(["afplay", str(wav)])
