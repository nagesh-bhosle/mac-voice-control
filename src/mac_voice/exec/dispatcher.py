"""Dispatch closed-set actions to exec helpers.

Only actions listed in brain/candidates.py ACTIONS are accepted. Anything
else raises ValueError and is never executed. dry_run is passed through to
every helper so --dry-run never touches AX or AppleScript.
"""

from __future__ import annotations

from typing import Any

from mac_voice.brain import candidates as C
from mac_voice.brain.jev_router import Action
from mac_voice.dictate import muse_normalize
from mac_voice.exec import applescript, apps, browser, editor
from mac_voice.ui import feedback


def dispatch_action(
    action: Action | dict[str, Any],
    dry_run: bool = False,
    muse_api_key: str = "",
) -> str:
    if isinstance(action, Action):
        name = action.action
        args = dict(action.args)
    else:
        name = action.get("action", "")
        raw_args = action.get("args", {})
        args = dict(raw_args) if isinstance(raw_args, dict) else {}
    if name not in C.ACTIONS:
        raise ValueError(f"Refusing unknown action: {name!r}. Closed set only.")

    if name == "open_app":
        return apps.open_app(args["app"], dry_run=dry_run)
    if name == "activate_app":
        return apps.activate_app(args["app"], dry_run=dry_run)
    if name == "quit_app":
        return apps.quit_app(args["app"], dry_run=dry_run)
    if name == "new_window":
        return apps.new_window(args.get("app"), dry_run=dry_run)
    if name == "close_window":
        return apps.close_window(dry_run=dry_run)
    if name == "minimize":
        return apps.minimize(dry_run=dry_run)
    if name == "fullscreen":
        return apps.fullscreen(dry_run=dry_run)

    if name == "open_url":
        return browser.open_url(
            site=args.get("site", "url"),
            url=args.get("url", ""),
            new_tab=bool(args.get("new_tab", False)),
            browser=args.get("browser", "chrome"),
            dry_run=dry_run,
        )
    if name == "new_tab":
        return browser.new_tab(dry_run=dry_run)
    if name == "close_tab":
        return browser.close_tab(dry_run=dry_run)
    if name == "next_tab":
        return browser.next_tab(dry_run=dry_run)
    if name == "prev_tab":
        return browser.prev_tab(dry_run=dry_run)
    if name == "search_web":
        return browser.search_web(
            args.get("query", ""),
            engine=args.get("engine", "google"),
            dry_run=dry_run,
        )

    if name == "focus_editor":
        return editor.focus_editor(args["app"], dry_run=dry_run)
    if name == "dictate":
        text = muse_normalize.normalize(args.get("text", ""), muse_api_key)
        return editor.dictate(text, dry_run=dry_run)
    if name == "editor_command":
        return editor.editor_command(
            args["command"],
            app=args.get("app", "vscode"),
            dry_run=dry_run,
        )
    if name == "code_snippet":
        template = args.get("template", "")
        text = muse_normalize.normalize(template, muse_api_key) if template else ""
        return editor.dictate(text, dry_run=dry_run)

    if name == "volume_up":
        return applescript.run_applescript(
            'tell application "System Events" to key code 72',
            dry_run=dry_run,
        )
    if name == "volume_down":
        return applescript.run_applescript(
            'tell application "System Events" to key code 73',
            dry_run=dry_run,
        )
    if name == "mute":
        return applescript.run_applescript(
            'tell application "System Events" to key code 74',
            dry_run=dry_run,
        )
    if name == "screenshot":
        return applescript.run_applescript(
            'do shell script "screencapture -x -t png '
            "$HOME/Desktop/mac-voice-$(date +%Y%m%d-%H%M%S).png\"",
            dry_run=dry_run,
        )
    if name == "say":
        feedback.speak(args.get("text", ""), dry_run=dry_run)
        return "[said]" if not dry_run else "[dry-run]"

    raise ValueError(f"Refusing unknown action: {name!r}. Closed set only.")


def dispatch_many(
    actions: list[Action | dict[str, Any]],
    dry_run: bool = False,
    muse_api_key: str = "",
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for action in actions:
        name = action.action if isinstance(action, Action) else action.get("action", "")
        try:
            result = dispatch_action(action, dry_run=dry_run, muse_api_key=muse_api_key)
            results.append({"action": name, "ok": True, "result": result})
        except Exception as exc:
            results.append({"action": name, "ok": False, "error": str(exc)})
    return results
