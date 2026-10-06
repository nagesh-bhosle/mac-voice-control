"""Terminal feedback plus optional macOS `say`."""

from __future__ import annotations

import platform
import subprocess


def status(message: str) -> None:
    print(message)


def speak(text: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"[dry-run] say: {text}")
        return
    if platform.system() != "Darwin":
        print(f"[say] {text}")
        return
    try:
        subprocess.run(["say", text], check=False)
    except FileNotFoundError:
        print(f"[say] {text}")


def plan_human(plan) -> str:
    lines = [f'Utterance: "{plan.utterance}" (via {plan.via})']
    for i, a in enumerate(plan.actions, 1):
        flag = " [confirm]" if a.confirm else ""
        lines.append(f"  {i}. {a.action} {a.args}{flag}")
    if plan.needs_confirm:
        lines.append("Note: destructive action needs --yes to execute.")
    return "\n".join(lines)
