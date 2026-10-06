# Mac Voice Control — Implementation Plan

**Owner:** Nagesh Bhosle  
**Stack:** Jev (`typesafe/jev`) for typed action routing + local Whisper STT + macOS Accessibility/AppleScript for execution. Coding dictation path uses Muse Spark 1.3 Contributor (via Command Code / optional LLM fallback) to turn spoken code into typed text.  
**Implementer:** Command Code with `meta/muse-spark-1.3-contributor`  
**Target OS:** macOS (Apple Silicon preferred). Linux CI can unit-test routing only.

---

## Goal

Hands-free Mac control by voice:

1. **Desktop control** — “open Rancher”, “go to VS Code”, “open Chrome and open Facebook in a tab”
2. **Voice coding** — stop typing in IntelliJ / VS Code; speak code, navigation, edits (“new line”, “select previous word”, “undo”, “type: public class Foo”)

Jev never invents free-form shell. It **selects** from a closed action set + typed argument candidates. App code executes. Optional Muse/LLM path only for **dictation text** (what to type), not for choosing dangerous system actions.

---

## Architecture

```
mic → VAD → whisper.cpp (local STT)
        → Brain (build Jev Choice questions + candidates)
        → typesafe/jev (one fan-out: action + args)
        → Executor (AppleScript / Accessibility / AX)
        → optional `say` feedback

Coding mode:
  action=dictate | editor_command
  dictate text: local SlotExtractor spans OR Muse when utterance is free-form code
```

### Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| Hands-free | Wake word “Alfred” (configurable) or Caps Lock tap | Listen → route → run |
| Hold | Hold Caps Lock / F18 | Talk while held, release to run |
| PTT | Enter start/stop in terminal | Explicit push-to-talk |
| Dry-run | `--text "…" --dry-run` | Route only, no AX |

### Safety

- Closed action enum only (no arbitrary shell from Jev).
- Destructive actions (`quit`, `close window`, `send`, `delete`) require confirm gate via Jev `destructive?` + Yes/No utterance or popover.
- `--dry-run` for testing.
- Secrets never logged; API keys in `.env` only.

---

## MVP action set (v0.1)

### Apps & windows
- `open_app` — candidate apps from `/Applications` + common CLI apps
- `activate_app` / `switch_to`
- `quit_app` (confirm)
- `new_window`, `close_window` (confirm), `minimize`, `fullscreen`

### Browser (Chrome / Safari / Arc if present)
- `open_url` — known sites map (`facebook`, `github`, `gmail`, …) + raw URL if spoken
- `new_tab`, `close_tab`, `next_tab`, `prev_tab`
- `search_web` — engine choice + query span

### Editor / coding (IntelliJ, VS Code, Cursor, JetBrains)
- `focus_editor` — activate named IDE
- `dictate` — type transcribed / Muse-normalized text at caret
- `editor_command` — mapped shortcuts: new line, delete line, undo, redo, select word/line, go to line, save, format, comment, find, replace, run, debug
- `code_snippet` — small templates (class, function, if/else) via candidates, not free LLM codegen in v0.1

### System
- `volume_up` / `volume_down` / `mute`
- `screenshot`
- `say` (speak back last action)

Out of scope for v0.1: full agentic browsing, multi-step sagas, mouse click-by-vision, Windows/Linux desktop.

---

## File tree

```
mac-voice-control/
├── PLAN.md                 # this file
├── README.md               # how to install, permissions, examples
├── LICENSE                 # MIT
├── .env.example            # TYPESAFE_API_KEY, optional OPENAI/MUSE keys
├── pyproject.toml          # Python 3.12+, uv
├── scripts/
│   ├── setup.sh            # whisper, ffmpeg, caps lock→F18, permissions hints
│   └── uninstall-capslock.sh
├── src/mac_voice/
│   ├── __init__.py
│   ├── __main__.py         # CLI entry: mac-voice / python -m mac_voice
│   ├── config.py
│   ├── stt/
│   │   ├── whisper_engine.py
│   │   └── vad.py
│   ├── brain/
│   │   ├── candidates.py   # apps, sites, editor cmds
│   │   ├── slots.py        # SlotExtractor for text spans
│   │   └── jev_router.py   # build questions → call typesafe/jev
│   ├── exec/
│   │   ├── applescript.py
│   │   ├── accessibility.py
│   │   ├── browser.py
│   │   ├── editor.py       # IntelliJ + VS Code key maps
│   │   └── apps.py
│   ├── dictate/
│   │   └── muse_normalize.py  # optional Muse path for code dictation
│   └── ui/
│       └── feedback.py     # say + terminal status
├── tests/
│   ├── test_router_dry.py  # --text fixtures → expected action
│   ├── test_slots.py
│   └── fixtures/utterances.json
└── docs/
    └── examples.md
```

---

## Implementation steps (Command Code / Muse)

1. Scaffold package (`pyproject.toml`, CLI, config, `.env.example`).
2. Implement candidate catalogs (apps, sites, editor commands) + SlotExtractor.
3. Implement `jev_router.py` against TypeSafe Jev API (or `cmd -p … -m typesafe/jev` pattern for headless tests).
4. Implement AppleScript/AX executors for open app, browser tab/URL, basic editor keys.
5. Wire STT + VAD + hold/PTT modes (macOS-only modules; mock on Linux).
6. Add dictate path: default type transcript; optional Muse normalize for punctuation/code.
7. Dry-run CLI + fixture tests for utterances:
   - “open rancher”
   - “go to vs code”
   - “open chrome open facebook in a tab”
   - “in intellij type public static void main”
   - “undo” / “save” / “new line”
8. Write README with permissions, setup, examples, troubleshooting.
9. Push to GitHub; tag `v0.1.0-plan` after plan-only commit, then `v0.1.0` after impl.

---

## Acceptance criteria

- [ ] `python -m mac_voice --text "open chrome" --dry-run` prints `open_app(chrome)` (or equivalent)
- [ ] `--text "open chrome and open facebook in a tab" --dry-run` yields compound plan: open/activate Chrome → new_tab/open_url facebook
- [ ] Editor dry-run maps “undo”, “save”, “go to vs code”
- [ ] README documents Mic / Accessibility / Input Monitoring + `TYPESAFE_API_KEY`
- [ ] No arbitrary shell execution from model output
- [ ] Tests pass on Linux for routing/slots (skip live AX)

---

## API keys

| Key | Purpose |
|-----|---------|
| `TYPESAFE_API_KEY` | Required — Jev routing |
| Optional Muse / OpenAI | Code dictation normalization only |

Never commit real keys. Use `.env`.

---

## Risks

| Risk | Mitigation |
|------|------------|
| AX permissions blocked | Clear README + launch-time checks |
| Whisper latency | Small base model + Metal; hold mode |
| Compound utterances | Jev `compound?` + ordered action list |
| IDE shortcut variance | Per-app key maps; user config override |
| Cannot test AX on Linux CI | Dry-run + fixtures; Mac manual smoke |

---

## Success demo script (manual on Mac)

1. `./scripts/setup.sh` && grant permissions  
2. `mac-voice --hold`  
3. Say: “open Rancher” → Rancher launches  
4. Say: “go to VS Code” → VS Code frontmost  
5. Say: “open Chrome open Facebook in a tab” → Chrome tab to Facebook  
6. In IntelliJ: “new line” then dictate a short method → text appears at caret
