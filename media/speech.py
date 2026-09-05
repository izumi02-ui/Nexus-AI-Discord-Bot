"""Groq speech recognition and expressive speech synthesis for Nexy."""

from __future__ import annotations

import io
import shutil
import wave
from functools import lru_cache

from groq import AsyncGroq

from utils.settings import settings


VOICE_CONTEXT = """
You are speaking aloud in a Discord voice channel. Project Nexus may also be
called Nexy. Lead with the answer and keep the spoken reply natural, friendly,
and under 180 characters. Do not read Markdown syntax, raw URLs, citations,
code, or long lists aloud. Put additional detail in the text response.
""".strip()


class SpeechModelTermsRequired(RuntimeError):
    """The configured Groq speech model is blocked pending org approval."""

    def __init__(self, model: str):
        self.model = model
        super().__init__(f"Groq model terms are not enabled for {model}.")


def _speech_error_text(error: Exception) -> str:
    """Collect Groq's message/body without exposing it to Discord users."""
    body = getattr(error, "body", None)
    response = getattr(error, "response", None)
    return f"{error!s} {body!r} {response!r}".casefold()


def _raise_if_model_terms_required(error: Exception, model: str) -> None:
    detail = _speech_error_text(error)
    if "model_terms_required" in detail or "requires terms acceptance" in detail:
        raise SpeechModelTermsRequired(model) from error


def pcm_to_wav(pcm: bytes) -> bytes:
    """Wrap Discord's decoded 48 kHz stereo PCM in a WAV container."""
    destination = io.BytesIO()

    with wave.open(destination, "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(48_000)
        output.writeframes(pcm)

    return destination.getvalue()


@lru_cache(maxsize=1)
def ffmpeg_executable() -> str:
    """Use an explicit/system FFmpeg, then the wheel-bundled binary."""
    if settings.ffmpeg_path:
        return settings.ffmpeg_path

    system = shutil.which("ffmpeg")

    if system:
        return system

    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as error:  # noqa: BLE001
        raise RuntimeError(
            "FFmpeg is unavailable. Set FFMPEG_PATH or install imageio-ffmpeg."
        ) from error


class GroqSpeech:
    """One reusable async client for STT and the configured female TTS voice."""

    def __init__(self):
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is required for live voice chat.")

        self.client = AsyncGroq(api_key=settings.groq_api_key)

    async def transcribe(self, pcm: bytes) -> str:
        arguments = {
            "model": settings.voice_stt_model,
            "file": ("nexy-turn.wav", pcm_to_wav(pcm)),
            "response_format": "json",
            "temperature": 0.0,
        }

        if settings.voice_language:
            arguments["language"] = settings.voice_language

        try:
            response = await self.client.audio.transcriptions.create(**arguments)
        except Exception as error:  # noqa: BLE001 - translate provider configuration errors
            _raise_if_model_terms_required(error, settings.voice_stt_model)
            raise

        return (getattr(response, "text", "") or "").strip()

    async def synthesize(self, text: str) -> bytes:
        if not text or len(text) > 200:
            raise ValueError("Groq Orpheus speech input must contain 1-200 characters.")

        try:
            response = await self.client.audio.speech.create(
                model=settings.voice_tts_model,
                voice=settings.voice_tts_voice,
                input=text,
                response_format="wav",
                sample_rate=48_000,
                speed=settings.voice_tts_speed,
            )
        except Exception as error:  # noqa: BLE001 - translate provider configuration errors
            _raise_if_model_terms_required(error, settings.voice_tts_model)
            raise

        return await response.read()
