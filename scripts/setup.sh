#!/usr/bin/env bash
# mac-voice-control setup for macOS (Apple Silicon preferred).
# Installs: Xcode CLI tools hint, Homebrew packages, uv + Python deps,
# whisper.cpp model hint, Caps Lock remap hint, and .env bootstrap.
set -euo pipefail

echo "==> mac-voice-control setup"
echo "Target OS: macOS (Darwin). Linux can run routing tests only."

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "NOTE: you are not on macOS. Only routing tests and --dry-run are supported here."
fi

if ! xcode-select -p >/dev/null 2>&1; then
  echo "==> Xcode Command Line Tools not found. Installing (macOS only)..."
  if [[ "$(uname -s)" == "Darwin" ]]; then
    xcode-select --install || true
  fi
else
  echo "==> Xcode Command Line Tools present"
fi

if ! command -v brew >/dev/null 2>&1; then
  echo "==> Homebrew not found. Install it first:"
  echo '    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
else
  echo "==> Homebrew present: $(brew --version | head -n1)"
  echo "==> Installing ffmpeg + whisper-cpp (safe to re-run)..."
  brew install ffmpeg whisper-cpp || true
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "==> uv not found. Install it:"
  echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "Then re-run this script."
else
  echo "==> uv present: $(uv --version)"
  echo "==> Syncing Python deps (includes dev extras for pytest)..."
  uv sync --extra dev
fi

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example. Add your TYPESAFE_API_KEY."
else
  echo "==> .env already exists (or no .env.example); skipping."
fi

echo ""
echo "==> Permissions (macOS System Settings): grant all three to your terminal app"
echo "    (Terminal.app, iTerm2, or VS Code) or the app that runs mac-voice:"
echo "    1. Microphone: Privacy and Security > Microphone"
echo "    2. Accessibility: Privacy and Security > Accessibility"
echo "    3. Input Monitoring: Privacy and Security > Input Monitoring"
echo "You may need to restart the terminal after granting these."
echo ""
echo "==> Optional Caps Lock remap (Caps Lock to F18 for hold-to-talk):"
echo "    macOS 14+: System Settings > Keyboard > Keyboard Shortcuts > Modifier Keys."
echo "    Or run: hidutil property --set '{\"UserKeyMapping\":[{\"HIDKeyboardModifierMappingSrc\":0x700000039,\"HIDKeyboardModifierMappingDst\":0x70000006D}]}'"
echo "    To revert, run scripts/uninstall-capslock.sh"
echo ""
echo "==> Next steps:"
echo '    uv run python -m mac_voice --text "open chrome" --dry-run'
echo "    mac-voice --hold   # on macOS, after permissions"
