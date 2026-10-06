"""Editor control: focus IDE plus key maps for IntelliJ, VS Code, and Cursor.

Keys are sent through System Events keystrokes. Dry-run prints them.
"""

from __future__ import annotations

from mac_voice.brain import candidates as C
from mac_voice.exec import applescript, apps

KEY_SEQUENCES: dict[str, list[str]] = {
    "undo": ['keystroke "z" using command down'],
    "redo": ['keystroke "Z" using {command down, shift down}'],
    "save": ['keystroke "s" using command down'],
    "new_line": ["key code 36"],
    "delete_line": ['keystroke "d" using {command down, shift down}'],
    "select_word": ['keystroke "d" using command down'],
    "select_line": ['keystroke "l" using command down'],
    "go_to_line": ['keystroke "g" using {control down}'],
    "format": ['keystroke "l" using {command down, option down}'],
    "comment": ['keystroke "/" using command down'],
    "find": ['keystroke "f" using command down'],
    "replace": ['keystroke "f" using {command down, option down}'],
    "run": ['keystroke "r" using control down'],
    "debug": ['keystroke "d" using control down'],
    "copy": ['keystroke "c" using command down'],
    "paste": ['keystroke "v" using command down'],
    "cut": ['keystroke "x" using command down'],
}

INTELLIJ_OVERRIDES: dict[str, list[str]] = {
    "delete_line": ['keystroke "y" using command down'],
    "select_word": ['keystroke "w" using {option down}'],
    "format": ['keystroke "l" using {command down, option down}'],
    "run": ["key code 15 using shift down"],
}


def focus_editor(app: str, dry_run: bool = False) -> str:
    if app not in C.APPS:
        raise ValueError(f"Unknown editor: {app!r}")
    return apps.activate_app(app, dry_run=dry_run)


def key_sequence(command: str, app: str = "vscode") -> list[str]:
    if command not in C.EDITOR_COMMANDS:
        raise ValueError(f"Unknown editor command: {command!r}. Closed set only.")
    if app == "intellij" and command in INTELLIJ_OVERRIDES:
        return INTELLIJ_OVERRIDES[command]
    return KEY_SEQUENCES[command]


def editor_command(command: str, app: str = "vscode", dry_run: bool = False) -> str:
    seq = key_sequence(command, app)
    lines = "\n".join(f'  {s}' for s in seq)
    script = f'tell application "System Events"\n{lines}\nend tell'
    if dry_run:
        print(f"[dry-run] editor_command {command} ({app}): {' + '.join(seq)}")
        print(f"[dry-run] osascript:\n{script}")
        return "[dry-run]"
    return applescript.run_applescript(script, dry_run=dry_run)


def dictate(text: str, dry_run: bool = False) -> str:
    safe = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'tell application "System Events" to keystroke "{safe}"'
    if dry_run:
        print(f'[dry-run] dictate: "{text}"')
        return "[dry-run]"
    return applescript.run_applescript(script, dry_run=dry_run)
