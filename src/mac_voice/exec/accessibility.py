"""Accessibility helpers. Guarded so import works on Linux without pyobjc."""

from __future__ import annotations

import platform


class AccessibilityNotAvailableError(RuntimeError):
    pass


def is_available() -> bool:
    if platform.system() != "Darwin":
        return False
    try:
        import objc  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False
    except Exception:
        return False


def check_permission(dry_run: bool = False) -> bool:
    if dry_run:
        print("[dry-run] accessibility permission check skipped")
        return True
    if platform.system() != "Darwin":
        raise AccessibilityNotAvailableError("Accessibility APIs require macOS")
    return is_available()


def frontmost_app(dry_run: bool = False) -> str:
    if dry_run:
        return "[dry-run] frontmost app"
    if platform.system() != "Darwin":
        raise AccessibilityNotAvailableError("Accessibility APIs require macOS")
    raise AccessibilityNotAvailableError("pyobjc bridge not wired in MVP; grant Accessibility and retry")
