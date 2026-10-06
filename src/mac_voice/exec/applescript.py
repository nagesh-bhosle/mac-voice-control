"""AppleScript runner. Executes osascript on macOS; logs on dry-run or Linux."""

from __future__ import annotations

import platform
import subprocess


class NotOnMacOSError(RuntimeError):
    pass


def is_macos() -> bool:
    return platform.system() == "Darwin"


def run_applescript(script: str, dry_run: bool = False) -> str:
    if dry_run:
        print(f"[dry-run] osascript:\n{script}")
        return "[dry-run]"
    if not is_macos():
        raise NotOnMacOSError("AppleScript execution requires macOS (Darwin)")
    proc = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"osascript failed: {proc.stderr.strip()}")
    return proc.stdout.strip()
