# Mac Voice Control

Hands-free Mac control by voice. Jev typed action routing plus Deepgram
(or local Whisper) STT plus AppleScript and Accessibility execution.
Optional Command Code LLM (Muse / DeepSeek / free models) for routing and
code dictation. Speak to open apps, drive browser tabs, and dictate code
into IntelliJ or VS Code.

The brain only ever selects from a closed action set
(`src/mac_voice/brain/candidates.py`). Model output is never executed as
shell.

## Requirements

- macOS (Apple Silicon preferred) for live mic and live execution.
  Linux supports routing tests and `--dry-run` only.
- Python 3.12 or newer, [uv](https://docs.astral.sh/uv/).
- Optional keys (see Environment below):
  - `DEEPGRAM_API_KEY` for cloud STT
  - `COMMAND_CODE_API_KEY` (or `CMD_API_KEY`) for Muse / DeepSeek / free models
  - `TYPESAFE_API_KEY` for TypeSafe Jev API routing

## Setup

```sh
cp .env.example .env   # add DEEPGRAM_API_KEY and COMMAND_CODE_API_KEY
./scripts/setup.sh
```

`scripts/setup.sh` installs Homebrew packages (ffmpeg, whisper-cpp),
syncs Python deps with `uv sync --extra dev`, bootstraps `.env`, and
prints the permission steps below.

## Permissions (macOS)

Grant all three to the terminal app you launch `mac-voice` from
(Terminal.app, iTerm2, or VS Code):

1. **Microphone**: System Settings > Privacy and Security > Microphone.
2. **Accessibility**: System Settings > Privacy and Security > Accessibility.
3. **Input Monitoring**: System Settings > Privacy and Security > Input Monitoring.

Restart the terminal after granting these, or keystrokes and listening
will silently fail.

Optional Caps Lock hold-to-talk remap: System Settings > Keyboard >
Keyboard Shortcuts > Modifier Keys, or see the `hidutil` hint printed by
`scripts/setup.sh`. Revert with `scripts/uninstall-capslock.sh`.

## Environment

| Variable | Purpose |
|----------|---------|
| `DEEPGRAM_API_KEY` | Preferred STT when set (`MAC_VOICE_STT=auto`). |
| `COMMAND_CODE_API_KEY` / `CMD_API_KEY` | Command Code Provider API for `--use-llm` and code dictation normalize. |
| `MAC_VOICE_MODEL` | LLM model id. Default `meta/muse-spark-1.3-contributor`. |
| `MAC_VOICE_STT` | `auto` (default), `deepgram`, or `whisper`. |
| `MAC_VOICE_USE_LLM` | Set to `1` to enable LLM routing by default. |
| `TYPESAFE_API_KEY` | Optional. Enables `--use-jev` API routing. Local router is the default. |
| `MUSE_API_KEY` | Optional legacy Anthropic key for dictation only (Command Code preferred). |
| `OPENAI_API_KEY` | Optional, reserved. |
| `MAC_VOICE_WAKE_WORD` | Wake word, default `Alfred`. |
| `MAC_VOICE_DRY_RUN` | Set to `1` to force dry-run. |
| `MAC_VOICE_MODE` | Reserved, default `dry`. |

### Model examples (`MAC_VOICE_MODEL`)

| Model | Notes |
|-------|-------|
| `meta/muse-spark-1.3-contributor` | Default (Muse Spark 1.3 Contributor) |
| `deepseek/deepseek-v4-flash` | DeepSeek via Command Code |
| `poolside/laguna-s-2.1-free` | Free model |
| `inclusionai/ling-3.1-flash:free` | Free model |

Endpoint used: `https://api.commandcode.ai/provider/v1/chat/completions`
with `Authorization: Bearer $COMMAND_CODE_API_KEY`.

Secrets live in `.env` only and are never logged or committed.

## Usage

Dry-run routes the utterance and prints the plan without touching AX:

```sh
uv run python -m mac_voice --text "open chrome" --dry-run
uv run python -m mac_voice --text "open chrome and open facebook in a tab" --dry-run
uv run python -m mac_voice --text "go to vs code" --dry-run
uv run python -m mac_voice --text "open rancher" --dry-run
uv run python -m mac_voice --text "undo" --dry-run
uv run python -m mac_voice --text "in intellij type public static void main" --dry-run
```

LLM routing (Command Code) and Deepgram STT:

```sh
# Route with Muse (or another MAC_VOICE_MODEL) — still closed-catalog only
uv run python -m mac_voice --text "open rancher" --use-llm --dry-run
uv run python -m mac_voice --text "open chrome" --use-llm --model deepseek/deepseek-v4-flash --dry-run

# Transcribe an audio file with Deepgram (when DEEPGRAM_API_KEY is set)
uv run python -m mac_voice --audio ./clip.wav --stt deepgram --dry-run
uv run python -m mac_voice --audio ./clip.wav --use-llm --dry-run
```

Useful flags:

```sh
mac-voice --text "..." --dry-run        # route only, safe anywhere
mac-voice --text "..." --dry-run --json # machine readable plan
mac-voice --text "..."                  # execute on macOS
mac-voice --text "..." --yes            # also allow destructive actions
mac-voice --text "..." --use-jev        # route via TypeSafe Jev API
mac-voice --text "..." --use-llm        # route via Command Code LLM
mac-voice --model <id>                  # override MAC_VOICE_MODEL
mac-voice --stt auto|deepgram|whisper   # STT provider
mac-voice --audio PATH                  # transcribe file then route
mac-voice --hold | --ptt | --wake       # listening modes, macOS only
```

On Linux, `--hold`, `--ptt`, and `--wake` print
`listening not available on this OS` and exit 0. Live execution without
`--dry-run` on Linux prints an error asking for `--dry-run`.

## Examples

| Say | Result |
|-----|--------|
| "open chrome" | open_app chrome |
| "open rancher" | open_app rancher |
| "go to vs code" | focus_editor vscode |
| "open chrome and open facebook in a tab" | open_app chrome, then open_url facebook in a new tab |
| "undo" / "save" / "new line" | editor_command |
| "in intellij type public static void main" | focus_editor intellij, then dictate the code |
| "quit slack" | quit_app, needs confirm |
| "search for typesafe jev" | search_web on Google |
| "volume up" / "mute" | system volume |
| "take a screenshot" | screenshot to Desktop |

More utterances: [docs/examples.md](./docs/examples.md).

## Voice coding

Focus stays in the IDE. Editor commands send fixed key sequences per
app (IntelliJ overrides where shortcuts differ):

- Navigation and edits: "undo", "redo", "save", "new line",
  "delete line", "select word", "select line", "go to line 42",
  "format code", "comment line", "find", "replace", "run", "debug".
- Dictation: "in intellij type ..." or "type ..." types text at the
  caret. With `COMMAND_CODE_API_KEY` (preferred) or `MUSE_API_KEY`,
  spoken code is normalized to exact typed text via the configured
  model, but the action choice itself never comes from free-form shell.
- Snippets: "insert snippet main" types the closed template from
  `candidates.py`.

See `src/mac_voice/exec/editor.py` for the key maps.

## Safety: closed actions

- The router output is validated against the closed action enum in
  `brain/candidates.py`. Unknown actions raise `ValueError` in the
  dispatcher and are never executed.
- LLM routing (`--use-llm`) must return JSON actions from that same
  catalog; invalid or shell-like proposals are dropped and the local
  heuristic is used instead.
- No arbitrary shell comes from routing. The only shell path is the
  fixed `screencapture` command for the screenshot action.
- Destructive actions (`quit_app`, `close_window`, `close_tab`) are
  flagged with `confirm`. Live runs skip them unless you pass `--yes`.
  Dry-run always shows them with a `[confirm]` marker.
- `--dry-run` never calls AppleScript, Accessibility, or the mic.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `listening not available on this OS` | Expected on Linux. Use `--text ... --dry-run`, or run on a Mac. |
| Live run on Linux errors asking for `--dry-run` | Same: execution needs Darwin. Add `--dry-run`. |
| Nothing happens on macOS live run | Check Accessibility and Input Monitoring grants, then restart the terminal. |
| Mic never hears anything | Check Microphone grant for the terminal app. |
| `COMMAND_CODE_API_KEY is not set; falling back` | Set it (or `CMD_API_KEY`) in `.env`, or drop `--use-llm`. |
| `TYPESAFE_API_KEY is not set; falling back` | Set it in `.env` or drop `--use-jev` to use the local router. |
| `DEEPGRAM_API_KEY is not set` | Add it to `.env`, or use `--stt whisper` / `--text`. |
| `Unknown app` / `Unknown editor command` | The name is outside the closed set. Check `candidates.py` for supported names. |
| Whisper missing | Re-run `./scripts/setup.sh` for the brew and pip hints. |

## Development

```sh
uv sync --extra dev
uv run pytest -q
```

Tests cover routing, slot extraction, Command Code / Deepgram clients
(mocked HTTP), and LLM JSON validation. They pass on Linux without mic
or AX hardware.

## License

MIT
