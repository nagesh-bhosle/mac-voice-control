"""Deepgram REST speech-to-text (nova-2 / nova-3)."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import httpx

DEEPGRAM_LISTEN_URL = "https://api.deepgram.com/v1/listen"
DEFAULT_MODEL = "nova-2"


class DeepgramNotConfiguredError(RuntimeError):
    pass


class DeepgramEngine:
    """Transcribe audio bytes or files via Deepgram REST /v1/listen."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout

    def require_key(self) -> None:
        if not self.api_key:
            raise DeepgramNotConfiguredError(
                "DEEPGRAM_API_KEY is not set. Add it to .env or pass an api_key."
            )

    def listen_url(self) -> str:
        return f"{DEEPGRAM_LISTEN_URL}?model={self.model}&smart_format=true&punctuate=true"

    def auth_headers(self) -> dict[str, str]:
        self.require_key()
        return {"Authorization": f"Token {self.api_key}"}

    def transcribe_bytes(
        self,
        audio: bytes,
        *,
        content_type: str = "audio/wav",
    ) -> str:
        self.require_key()
        if not audio:
            return ""
        headers = {
            **self.auth_headers(),
            "Content-Type": content_type,
        }
        resp = httpx.post(
            self.listen_url(),
            headers=headers,
            content=audio,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return self._extract_transcript(resp.json())

    def transcribe_file(self, path: str | Path, *, content_type: str | None = None) -> str:
        path = Path(path)
        data = path.read_bytes()
        ctype = content_type or _guess_content_type(path)
        return self.transcribe_bytes(data, content_type=ctype)

    def transcribe_stream(self, stream: BinaryIO, *, content_type: str = "audio/wav") -> str:
        return self.transcribe_bytes(stream.read(), content_type=content_type)

    @staticmethod
    def _extract_transcript(payload: dict) -> str:
        try:
            channels = payload["results"]["channels"]
            alts = channels[0]["alternatives"]
            return (alts[0].get("transcript") or "").strip()
        except (KeyError, IndexError, TypeError):
            return ""


def _guess_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".m4a": "audio/mp4",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
    }.get(suffix, "application/octet-stream")
