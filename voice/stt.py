"""
Phase 6.17 — Speech-to-text using faster-whisper.

Requires:
    pip install faster-whisper

Usage:
    python voice/stt.py path/to/audio.webm
    # or import transcribe() from other modules

Model is lazy-loaded on first call and cached as a module-level singleton.
"""

import sys
from pathlib import Path

from faster_whisper import WhisperModel

MODEL_SIZE = "base.en"   # options: tiny, base, small, medium, large-v3
DEVICE = "cpu"           # or "cuda" if you have a GPU
COMPUTE_TYPE = "int8"    # efficient on CPU

_model: WhisperModel | None = None


def load_model() -> WhisperModel:
    global _model
    if _model is None:
        print(f"[STT] Loading Whisper model '{MODEL_SIZE}'...")
        _model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    return _model


def transcribe(audio_path: str | Path, model: WhisperModel | None = None) -> str:
    """
    Transcribe an audio file to text.

    Accepts any format faster-whisper supports (WAV, WebM, MP3, etc.).
    Requires ffmpeg to be installed for non-WAV formats.

    Args:
        audio_path: Path to audio file.
        model:      Pre-loaded WhisperModel (lazy-loads if None).

    Returns:
        Transcribed text string.
    """
    if model is None:
        model = load_model()

    segments, _ = model.transcribe(str(audio_path), beam_size=5)
    return " ".join(seg.text.strip() for seg in segments)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else None
    if not path:
        print("Usage: python voice/stt.py <audio_file>")
        sys.exit(1)
    print(transcribe(path))
