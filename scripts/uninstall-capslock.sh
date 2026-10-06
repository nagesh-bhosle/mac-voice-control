#!/usr/bin/env bash
# Revert the Caps Lock remap suggested by scripts/setup.sh.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script only applies to macOS."
  exit 0
fi

echo "==> Clearing hidutil UserKeyMapping (restores Caps Lock default)..."
hidutil property --set '{"UserKeyMapping":[]}' || true
echo "Done. If Caps Lock still acts as F18, log out and back in."
