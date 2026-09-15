"""Speech-to-text for the interview simulator's voice answers.

Separate from crews/llm.py: this talks to the OpenAI SDK's audio API
directly, not through crewai. Language is left to auto-detect since
candidates may answer in Hebrew or English.
"""

import io

from openai import OpenAI

from . import config

_client = OpenAI(api_key=config.OPENAI_API_KEY)


def transcribe(audio_bytes: bytes, filename: str = "answer.webm") -> str:
    buffer = io.BytesIO(audio_bytes)
    buffer.name = filename
    result = _client.audio.transcriptions.create(model="whisper-1", file=buffer)
    return result.text.strip()
