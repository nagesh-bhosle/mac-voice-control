"""Code dictation normalization. Pass-through by default; optional Muse path."""

from __future__ import annotations

import httpx

MUSE_API_URL = "https://api.anthropic.com/v1/messages"
MUSE_MODEL = "claude-3-5-haiku-latest"


def normalize_local(transcript: str) -> str:
    return transcript.strip()


def normalize_via_muse(transcript: str, api_key: str, timeout: float = 20.0) -> str:
    if not api_key:
        return normalize_local(transcript)
    try:
        resp = httpx.post(
            MUSE_API_URL,
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": MUSE_MODEL,
                "max_tokens": 512,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Convert this spoken code into exact typed code text. "
                            "Reply with only the code, no explanation. Spoken: " + transcript
                        ),
                    }
                ],
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        blocks = data.get("content", [])
        texts = [b.get("text", "") for b in blocks if isinstance(b, dict)]
        joined = "".join(texts).strip()
        return joined or normalize_local(transcript)
    except Exception:
        return normalize_local(transcript)


def normalize(transcript: str, muse_api_key: str = "") -> str:
    if muse_api_key:
        return normalize_via_muse(transcript, muse_api_key)
    return normalize_local(transcript)
