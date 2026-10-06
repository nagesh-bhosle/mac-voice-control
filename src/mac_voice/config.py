"""Settings loaded from environment and .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class Settings:
    typesafe_api_key: str = ""
    muse_api_key: str = ""
    openai_api_key: str = ""
    wake_word: str = "Alfred"
    dry_run: bool = False
    mode: str = "dry"


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        typesafe_api_key=os.getenv("TYPESAFE_API_KEY", "").strip(),
        muse_api_key=os.getenv("MUSE_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        wake_word=os.getenv("MAC_VOICE_WAKE_WORD", "Alfred").strip() or "Alfred",
        dry_run=os.getenv("MAC_VOICE_DRY_RUN", "").strip().lower()
        in {"1", "true", "yes"},
        mode=os.getenv("MAC_VOICE_MODE", "dry").strip() or "dry",
    )
