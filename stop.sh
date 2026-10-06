#!/usr/bin/env bash
# Stop the background mac-voice process started by ./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PID_FILE="$ROOT/.mac-voice.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "mac-voice is not running (no pid file)."
  exit 0
fi

pid="$(tr -d '[:space:]' < "$PID_FILE" || true)"
if [[ -z "$pid" ]]; then
  echo "Empty pid file; removing."
  rm -f "$PID_FILE"
  exit 0
fi

if ! kill -0 "$pid" 2>/dev/null; then
  echo "mac-voice not running (stale pid $pid). Cleaning up."
  rm -f "$PID_FILE"
  exit 0
fi

echo "Stopping mac-voice (pid $pid)..."
# Graceful first: SIGTERM to the wrapper (and hope children get it).
kill -TERM "$pid" 2>/dev/null || true

# Also terminate any direct child python mac_voice processes of this tree.
if command -v pgrep >/dev/null 2>&1; then
  # shellcheck disable=SC2009
  children="$(pgrep -P "$pid" 2>/dev/null || true)"
  for c in $children; do
    kill -TERM "$c" 2>/dev/null || true
  done
fi

# Wait up to ~5s for graceful exit
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if ! kill -0 "$pid" 2>/dev/null; then
    break
  fi
  sleep 0.5
done

if kill -0 "$pid" 2>/dev/null; then
  echo "Process still alive; sending SIGKILL..."
  kill -KILL "$pid" 2>/dev/null || true
  if command -v pgrep >/dev/null 2>&1; then
    children="$(pgrep -P "$pid" 2>/dev/null || true)"
    for c in $children; do
      kill -KILL "$c" 2>/dev/null || true
    done
  fi
  sleep 0.2
fi

rm -f "$PID_FILE"

if kill -0 "$pid" 2>/dev/null; then
  echo "error: failed to stop pid $pid" >&2
  exit 1
fi

echo "mac-voice stopped."
