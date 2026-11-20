"""
voice.py – Audio transcription using Groq Whisper.
"""
from groq import Groq
from config import GROQ_API_KEY, STT_MODEL


def transcribe(audio_bytes: bytes) -> str:
    """
    Transcribe audio bytes using Groq client STT model.
    Returns transcribed string, or empty string on error.
    """
    if not audio_bytes or not GROQ_API_KEY:
        return ""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        transcript = client.audio.transcriptions.create(
            model=STT_MODEL,
            file=("audio.wav", audio_bytes),
            response_format="text"
        )
        return transcript.strip() if isinstance(transcript, str) else getattr(transcript, "text", "").strip()
    except Exception:
        return ""
