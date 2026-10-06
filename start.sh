#!/usr/bin/env bash
# Start mac-voice-control in background hold-to-talk mode.
# Prompts for missing API keys (secrets are not echoed), writes .env, then
# runs: uv run python -m mac_voice --hold (looped so the daemon stays up).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PID_FILE="$ROOT/.mac-voice.pid"
LOG_FILE="$ROOT/.mac-voice.log"
ENV_FILE="$ROOT/.env"

is_pid_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

load_env_file() {
  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE" | tr -d '\r')
    set +a
  fi
}

# Upsert KEY=VALUE in .env without printing the value. Creates file if needed.
upsert_env() {
  local key="$1"
  local value="$2"
  local tmp
  tmp="$(mktemp)"
  touch "$ENV_FILE"
  if grep -qE "^${key}=" "$ENV_FILE" 2>/dev/null; then
    awk -v k="$key" -v v="$value" '
      BEGIN { done=0 }
      $0 ~ ("^" k "=") {
        print k "=" v
        done=1
        next
      }
      { print }
      END { if (!done) print k "=" v }
    ' "$ENV_FILE" > "$tmp"
    mv "$tmp" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
    rm -f "$tmp"
  fi
  chmod 600 "$ENV_FILE"
}

prompt_secret() {
  # usage: prompt_secret VAR "prompt text"
  local __var="$1"
  local __prompt="$2"
  local __val=""
  if [[ ! -t 0 ]]; then
    printf '%s\n' "stdin is not a TTY; skipping interactive prompt for ${__var}." >&2
    printf -v "$__var" '%s' ""
    return 0
  fi
  read -r -s -p "$__prompt" __val
  echo "" >&2
  printf -v "$__var" '%s' "$__val"
}

# --- already running? ------------------------------------------------------

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(tr -d '[:space:]' < "$PID_FILE" || true)"
  if is_pid_alive "$old_pid"; then
    echo "mac-voice already running (pid $old_pid)."
    echo "Logs: $LOG_FILE"
    echo "Stop with: ./stop.sh"
    exit 0
  fi
  echo "Removing stale pid file (pid $old_pid not running)."
  rm -f "$PID_FILE"
fi

# --- load existing .env ----------------------------------------------------

if [[ ! -f "$ENV_FILE" && -f "$ROOT/.env.example" ]]; then
  cp "$ROOT/.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created .env from .env.example"
fi

load_env_file

# --- prompt for missing keys -----------------------------------------------

env_changed=0

if [[ -z "${DEEPGRAM_API_KEY:-}" ]]; then
  prompt_secret DEEPGRAM_API_KEY "Paste Deepgram key (DEEPGRAM_API_KEY) or Enter to skip: "
  if [[ -n "${DEEPGRAM_API_KEY:-}" ]]; then
    upsert_env DEEPGRAM_API_KEY "$DEEPGRAM_API_KEY"
    export DEEPGRAM_API_KEY
    env_changed=1
  else
    echo "Skipping Deepgram (local Whisper / --text still work)." >&2
  fi
else
  echo "DEEPGRAM_API_KEY: already set"
fi

want_cc=0
if [[ "${MAC_VOICE_USE_LLM:-0}" == "1" || "${MAC_VOICE_USE_JEV:-0}" == "1" ]]; then
  want_cc=1
fi

if [[ -z "${COMMAND_CODE_API_KEY:-}" && -z "${CMD_API_KEY:-}" ]]; then
  if [[ "$want_cc" -eq 1 ]]; then
    prompt_secret COMMAND_CODE_API_KEY "Paste Command Code key (needed for --use-llm / --use-jev) or Enter to skip: "
  else
    prompt_secret COMMAND_CODE_API_KEY "Paste Command Code key (COMMAND_CODE_API_KEY) for Muse/Jev, or Enter to skip: "
  fi
  if [[ -n "${COMMAND_CODE_API_KEY:-}" ]]; then
    upsert_env COMMAND_CODE_API_KEY "$COMMAND_CODE_API_KEY"
    export COMMAND_CODE_API_KEY
    env_changed=1
  else
    if [[ "$want_cc" -eq 1 ]]; then
      echo "Warning: MAC_VOICE_USE_LLM/JEV is on but COMMAND_CODE_API_KEY is missing; local router will be used." >&2
    else
      echo "Skipping Command Code (local router default; --use-llm / --use-jev need this key)." >&2
    fi
  fi
else
  echo "COMMAND_CODE_API_KEY / CMD_API_KEY: already set"
fi

if [[ "$env_changed" -eq 1 ]]; then
  echo "Updated .env (chmod 600). Secrets are not printed."
  load_env_file
fi

if [[ -n "${COMMAND_CODE_API_KEY:-}${CMD_API_KEY:-}" && -z "${MAC_VOICE_MODEL:-}" ]]; then
  upsert_env MAC_VOICE_MODEL "meta/muse-spark-1.3-contributor"
  export MAC_VOICE_MODEL="meta/muse-spark-1.3-contributor"
fi

# --- deps ------------------------------------------------------------------

if ! command -v uv >/dev/null 2>&1; then
  echo "error: uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1
fi

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "Syncing Python deps (uv sync)..."
  uv sync
else
  uv sync --quiet 2>/dev/null || uv sync
fi

# --- launch ----------------------------------------------------------------

EXTRA_FLAGS=()
if [[ "${MAC_VOICE_USE_LLM:-0}" == "1" ]]; then
  EXTRA_FLAGS+=(--use-llm)
fi
if [[ "${MAC_VOICE_USE_JEV:-0}" == "1" ]]; then
  EXTRA_FLAGS+=(--use-jev)
fi

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Hold listening requires macOS. Keys/.env are ready; on a Mac run ./start.sh again."
  echo "For routing tests here: uv run python -m mac_voice --text \"open chrome\" --dry-run"
  exit 0
fi

echo "Starting mac-voice hold mode in background..."
# Loop so the daemon keeps listening after each utterance (--hold is one-shot).
EXTRA_JOINED="${EXTRA_FLAGS[*]-}"
nohup bash -c '
  cd "'"$ROOT"'"
  set -a
  if [[ -f .env ]]; then
    # shellcheck disable=SC1091
    source <(grep -E "^[A-Za-z_][A-Za-z0-9_]*=" .env | tr -d "\r")
  fi
  set +a
  while true; do
    # shellcheck disable=SC2086
    uv run python -m mac_voice --hold '"$EXTRA_JOINED"' || true
    sleep 0.3
  done
' >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"
chmod 600 "$PID_FILE" 2>/dev/null || true

sleep 0.4
new_pid="$(tr -d '[:space:]' < "$PID_FILE")"
if is_pid_alive "$new_pid"; then
  echo "mac-voice started (pid $new_pid)."
  echo "Log: $LOG_FILE"
  echo "Stop with: ./stop.sh"
else
  echo "error: process exited immediately; check $LOG_FILE" >&2
  rm -f "$PID_FILE"
  exit 1
fi
