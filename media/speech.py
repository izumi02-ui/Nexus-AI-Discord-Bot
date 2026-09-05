"""Groq speech recognition and expressive speech synthesis for Nexy."""

from __future__ import annotations

import io
import re
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


class SpeechModelAccessError(RuntimeError):
    """Groq denied access to a configured speech model."""

    def __init__(
        self,
        model: str,
        *,
        code: str = "model_access_denied",
        operation: str = "speech",
    ):
        self.model = model
        self.code = code
        self.operation = operation
        super().__init__(f"Groq denied {operation} access to {model} ({code}).")


class SpeechModelTermsRequired(SpeechModelAccessError):
    """The configured Groq speech model is blocked pending terms acceptance."""

    def __init__(self, model: str, *, operation: str = "speech"):
        super().__init__(
            model,
            code="model_terms_required",
            operation=operation,
        )


def _speech_error_text(error: Exception) -> str:
    """Collect Groq's message/body without exposing it to Discord users."""
    body = getattr(error, "body", None)
    response = getattr(error, "response", None)
    return f"{error!s} {body!r} {response!r}".casefold()


def _speech_error_code(error: Exception) -> str:
    """Extract a stable provider code without returning the raw response body."""
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        detail = body.get("error", body)
        if isinstance(detail, dict) and detail.get("code"):
            return str(detail["code"]).strip().casefold()

    detail = _speech_error_text(error)
    for candidate in (
        "model_terms_required",
        "permission_denied",
        "access_denied",
        "unauthorized",
        "forbidden",
    ):
        if candidate in detail:
            return candidate

    match = re.search(r"['\"]code['\"]\s*:\s*['\"]([^'\"]+)", detail)
    return match.group(1).casefold() if match else "model_access_denied"


def classify_speech_access_error(
    error: Exception,
    model: str,
    *,
    operation: str = "speech",
) -> SpeechModelAccessError | None:
    """Translate only provider permission/terms failures into safe exceptions."""
    detail = _speech_error_text(error)
    if "model_terms_required" in detail or "requires terms acceptance" in detail:
        return SpeechModelTermsRequired(model, operation=operation)

    status = getattr(error, "status_code", None)
    response = getattr(error, "response", None)
    status = status or getattr(response, "status_code", None)
    permission_markers = (
        "permission_denied",
        "permission denied",
        "access_denied",
        "access denied",
        "does not have access",
        "not authorized",
        "unauthorized",
        "forbidden",
        "model permission",
    )
    if status in {401, 403} or any(marker in detail for marker in permission_markers):
        return SpeechModelAccessError(
            model,
            code=_speech_error_code(error),
            operation=operation,
        )

    return None


def _raise_if_speech_access_denied(
    error: Exception,
    model: str,
    *,
    operation: str,
) -> None:
    classified = classify_speech_access_error(
        error,
        model,
        operation=operation,
    )
    if classified is not None:
        raise classified from error


def _raise_if_model_terms_required(error: Exception, model: str) -> None:
    """Backward-compatible helper retained for callers and regression tests."""
    classified = classify_speech_access_error(error, model)
    if isinstance(classified, SpeechModelTermsRequired):
        raise classified from error


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
            _raise_if_speech_access_denied(
                error,
                settings.voice_stt_model,
                operation="stt",
            )
            raise

        return (getattr(response, "text", "") or "").strip()

    async def synthesize(self, text: str) -> bytes:
        if not text or len(text) > 200:
            raise ValueError("Groq Orpheus speech input must contain 1-200 characters.")

        if settings.voice_tts_provider != "groq":
            raise RuntimeError(
                f"Unsupported VOICE_TTS_PROVIDER: {settings.voice_tts_provider}"
            )

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
            _raise_if_speech_access_denied(
                error,
                settings.voice_tts_model,
                operation="tts",
            )
            raise

        return await response.read()
