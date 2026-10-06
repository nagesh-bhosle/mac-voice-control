"""Jev router: local heuristic routing (always offline) plus optional Command Code
Jev (typesafe/jev via Provider API systemone) and optional Command Code LLM
routing constrained to the closed action catalog.

The local router is the primary path for --dry-run and tests. When --use-jev
is passed and COMMAND_CODE_API_KEY (or CMD_API_KEY) is set, the router calls
Command Code Jev at /provider/v1/systemone with model typesafe/jev. When
--use-llm (or MAC_VOICE_USE_LLM) and a Command Code key are set, the router
asks a chat model for a JSON ActionPlan, validates it against
brain/candidates.py, and falls back to the local heuristic on failure.

TYPESAFE_API_KEY is legacy/optional and is not required for --use-jev.

The closed action set in brain/candidates.py is the only source of
actions. Model output is never executed as shell.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field

from mac_voice.brain import candidates as C
from mac_voice.brain.slots import SlotExtractor
from mac_voice.config import JEV_MODEL, Settings

_slots = SlotExtractor()

_OPEN_RE = re.compile(r"\b(open|launch|start|go to|goto|switch to|focus|show)\b", re.IGNORECASE)
_QUIT_RE = re.compile(r"\b(quit|exit|close)\b", re.IGNORECASE)
_SEARCH_RE = re.compile(r"\b(?:search(?:\s+for|\s+the\s+web\s+for)?|google|look up|look\s+up)\s+(?P<q>.+)$", re.IGNORECASE)
_SAY_RE = re.compile(r"^\s*say\s+(?P<text>.+)$", re.IGNORECASE)
_SNIPPET_RE = re.compile(r"\b(?:snippet|template|insert)\s+(?P<name>class|function|if else|if|for|main)\b", re.IGNORECASE)
_GO_TO_LINE_RE = re.compile(r"go to line\s+(?P<n>\d+)", re.IGNORECASE)
_VOLUME_UP_RE = re.compile(r"\b(volume up|turn (?:it|the volume) up|louder|increase volume)\b", re.IGNORECASE)
_VOLUME_DOWN_RE = re.compile(r"\b(volume down|turn (?:it|the volume) down|quieter|decrease volume)\b", re.IGNORECASE)
_MUTE_RE = re.compile(r"\b(mute|unmute|silence)\b", re.IGNORECASE)
_SCREENSHOT_RE = re.compile(r"\b(screenshot|screen ?shot|take a picture of the screen|capture (?:the )?screen)\b", re.IGNORECASE)


class Action(BaseModel):
    action: str
    args: dict[str, Any] = Field(default_factory=dict)
    confirm: bool = False
    text: str = ""


class ActionPlan(BaseModel):
    utterance: str
    actions: list[Action] = Field(default_factory=list)
    via: str = "local"
    needs_confirm: bool = False

    def model_post_init(self, __context: Any) -> None:
        self.needs_confirm = any(a.confirm for a in self.actions)


def _confirm_for(action: str) -> bool:
    return action in C.DESTRUCTIVE_ACTIONS


def _route_single(part: str) -> list[Action]:
    raw = part.strip()
    text = _slots.normalize(raw)
    if not text:
        return []

    app_dictate = _slots.match_app_dictate(raw)
    if app_dictate:
        app, body = app_dictate
        return [
            Action(action="focus_editor", args={"app": app}, text=f"focus {app}"),
            Action(action="dictate", args={"text": body}, text=body),
        ]

    dictate_text = _slots.extract_dictate_text(raw)
    if dictate_text:
        app = _slots.extract_app(text)
        if app and C.APPS[app].get("editor"):
            return [
                Action(action="focus_editor", args={"app": app}, text=f"focus {app}"),
                Action(action="dictate", args={"text": dictate_text}, text=dictate_text),
            ]
        in_match = re.match(r"^(?:in|inside|using)\s+.+$", text)
        if in_match and app:
            return [
                Action(action="focus_editor", args={"app": app}, text=f"focus {app}"),
                Action(action="dictate", args={"text": dictate_text}, text=dictate_text),
            ]
        return [Action(action="dictate", args={"text": dictate_text}, text=dictate_text)]

    m = _SAY_RE.match(raw.strip())
    if m:
        return [Action(action="say", args={"text": m.group("text").strip()}, text=m.group("text").strip())]

    for ident, info in C.EDITOR_COMMANDS.items():
        for phrase in info["phrases"]:
            if re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", text):
                args: dict[str, Any] = {"command": ident}
                line_m = _GO_TO_LINE_RE.search(text)
                if ident == "go_to_line" and line_m:
                    args["line"] = int(line_m.group("n"))
                return [Action(action="editor_command", args=args, text=raw.strip())]

    app = _slots.extract_app(text)
    site = _slots.extract_site(text)
    url = _slots.extract_url(raw)

    if re.search(r"\bclose tab\b", text):
        return [Action(action="close_tab", args={}, confirm=True, text=raw.strip())]
    if re.search(r"\bclose window\b", text):
        return [Action(action="close_window", args={}, confirm=True, text=raw.strip())]
    if _QUIT_RE.search(text) and app:
        return [Action(action="quit_app", args={"app": app}, confirm=True, text=raw.strip())]
    if re.search(r"\bclose\b", text) and app and not _OPEN_RE.search(text):
        return [Action(action="quit_app", args={"app": app}, confirm=True, text=raw.strip())]

    if url or (site and re.search(r"\b(open|tab|visit|navigate|goto|go to|launch)\b", text)):
        site_id = site or "url"
        resolved = C.SITES[site_id]["url"] if site else url or ""
        if url and not site:
            resolved = url if url.startswith("http") else f"https://{url}"
        args = {"site": site_id, "url": resolved}
        if re.search(r"\btab\b", text):
            args["new_tab"] = True
        return [Action(action="open_url", args=args, text=raw.strip())]

    search_m = _SEARCH_RE.search(raw.strip())
    if search_m and search_m.group("q").strip():
        return [Action(action="search_web", args={"query": search_m.group("q").strip()}, text=raw.strip())]

    if re.search(r"\bnew tab\b", text):
        return [Action(action="new_tab", args={}, text=raw.strip())]
    if re.search(r"\bnext tab\b", text):
        return [Action(action="next_tab", args={}, text=raw.strip())]
    if re.search(r"\b(previous|prev) tab\b", text):
        return [Action(action="prev_tab", args={}, text=raw.strip())]
    if re.search(r"\bnew window\b", text):
        args = {"app": app} if app else {}
        return [Action(action="new_window", args=args, text=raw.strip())]
    if re.search(r"\bminimi[sz]e\b", text):
        return [Action(action="minimize", args={}, text=raw.strip())]
    if re.search(r"\bfull ?screen\b", text):
        return [Action(action="fullscreen", args={}, text=raw.strip())]

    if _VOLUME_UP_RE.search(text):
        return [Action(action="volume_up", args={}, text=raw.strip())]
    if _VOLUME_DOWN_RE.search(text):
        return [Action(action="volume_down", args={}, text=raw.strip())]
    if _MUTE_RE.search(text):
        return [Action(action="mute", args={}, text=raw.strip())]
    if _SCREENSHOT_RE.search(text):
        return [Action(action="screenshot", args={}, text=raw.strip())]

    snippet_m = _SNIPPET_RE.search(text)
    if snippet_m:
        name = snippet_m.group("name").replace(" ", "_")
        if name == "if_else":
            name = "if_else"
        template = C.SNIPPETS.get(name, "")
        return [Action(action="code_snippet", args={"name": name, "template": template}, text=raw.strip())]

    if _OPEN_RE.search(text) or re.search(r"\b(tab|window|browser|website|site|page)\b", text):
        if app and site:
            if text.find(app.replace("_", " ")) < 0:
                pass
            app_pos = _app_position(text, app)
            site_pos = _site_position(text, site)
            if site_pos is not None and (app_pos is None or site_pos > app_pos):
                pass
            return [
                Action(action="open_app", args={"app": app}, text=raw.strip()),
                Action(
                    action="open_url",
                    args={"site": site, "url": C.SITES[site]["url"], "new_tab": True},
                    text=raw.strip(),
                ),
            ]
        if app:
            if C.APPS[app].get("editor") and re.search(r"\bgo to\b", text):
                return [Action(action="focus_editor", args={"app": app}, text=raw.strip())]
            verb_open = re.search(r"\b(open|launch|start)\b", text)
            verb_go = re.search(r"\b(go to|goto|switch to|focus)\b", text)
            if verb_go and not verb_open:
                if C.APPS[app].get("editor"):
                    return [Action(action="focus_editor", args={"app": app}, text=raw.strip())]
                return [Action(action="activate_app", args={"app": app}, text=raw.strip())]
            return [Action(action="open_app", args={"app": app}, text=raw.strip())]
        if site:
            return [Action(action="open_url", args={"site": site, "url": C.SITES[site]["url"]}, text=raw.strip())]
        if url:
            resolved = url if url.startswith("http") else f"https://{url}"
            return [Action(action="open_url", args={"site": "url", "url": resolved}, text=raw.strip())]

    if app and C.APPS[app].get("editor"):
        return [Action(action="focus_editor", args={"app": app}, text=raw.strip())]
    if app:
        return [Action(action="open_app", args={"app": app}, text=raw.strip())]
    if site:
        return [Action(action="open_url", args={"site": site, "url": C.SITES[site]["url"]}, text=raw.strip())]

    return [Action(action="dictate", args={"text": raw.strip()}, text=raw.strip())]


def _app_position(text: str, app: str) -> int | None:
    best: int | None = None
    for name in C.APPS[app]["names"]:
        pos = text.find(name)
        if pos >= 0 and (best is None or pos < best):
            best = pos
    return best


def _site_position(text: str, site: str) -> int | None:
    best: int | None = None
    for name in C.SITES[site]["names"]:
        pos = text.find(name)
        if pos >= 0 and (best is None or pos < best):
            best = pos
    return best


def route_local(utterance: str) -> ActionPlan:
    parts = _slots.split_compound(utterance)
    actions: list[Action] = []
    for part in parts:
        actions.extend(_route_single(part))
    if not actions:
        actions = [Action(action="dictate", args={"text": utterance.strip()}, text=utterance.strip())]
    return ActionPlan(utterance=utterance, actions=actions, via="local")


_ACTION_LABELS: dict[str, str] = {
    "open_app": "Open or launch an application",
    "activate_app": "Bring an already-running app to the front",
    "quit_app": "Quit an application",
    "new_window": "Open a new window",
    "close_window": "Close the front window",
    "minimize": "Minimize the front window",
    "fullscreen": "Toggle fullscreen",
    "open_url": "Open a website or URL in the browser",
    "new_tab": "Open a new browser tab",
    "close_tab": "Close the current browser tab",
    "next_tab": "Switch to the next browser tab",
    "prev_tab": "Switch to the previous browser tab",
    "search_web": "Search the web for a query",
    "focus_editor": "Focus an IDE / code editor",
    "dictate": "Type spoken text at the caret",
    "editor_command": "Run an IDE shortcut (undo, save, etc.)",
    "code_snippet": "Insert a closed code snippet template",
    "volume_up": "Increase system volume",
    "volume_down": "Decrease system volume",
    "mute": "Mute or unmute",
    "screenshot": "Capture the screen",
    "say": "Speak text aloud with macOS say",
}


def build_choice_questions(utterance: str) -> list[dict[str, Any]]:
    """Legacy list shape kept for tests/docs; prefer build_jev_questions."""
    parts = _slots.split_compound(utterance)
    questions: list[dict[str, Any]] = []
    for part in parts:
        questions.append(
            {
                "question": f"What action does this voice command request? Command: {part!r}",
                "candidates": [{"id": a, "label": a} for a in C.ACTIONS],
            }
        )
        app = _slots.extract_app(part)
        if app or re.search(r"\b(open|go to|launch|focus|switch|quit)\b", part, re.IGNORECASE):
            questions.append(
                {
                    "question": f"Which app is named in this command? Command: {part!r}",
                    "candidates": [{"id": k, "label": v["process"]} for k, v in C.APPS.items()],
                }
            )
        site = _slots.extract_site(part)
        if site or re.search(r"\b(tab|url|website|site|facebook|github|gmail|youtube|google|twitter|linkedin)\b", part, re.IGNORECASE):
            questions.append(
                {
                    "question": f"Which site is named in this command? Command: {part!r}",
                    "candidates": [{"id": k, "label": v["url"]} for k, v in C.SITES.items()],
                }
            )
    return questions


def build_jev_questions(utterance: str) -> tuple[list[str], dict[str, Any]]:
    """Build Command Code systemone questions for typesafe/jev.

    Returns (parts, questions) where questions maps name -> {type, instructions, criteria}.
    """
    parts = _slots.split_compound(utterance) or [utterance.strip() or utterance]
    questions: dict[str, Any] = {}
    for i, part in enumerate(parts):
        questions[f"action_{i}"] = {
            "type": "choice",
            "instructions": (
                "Which closed Mac voice-control action best matches this command part? "
                f"Command: {part!r}"
            ),
            "criteria": {a: _ACTION_LABELS.get(a, a) for a in C.ACTIONS},
        }
        questions[f"app_{i}"] = {
            "type": "choice",
            "instructions": (
                "Which application is named in this command part? "
                f"Choose none if no app is named. Command: {part!r}"
            ),
            "criteria": {
                **{k: v["process"] for k, v in C.APPS.items()},
                "none": "No application is named",
            },
        }
        questions[f"site_{i}"] = {
            "type": "choice",
            "instructions": (
                "Which website is named in this command part? "
                f"Choose none if no site is named. Command: {part!r}"
            ),
            "criteria": {
                **{k: v["url"] for k, v in C.SITES.items()},
                "none": "No website is named",
            },
        }
        if re.search(
            r"\b(undo|redo|save|new line|delete line|select word|select line|"
            r"go to line|format|comment|find|replace|run|debug|copy|paste|cut)\b",
            part,
            re.IGNORECASE,
        ):
            questions[f"editor_{i}"] = {
                "type": "choice",
                "instructions": (
                    "Which editor shortcut command is requested? "
                    f"Choose none if none. Command: {part!r}"
                ),
                "criteria": {
                    **{k: " / ".join(v["phrases"]) for k, v in C.EDITOR_COMMANDS.items()},
                    "none": "No editor command",
                },
            }
        if re.search(r"\b(snippet|template|insert)\b", part, re.IGNORECASE):
            questions[f"snippet_{i}"] = {
                "type": "choice",
                "instructions": (
                    "Which code snippet template is requested? "
                    f"Choose none if none. Command: {part!r}"
                ),
                "criteria": {
                    **{k: v for k, v in C.SNIPPETS.items()},
                    "none": "No snippet",
                },
            }
    return parts, questions


def _choice_id(answer: Any) -> str | None:
    if not isinstance(answer, dict):
        return None
    choice = answer.get("choice")
    if isinstance(choice, str) and choice and choice != "none":
        return choice
    return None


def _args_for_jev_action(
    action: str,
    part: str,
    app: str | None,
    site: str | None,
    editor_cmd: str | None,
    snippet: str | None,
) -> dict[str, Any]:
    """Fill closed-catalog args from Jev choices + local slot extraction."""
    text = _slots.normalize(part)
    args: dict[str, Any] = {}
    if action in {"open_app", "activate_app", "quit_app", "focus_editor"}:
        resolved = app or _slots.extract_app(text)
        if resolved and resolved in C.APPS:
            args["app"] = resolved
    elif action == "new_window":
        resolved = app or _slots.extract_app(text)
        if resolved and resolved in C.APPS:
            args["app"] = resolved
    elif action == "open_url":
        resolved_site = site or _slots.extract_site(text)
        url = _slots.extract_url(part)
        if resolved_site and resolved_site in C.SITES:
            args["site"] = resolved_site
            args["url"] = C.SITES[resolved_site]["url"]
        elif url:
            args["site"] = "url"
            args["url"] = url if url.startswith("http") else f"https://{url}"
        if re.search(r"\btab\b", text):
            args["new_tab"] = True
    elif action == "search_web":
        m = _SEARCH_RE.search(part.strip())
        query = m.group("q").strip() if m else ""
        if not query:
            # strip leading search verbs
            query = re.sub(
                r"^\s*(?:search(?:\s+for|\s+the\s+web\s+for)?|google|look up|look\s+up)\s+",
                "",
                part.strip(),
                flags=re.IGNORECASE,
            ).strip()
        if query:
            args["query"] = query
    elif action == "dictate":
        dictate_text = _slots.extract_dictate_text(part) or part.strip()
        args["text"] = dictate_text
    elif action == "say":
        m = _SAY_RE.match(part.strip())
        args["text"] = m.group("text").strip() if m else part.strip()
    elif action == "editor_command":
        cmd = editor_cmd
        if not cmd or cmd not in C.EDITOR_COMMANDS:
            for ident, info in C.EDITOR_COMMANDS.items():
                for phrase in info["phrases"]:
                    if re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", text):
                        cmd = ident
                        break
                if cmd:
                    break
        if cmd and cmd in C.EDITOR_COMMANDS:
            args["command"] = cmd
        line_m = _GO_TO_LINE_RE.search(text)
        if cmd == "go_to_line" and line_m:
            args["line"] = int(line_m.group("n"))
    elif action == "code_snippet":
        name = snippet
        if not name or name not in C.SNIPPETS:
            snippet_m = _SNIPPET_RE.search(text)
            if snippet_m:
                name = snippet_m.group("name").replace(" ", "_")
                if name == "if_else":
                    name = "if_else"
        if name and name in C.SNIPPETS:
            args["name"] = name
            args["template"] = C.SNIPPETS[name]
    return args


def plan_from_jev_answers(utterance: str, data: dict[str, Any], parts: list[str] | None = None) -> ActionPlan:
    """Build an ActionPlan from a Command Code systemone / Jev answers payload."""
    answers = data.get("answers") if isinstance(data.get("answers"), dict) else data
    if not isinstance(answers, dict):
        plan = route_local(utterance)
        plan.via = "local-fallback(jev-no-answers)"
        return plan
    if parts is None:
        parts = _slots.split_compound(utterance) or [utterance.strip() or utterance]
    actions: list[Action] = []
    for i, part in enumerate(parts):
        action_name = _choice_id(answers.get(f"action_{i}"))
        if not action_name or action_name not in C.ACTIONS:
            # fall back to local for this part
            actions.extend(_route_single(part))
            continue
        app = _choice_id(answers.get(f"app_{i}"))
        site = _choice_id(answers.get(f"site_{i}"))
        editor_cmd = _choice_id(answers.get(f"editor_{i}"))
        snippet = _choice_id(answers.get(f"snippet_{i}"))
        args = _args_for_jev_action(action_name, part, app, site, editor_cmd, snippet)
        # Require minimal args; otherwise local for this part
        if action_name in {"open_app", "activate_app", "quit_app", "focus_editor"} and "app" not in args:
            actions.extend(_route_single(part))
            continue
        if action_name == "open_url" and "url" not in args and "site" not in args:
            actions.extend(_route_single(part))
            continue
        if action_name == "search_web" and "query" not in args:
            actions.extend(_route_single(part))
            continue
        if action_name == "editor_command" and "command" not in args:
            actions.extend(_route_single(part))
            continue
        if action_name == "code_snippet" and "name" not in args:
            actions.extend(_route_single(part))
            continue
        actions.append(
            Action(
                action=action_name,
                args=args,
                confirm=_confirm_for(action_name),
                text=part.strip(),
            )
        )
    if not actions:
        plan = route_local(utterance)
        plan.via = "local-fallback(jev-empty)"
        return plan
    return ActionPlan(utterance=utterance, actions=actions, via="jev")


def route_via_jev(utterance: str, settings: Settings, timeout: float = 15.0) -> ActionPlan:
    """Route via Command Code Jev (typesafe/jev). Falls back to local on missing key/errors."""
    if not settings.command_code_api_key:
        plan = route_local(utterance)
        plan.via = "local-fallback(no-command-code-key)"
        return plan
    parts, questions = build_jev_questions(utterance)
    state = {"utterance": utterance, "parts": parts}
    try:
        from mac_voice.llm.command_code import CommandCodeClient

        client = CommandCodeClient(api_key=settings.command_code_api_key)
        data = client.systemone(
            state,
            questions,
            model=JEV_MODEL,
            timeout=timeout,
        )
    except Exception as exc:
        plan = route_local(utterance)
        plan.via = f"local-fallback({type(exc).__name__})"
        return plan
    return plan_from_jev_answers(utterance, data, parts=parts)


def plan_from_jev_payload(utterance: str, data: dict[str, Any]) -> ActionPlan:
    """Accept systemone answers OR a legacy {actions:[...]} shape."""
    if isinstance(data.get("answers"), dict) or any(
        isinstance(k, str) and k.startswith("action_") for k in data
    ):
        return plan_from_jev_answers(utterance, data)
    raw_actions = data.get("actions") or data.get("plan") or []
    actions: list[Action] = []
    for item in raw_actions:
        if isinstance(item, str):
            if item in C.ACTIONS:
                actions.append(Action(action=item, args={}, confirm=_confirm_for(item)))
            continue
        if not isinstance(item, dict):
            continue
        name = item.get("action", "")
        if name not in C.ACTIONS:
            continue
        args = {k: v for k, v in item.get("args", {}).items() if isinstance(k, str)}
        actions.append(Action(action=name, args=args, confirm=_confirm_for(name)))
    if not actions:
        return route_local(utterance)
    return ActionPlan(utterance=utterance, actions=actions, via="jev")


def plan_from_llm_payload(utterance: str, data: dict[str, Any]) -> ActionPlan:
    """Build an ActionPlan from LLM JSON after closed-catalog validation."""
    from mac_voice.llm.command_code import validate_llm_actions

    cleaned = validate_llm_actions(data)
    actions = [
        Action(
            action=item["action"],
            args=item.get("args", {}),
            confirm=_confirm_for(item["action"]),
            text=utterance.strip(),
        )
        for item in cleaned
    ]
    if not actions:
        plan = route_local(utterance)
        plan.via = "local-fallback(llm-empty)"
        return plan
    return ActionPlan(utterance=utterance, actions=actions, via="llm")


def route_via_llm(utterance: str, settings: Settings) -> ActionPlan:
    """Ask Command Code for a JSON ActionPlan; validate; fall back to local."""
    if not settings.command_code_api_key:
        plan = route_local(utterance)
        plan.via = "local-fallback(no-command-code-key)"
        return plan
    try:
        from mac_voice.llm.command_code import CommandCodeClient

        client = CommandCodeClient(
            api_key=settings.command_code_api_key,
            model=settings.llm_model,
        )
        data = client.route_to_action_plan_json(utterance)
        return plan_from_llm_payload(utterance, data)
    except Exception as exc:
        plan = route_local(utterance)
        plan.via = f"local-fallback({type(exc).__name__})"
        return plan


def route_utterance(
    utterance: str,
    settings: Settings | None = None,
    use_jev: bool = False,
    use_llm: bool = False,
) -> ActionPlan:
    settings = settings or Settings()
    if use_llm and settings.command_code_api_key:
        return route_via_llm(utterance, settings)
    if use_jev:
        return route_via_jev(utterance, settings)
    return route_local(utterance)
