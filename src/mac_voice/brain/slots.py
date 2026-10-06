"""SlotExtractor: pull typed spans (apps, sites, URLs, dictate text) from text."""

from __future__ import annotations

import re

from mac_voice.brain import candidates as C

_URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+|[a-z0-9-]+\.(com|io|ai|dev|org|net|edu|gov)[^\s]*)", re.IGNORECASE)
_DICTATE_RE = re.compile(r"\b(?:type|dictate)(?:\s+out)?\s+(?P<text>.+)$", re.IGNORECASE | re.DOTALL)
_APP_DICTATE_RE = re.compile(
    r"^(?:in|inside|using)\s+(?P<app>.+?)\s+(?:type|dictate)(?:\s+out)?\s+(?P<text>.+)$",
    re.IGNORECASE | re.DOTALL,
)
_SPLIT_RE = re.compile(r"\s+(?:and then|then|and)\s+|,\s*", re.IGNORECASE)


def _alias_table(table: dict[str, dict]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for ident, info in table.items():
        for name in info["names"]:
            pairs.append((name.lower(), ident))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs


_APP_ALIASES = _alias_table(C.APPS)
_SITE_ALIASES = _alias_table(C.SITES)


class SlotExtractor:
    def normalize(self, text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"\s+", " ", text)
        return text.strip(" .,!?;:")

    def split_compound(self, text: str) -> list[str]:
        parts = [p.strip(" .,!?;:") for p in _SPLIT_RE.split(text.strip())]
        return [p for p in parts if p]

    def _match_alias(self, text: str, aliases: list[tuple[str, str]]) -> str | None:
        lowered = f" {text.lower()} "
        for alias, ident in aliases:
            if re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", lowered):
                return ident
        return None

    def extract_app(self, text: str) -> str | None:
        return self._match_alias(text, _APP_ALIASES)

    def extract_site(self, text: str) -> str | None:
        return self._match_alias(text, _SITE_ALIASES)

    def extract_url(self, text: str) -> str | None:
        m = _URL_RE.search(text)
        return m.group(0) if m else None

    def extract_dictate_text(self, text: str) -> str | None:
        m = _DICTATE_RE.search(text.strip())
        return m.group("text").strip() if m else None

    def match_app_dictate(self, text: str) -> tuple[str, str] | None:
        m = _APP_DICTATE_RE.match(text.strip())
        if not m:
            return None
        app = self.extract_app(m.group("app"))
        if app is None:
            return None
        body = m.group("text").strip()
        if not body:
            return None
        return app, body
