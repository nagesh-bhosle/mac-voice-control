"""Code dictation normalization. Prefer Command Code LLM; optional Muse; else pass-through."""

from __future__ import annotations

import httpx

from mac_voice.config import DEFAULT_LLM_MODEL

MUSE_API_URL = "https://api.anthropic.com/v1/messages"
MUSE_MODEL = "claude-3-5-haiku-latest"


def normalize_local(transcript: str) -> str:
    return transcript.strip()


def normalize_via_command_code(
    transcript: str,
    api_key: str,
    model: str = DEFAULT_LLM_MODEL,
    timeout: float = 20.0,
) -> str:
    if not api_key:
        return normalize_local(transcript)
    try:
        from mac_voice.llm.command_code import CommandCodeClient

        client = CommandCodeClient(api_key=api_key, model=model or DEFAULT_LLM_MODEL, timeout=timeout)
        return client.normalize_code_dictation(transcript)
    except Exception:
        return normalize_local(transcript)


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


def normalize(
    transcript: str,
    muse_api_key: str = "",
    command_code_api_key: str = "",
    model: str = "",
) -> str:
    """Prefer Command Code (MAC_VOICE_MODEL) when keyed; else Muse; else pass-through."""
    if command_code_api_key:
        return normalize_via_command_code(
            transcript,
            command_code_api_key,
            model=model or DEFAULT_LLM_MODEL,
        )
    if muse_api_key:
        return normalize_via_muse(transcript, muse_api_key)
    return normalize_local(transcript)
