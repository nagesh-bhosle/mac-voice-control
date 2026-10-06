"""Settings loaded from environment and .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

DEFAULT_LLM_MODEL = "meta/muse-spark-1.3-contributor"
JEV_MODEL = "typesafe/jev"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # Legacy TypeSafe direct key — unused for Jev when COMMAND_CODE_API_KEY is set.
    typesafe_api_key: str = ""
    muse_api_key: str = ""
    openai_api_key: str = ""
    deepgram_api_key: str = ""
    # Auth for Command Code chat models AND typesafe/jev (systemone).
    command_code_api_key: str = ""
    llm_model: str = DEFAULT_LLM_MODEL
    stt_provider: str = "auto"  # auto | deepgram | whisper
    llm_enabled: bool = False
    jev_enabled: bool = False
    wake_word: str = "Alfred"
    dry_run: bool = False
    mode: str = "dry"


def load_settings() -> Settings:
    load_dotenv()
    command_code = (
        os.getenv("COMMAND_CODE_API_KEY", "").strip()
        or os.getenv("CMD_API_KEY", "").strip()
    )
    stt = (os.getenv("MAC_VOICE_STT", "auto").strip() or "auto").lower()
    if stt not in {"auto", "deepgram", "whisper"}:
        stt = "auto"
    return Settings(
        typesafe_api_key=os.getenv("TYPESAFE_API_KEY", "").strip(),
        muse_api_key=os.getenv("MUSE_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        deepgram_api_key=os.getenv("DEEPGRAM_API_KEY", "").strip(),
        command_code_api_key=command_code,
        llm_model=(
            os.getenv("MAC_VOICE_MODEL", "").strip()
            or DEFAULT_LLM_MODEL
        ),
        stt_provider=stt,
        llm_enabled=_truthy(os.getenv("MAC_VOICE_USE_LLM")),
        jev_enabled=_truthy(os.getenv("MAC_VOICE_USE_JEV")),
        wake_word=os.getenv("MAC_VOICE_WAKE_WORD", "Alfred").strip() or "Alfred",
        dry_run=_truthy(os.getenv("MAC_VOICE_DRY_RUN")),
        mode=os.getenv("MAC_VOICE_MODE", "dry").strip() or "dry",
    )
