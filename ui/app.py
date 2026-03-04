"""
Phase 5/6 — Chainlit chat UI with conversation memory and voice I/O.

Usage:
    chainlit run ui/app.py --watch

Voice input:  Click the mic button → speak → Whisper transcribes.
Voice output: Pedor's reply is synthesized and played back automatically.
"""

import sys
import tempfile
import wave
from pathlib import Path

# Chainlit streams raw PCM: 16-bit signed, mono, at sample_rate from config.toml
PCM_SAMPLE_RATE = 24000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # bytes (16-bit)

# Ensure project root is on sys.path so `agent`, `rag`, `voice` packages resolve
sys.path.insert(0, str(Path(__file__).parent.parent))

import chainlit as cl
from agent.chain import ask_gandalf
from voice.stt import transcribe
from voice.tts import speak

WELCOME_MESSAGE = """\
*"The names of things are not merely labels — they are the shape of thought \
itself, pressed into sound."*

I am **Pedor**, a Lambengolmor of the Eldar — keeper of tongues, chronicler \
of lore. The histories of Middle-earth, its languages and its peoples, are \
my long study.

Ask me of the Shire or the Lonely Mountain, of dragon-speech or dwarvish rune, \
of the deep ages or the events of the Quest of Erebor. Speak or write — \
I am at home in both.

What would you know?
"""

MAX_HISTORY_TURNS = 10

AUTHOR = "Pedor"


@cl.on_chat_start
async def on_start():
    cl.user_session.set("history", [])
    await cl.Message(author=AUTHOR, content=WELCOME_MESSAGE).send()


@cl.on_message
async def on_message(message: cl.Message):
    await _respond(message.content)


# ── Voice input ──────────────────────────────────────────────────────────────

@cl.on_audio_start
async def on_audio_start():
    """Called by Chainlit when the user starts recording."""
    cl.user_session.set("audio_buffer", bytearray())
    return True


@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    """Accumulate raw audio bytes streamed from the browser."""
    buf: bytearray = cl.user_session.get("audio_buffer", bytearray())
    buf.extend(chunk.data)
    cl.user_session.set("audio_buffer", buf)


@cl.on_audio_end
async def on_audio_end():
    """Transcribe buffered audio, then respond as normal."""
    buf: bytearray = cl.user_session.get("audio_buffer", bytearray())
    if not buf:
        return

    # Wrap raw PCM bytes in a WAV container so faster-whisper can read it
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio_path = f.name
    with wave.open(audio_path, "wb") as wf:
        wf.setnchannels(PCM_CHANNELS)
        wf.setsampwidth(PCM_SAMPLE_WIDTH)
        wf.setframerate(PCM_SAMPLE_RATE)
        wf.writeframes(bytes(buf))

    await cl.Message(author="System", content="*Transcribing...*").send()
    question = transcribe(audio_path)
    Path(audio_path).unlink(missing_ok=True)

    if not question.strip():
        await cl.Message(author=AUTHOR, content="*The words did not reach me. Speak again, if you will.*").send()
        return

    # Echo what was heard so the user can see the transcription
    await cl.Message(author="You", content=question).send()
    await _respond(question, voice_reply=True)


# ── Shared response logic ────────────────────────────────────────────────────

async def _respond(question: str, voice_reply: bool = False):
    history: list[dict] = cl.user_session.get("history", [])

    async with cl.Step(name="Consulting the lore...") as step:
        step.input = question
        response = ask_gandalf(question, history=history)
        step.output = response

    elements = []
    if voice_reply:
        wav_path = speak(response)
        elements.append(cl.Audio(name="pedor.wav", path=str(wav_path), display="inline"))

    await cl.Message(author=AUTHOR, content=response, elements=elements).send()

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": response})
    if len(history) > MAX_HISTORY_TURNS * 2:
        history = history[-(MAX_HISTORY_TURNS * 2):]
    cl.user_session.set("history", history)
