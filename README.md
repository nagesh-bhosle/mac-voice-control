# Mac Voice Control

Hands-free Mac control by voice. Jev typed action routing plus local
Whisper STT plus AppleScript and Accessibility execution. Speak to open
apps, drive browser tabs, and dictate code into IntelliJ or VS Code.

The brain only ever selects from a closed action set
(`src/mac_voice/brain/candidates.py`). Model output is never executed as
shell.

## Requirements

- macOS (Apple Silicon preferred) for live mic and live execution.
  Linux supports routing tests and `--dry-run` only.
- Python 3.12 or newer, [uv](https://docs.astral.sh/uv/).
- Optional: `TYPESAFE_API_KEY` from https://console.typesafe.ai for Jev
  API routing. Without it, the built-in local router is used.

## Setup

```sh
cp .env.example .env   # add TYPESAFE_API_KEY (optional)
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
| `TYPESAFE_API_KEY` | Optional. Enables `--use-jev` API routing. Local router is the default. |
| `MUSE_API_KEY` | Optional. Code dictation normalization only, never action choice. |
| `OPENAI_API_KEY` | Optional, reserved. |
| `MAC_VOICE_WAKE_WORD` | Wake word, default `Alfred`. |
| `MAC_VOICE_DRY_RUN` | Set to `1` to force dry-run. |
| `MAC_VOICE_MODE` | Reserved, default `dry`. |

Secrets live in `.env` only and are never logged.

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

Useful flags:

```sh
mac-voice --text "..." --dry-run        # route only, safe anywhere
mac-voice --text "..." --dry-run --json # machine readable plan
mac-voice --text "..."                  # execute on macOS
mac-voice --text "..." --yes            # also allow destructive actions
mac-voice --text "..." --use-jev        # route via TypeSafe Jev API
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
  caret. With `MUSE_API_KEY` set, spoken code is normalized to exact
  typed text, but the action choice itself never comes from the model.
- Snippets: "insert snippet main" types the closed template from
  `candidates.py`.

See `src/mac_voice/exec/editor.py` for the key maps.

## Safety: closed actions

- The router output is validated against the closed action enum in
  `brain/candidates.py`. Unknown actions raise `ValueError` in the
  dispatcher and are never executed.
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
| `TYPESAFE_API_KEY is not set; falling back` | Set it in `.env` or drop `--use-jev` to use the local router. |
| `Unknown app` / `Unknown editor command` | The name is outside the closed set. Check `candidates.py` for supported names. |
| Whisper missing | Re-run `./scripts/setup.sh` for the brew and pip hints. |

## Development

```sh
uv sync --extra dev
uv run pytest -q
```

Tests cover routing and slot extraction only, so they pass on Linux
without mic or AX hardware.

## License

MIT
