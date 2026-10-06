# Mac Voice Control

Voice-control your Mac with **Jev** (typed action routing) + local Whisper STT. Open apps, drive Chrome tabs, and dictate into IntelliJ / VS Code without typing.

> Status: plan landed — implementation via Command Code (`meta/muse-spark-1.3-contributor`) in progress. See [PLAN.md](./PLAN.md).

## Quick start (macOS, Apple Silicon)

```sh
cp .env.example .env   # add TYPESAFE_API_KEY from https://console.typesafe.ai
./scripts/setup.sh
```

Grant **Microphone**, **Accessibility**, and **Input Monitoring** to the terminal app you launch from.

```sh
mac-voice --hold
# or: python -m mac_voice --text "open chrome" --dry-run
```

Full usage will be filled in as the Muse implementation lands. Until then, the authoritative design is in `PLAN.md`.

## License

MIT
