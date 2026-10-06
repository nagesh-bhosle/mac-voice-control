"""Speech-to-text providers: Deepgram (preferred when keyed) or local Whisper."""

from __future__ import annotations

from pathlib import Path

from mac_voice.config import Settings
from mac_voice.stt.deepgram_engine import DeepgramEngine, DeepgramNotConfiguredError
from mac_voice.stt.whisper_engine import WhisperEngine, WhisperNotAvailableError


def resolve_stt_provider(settings: Settings) -> str:
    choice = (settings.stt_provider or "auto").lower()
    if choice == "deepgram":
        return "deepgram"
    if choice == "whisper":
        return "whisper"
    # auto
    if settings.deepgram_api_key:
        return "deepgram"
    return "whisper"


def transcribe_audio(
    audio: str | Path | bytes,
    settings: Settings,
    *,
    content_type: str = "audio/wav",
) -> str:
    """Transcribe a file path or raw bytes using the configured STT provider."""
    provider = resolve_stt_provider(settings)
    if provider == "deepgram":
        engine = DeepgramEngine(settings.deepgram_api_key)
        if isinstance(audio, (str, Path)):
            return engine.transcribe_file(audio)
        return engine.transcribe_bytes(audio, content_type=content_type)
    # whisper
    if isinstance(audio, bytes):
        raise WhisperNotAvailableError(
            "Whisper path expects a file path; pass audio as a path or use Deepgram."
        )
    engine = WhisperEngine()
    return engine.transcribe(str(audio))


__all__ = [
    "DeepgramEngine",
    "DeepgramNotConfiguredError",
    "WhisperEngine",
    "WhisperNotAvailableError",
    "resolve_stt_provider",
    "transcribe_audio",
]
