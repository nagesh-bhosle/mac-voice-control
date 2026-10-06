"""Jev router: local heuristic routing (always offline) plus optional TypeSafe Jev API.

The local router is the primary path for --dry-run and tests. When
TYPESAFE_API_KEY is set and --no-local is passed, the router calls the
TypeSafe Jev API with Choice questions built from the closed catalogs
and falls back to the local heuristic if the API fails.

The closed action set in brain/candidates.py is the only source of
actions. Model output is never executed as shell.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from mac_voice.brain import candidates as C
from mac_voice.brain.slots import SlotExtractor
from mac_voice.config import Settings

JEV_API_URL = "https://api.typesafe.ai/v1/jev/route"

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


def build_choice_questions(utterance: str) -> list[dict[str, Any]]:
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


def route_via_jev(utterance: str, settings: Settings, timeout: float = 15.0) -> ActionPlan:
    if not settings.typesafe_api_key:
        raise RuntimeError("TYPESAFE_API_KEY is not set")
    payload = {
        "utterance": utterance,
        "questions": build_choice_questions(utterance),
        "actions": list(C.ACTIONS),
    }
    headers = {"Authorization": f"Bearer {settings.typesafe_api_key}"}
    try:
        resp = httpx.post(JEV_API_URL, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        plan = route_local(utterance)
        plan.via = f"local-fallback({type(exc).__name__})"
        return plan
    try:
        data = resp.json()
    except ValueError:
        plan = route_local(utterance)
        plan.via = "local-fallback(bad-json)"
        return plan
    return plan_from_jev_payload(utterance, data)


def plan_from_jev_payload(utterance: str, data: dict[str, Any]) -> ActionPlan:
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


def route_utterance(utterance: str, settings: Settings | None = None, use_jev: bool = False) -> ActionPlan:
    settings = settings or Settings()
    if use_jev and settings.typesafe_api_key:
        return route_via_jev(utterance, settings)
    return route_local(utterance)
