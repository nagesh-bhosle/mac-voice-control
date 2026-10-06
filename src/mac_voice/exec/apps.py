"""App control via AppleScript. Closed set only: open, activate, quit, window ops."""

from __future__ import annotations

from mac_voice.brain import candidates as C
from mac_voice.exec import applescript


def _process(app: str) -> str:
    if app not in C.APPS:
        raise ValueError(f"Unknown app: {app!r}. Closed set only.")
    return C.APPS[app]["process"]


def open_app(app: str, dry_run: bool = False) -> str:
    proc = _process(app)
    script = f'tell application "{proc}" to activate'
    return applescript.run_applescript(script, dry_run=dry_run)


def activate_app(app: str, dry_run: bool = False) -> str:
    return open_app(app, dry_run=dry_run)


def quit_app(app: str, dry_run: bool = False) -> str:
    proc = _process(app)
    script = f'tell application "{proc}" to quit'
    return applescript.run_applescript(script, dry_run=dry_run)


def new_window(app: str | None = None, dry_run: bool = False) -> str:
    if app:
        _process(app)
        target = f'tell application "{C.APPS[app]["process"]}" to make new window'
    else:
        target = 'tell application "System Events" to keystroke "n" using command down'
    return applescript.run_applescript(target, dry_run=dry_run)


def close_window(dry_run: bool = False) -> str:
    return applescript.run_applescript(
        'tell application "System Events" to keystroke "w" using command down',
        dry_run=dry_run,
    )


def minimize(dry_run: bool = False) -> str:
    return applescript.run_applescript(
        'tell application "System Events" to keystroke "m" using command down',
        dry_run=dry_run,
    )


def fullscreen(dry_run: bool = False) -> str:
    return applescript.run_applescript(
        'tell application "System Events" to key code 3 using {command down, control down}',
        dry_run=dry_run,
    )
