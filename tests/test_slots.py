"""Unit tests for SlotExtractor spans."""

from __future__ import annotations

from mac_voice.brain.slots import SlotExtractor

_slots = SlotExtractor()


def test_extract_app():
    assert _slots.extract_app("open chrome") == "chrome"
    assert _slots.extract_app("go to vs code") == "vscode"
    assert _slots.extract_app("open rancher") == "rancher"
    assert _slots.extract_app("open rancher desktop") == "rancher"
    assert _slots.extract_app("in intellij type hello") == "intellij"
    assert _slots.extract_app("quit slack") == "slack"
    assert _slots.extract_app("focus cursor") == "cursor"


def test_extract_app_none():
    assert _slots.extract_app("open facebook in a tab") is None
    assert _slots.extract_app("undo") is None


def test_extract_site():
    assert _slots.extract_site("open facebook in a tab") == "facebook"
    assert _slots.extract_site("go to github") == "github"
    assert _slots.extract_site("search gmail for receipts") == "gmail"


def test_extract_site_none():
    assert _slots.extract_site("open chrome") is None
    assert _slots.extract_site("undo") is None


def test_split_compound():
    assert _slots.split_compound("open chrome and open facebook in a tab") == [
        "open chrome",
        "open facebook in a tab",
    ]
    assert _slots.split_compound("undo then save") == ["undo", "save"]
    assert _slots.split_compound("open chrome, open gmail") == ["open chrome", "open gmail"]
    assert _slots.split_compound("undo") == ["undo"]


def test_match_app_dictate():
    assert _slots.match_app_dictate("in intellij type public static void main") == (
        "intellij",
        "public static void main",
    )
    assert _slots.match_app_dictate("using vs code dictate hello world") == (
        "vscode",
        "hello world",
    )


def test_match_app_dictate_none():
    assert _slots.match_app_dictate("open chrome") is None
    assert _slots.match_app_dictate("type hello") is None
    assert _slots.match_app_dictate("in nowhere type hello") is None


def test_normalize():
    assert _slots.normalize("  Open   Chrome! ") == "open chrome"
