"""CLI entry point for mac-voice-control.

Console script ``mac-voice`` maps here (see pyproject project.scripts).
Routing always goes through mac_voice.brain.jev_router, which only ever
emits actions from the closed catalog in brain/candidates.py.
"""

from __future__ import annotations

import json
import platform
import sys

import click

from mac_voice.brain.jev_router import route_utterance
from mac_voice.config import DEFAULT_LLM_MODEL, load_settings
from mac_voice.exec import dispatcher
from mac_voice.stt import resolve_stt_provider, transcribe_audio
from mac_voice.ui import feedback


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--text", default="", help='Utterance to route, e.g. --text "open chrome".')
@click.option("--dry-run", is_flag=True, default=False, help="Print the ActionPlan without touching AX or AppleScript.")
@click.option("--hold", is_flag=True, default=False, help="Hold-to-talk listening mode (macOS only).")
@click.option("--ptt", is_flag=True, default=False, help="Push-to-talk listening mode (macOS only).")
@click.option("--wake", is_flag=True, default=False, help="Wake-word listening mode (macOS only).")
@click.option("--json", "as_json", is_flag=True, default=False, help="Print the plan (dry-run) or results as JSON.")
@click.option("--use-jev", is_flag=True, default=False, help="Route via the TypeSafe Jev API (needs TYPESAFE_API_KEY).")
@click.option("--use-llm", is_flag=True, default=False, help="Route via Command Code LLM (needs COMMAND_CODE_API_KEY).")
@click.option(
    "--model",
    default="",
    help=f"Command Code model id (default: {DEFAULT_LLM_MODEL} or MAC_VOICE_MODEL).",
)
@click.option(
    "--stt",
    "stt_choice",
    type=click.Choice(["auto", "deepgram", "whisper"], case_sensitive=False),
    default=None,
    help="Speech-to-text provider (default: MAC_VOICE_STT or auto).",
)
@click.option("--audio", "audio_path", default="", help="Transcribe this audio file instead of --text / mic.")
@click.option("--yes", is_flag=True, default=False, help="Allow destructive actions (quit_app, close_window, close_tab).")
def main(text, dry_run, hold, ptt, wake, as_json, use_jev, use_llm, model, stt_choice, audio_path, yes):
    """Route a voice utterance to a typed action plan and execute it."""
    if hold or ptt or wake:
        if platform.system() != "Darwin":
            print("listening not available on this OS")
            return

    settings = load_settings()
    dry_run = dry_run or settings.dry_run
    if stt_choice:
        settings.stt_provider = stt_choice.lower()
    if model:
        settings.llm_model = model.strip()
    use_llm = use_llm or settings.llm_enabled

    utterance = (text or "").strip()
    if audio_path:
        utterance = transcribe_audio(audio_path, settings)
        feedback.status(f"STT ({resolve_stt_provider(settings)}): {utterance!r}")
    elif not utterance and (hold or ptt or wake):
        mode = "hold" if hold else ("ptt" if ptt else "wake")
        utterance = _listen_once(mode, settings)
    if not utterance:
        raise click.UsageError(
            'nothing to route: pass --text "utterance", --audio PATH, or use a listening mode on macOS'
        )

    if use_llm and not settings.command_code_api_key:
        print("COMMAND_CODE_API_KEY is not set; falling back to the local router.")
    if use_jev and not settings.typesafe_api_key:
        print("TYPESAFE_API_KEY is not set; falling back to the local router.")

    plan = route_utterance(utterance, settings, use_jev=use_jev, use_llm=use_llm)

    if dry_run:
        if as_json:
            print(plan.model_dump_json(indent=2))
        else:
            print(feedback.plan_human(plan))
        return

    if platform.system() != "Darwin":
        print(
            "error: live execution needs macOS (Darwin); re-run with --dry-run to route only.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    actions = list(plan.actions)
    if plan.needs_confirm and not yes:
        skipped = [a for a in actions if a.confirm]
        actions = [a for a in actions if not a.confirm]
        for action in skipped:
            print(f"skipped destructive action {action.action} {action.args} (re-run with --yes to allow)")
    if not actions:
        print("nothing to execute")
        return

    results = dispatcher.dispatch_many(
        actions,
        dry_run=False,
        muse_api_key=settings.muse_api_key,
        command_code_api_key=settings.command_code_api_key,
        llm_model=settings.llm_model,
    )
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        for res in results:
            if res["ok"]:
                print(f"ok: {res['action']} {res.get('result', '')}")
            else:
                print(f"failed: {res['action']}: {res['error']}")


def _listen_once(mode: str, settings) -> str:
    provider = resolve_stt_provider(settings)
    feedback.status(f"{mode} mode: STT provider={provider}.")
    if provider == "deepgram":
        feedback.status("Deepgram key detected; live mic capture still MVP-stubbed.")
        feedback.status("Pass --audio PATH to transcribe a file with Deepgram, or type below.")
    else:
        feedback.status("live mic capture is not wired in this MVP; type the utterance.")
    feedback.status('Type the utterance and press Enter (empty line aborts), or use --text / --audio.')
    try:
        return input("> ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""


if __name__ == "__main__":
    main()
