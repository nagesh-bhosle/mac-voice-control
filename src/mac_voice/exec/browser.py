"""Browser control for Chrome and Safari via AppleScript."""

from __future__ import annotations

from mac_voice.brain import candidates as C
from mac_voice.exec import applescript


def _resolve_url(site: str, url: str) -> str:
    if site in C.SITES:
        return url or C.SITES[site]["url"]
    if url:
        return url if url.startswith("http") else f"https://{url}"
    raise ValueError("open_url needs a known site or a URL")


def open_url(site: str = "url", url: str = "", new_tab: bool = False, browser: str = "chrome", dry_run: bool = False) -> str:
    resolved = _resolve_url(site, url)
    if browser not in ("chrome", "safari"):
        raise ValueError("browser must be chrome or safari")
    if browser == "chrome":
        if new_tab:
            script = (
                'tell application "Google Chrome"\n'
                "  activate\n"
                '  tell front window to make new tab with properties {URL:"' + resolved + '"}\n'
                "end tell"
            )
        else:
            script = f'tell application "Google Chrome" to open location "{resolved}"'
    else:
        if new_tab:
            script = (
                'tell application "Safari"\n'
                "  activate\n"
                '  tell front window to make new tab with properties {URL:"' + resolved + '"}\n'
                "end tell"
            )
        else:
            script = f'tell application "Safari" to open location "{resolved}"'
    return applescript.run_applescript(script, dry_run=dry_run)


def new_tab(browser: str = "chrome", dry_run: bool = False) -> str:
    return applescript.run_applescript(
        'tell application "System Events" to keystroke "t" using command down',
        dry_run=dry_run,
    )


def close_tab(dry_run: bool = False) -> str:
    return applescript.run_applescript(
        'tell application "System Events" to keystroke "w" using command down',
        dry_run=dry_run,
    )


def next_tab(dry_run: bool = False) -> str:
    return applescript.run_applescript(
        'tell application "System Events" to key code 48 using {command down, option down}',
        dry_run=dry_run,
    )


def prev_tab(dry_run: bool = False) -> str:
    return applescript.run_applescript(
        'tell application "System Events" to key code 48 using {command down, option down, shift down}',
        dry_run=dry_run,
    )


def search_web(query: str, engine: str = "google", dry_run: bool = False) -> str:
    import urllib.parse

    q = urllib.parse.quote_plus(query)
    url = f"https://www.google.com/search?q={q}" if engine == "google" else f"https://duckduckgo.com/?q={q}"
    return open_url(site="url", url=url, dry_run=dry_run)
