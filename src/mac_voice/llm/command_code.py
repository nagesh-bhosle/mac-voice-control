"""Command Code Provider API client (OpenAI-compatible chat completions)."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from mac_voice.brain import candidates as C
from mac_voice.config import DEFAULT_LLM_MODEL

COMMAND_CODE_CHAT_URL = "https://api.commandcode.ai/provider/v1/chat/completions"

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


class CommandCodeError(RuntimeError):
    pass


class CommandCodeClient:
    """Thin chat-completions client for Command Code Provider API."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_LLM_MODEL,
        timeout: float = 45.0,
        base_url: str = COMMAND_CODE_CHAT_URL,
    ) -> None:
        self.api_key = (api_key or "").strip()
        self.model = model or DEFAULT_LLM_MODEL
        self.timeout = timeout
        self.base_url = base_url

    def require_key(self) -> None:
        if not self.api_key:
            raise CommandCodeError(
                "COMMAND_CODE_API_KEY (or CMD_API_KEY) is not set. Add it to .env."
            )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
    ) -> str:
        self.require_key()
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.post(
            self.base_url,
            headers=headers,
            json=payload,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        try:
            return (data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise CommandCodeError(f"Unexpected Command Code response shape: {data!r}") from exc

    def normalize_code_dictation(self, transcript: str) -> str:
        """Turn spoken code into exact typed text. Returns empty string on blank input."""
        text = (transcript or "").strip()
        if not text:
            return ""
        content = self.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "Convert spoken code dictation into exact typed code text. "
                        "Reply with only the code, no markdown fences, no explanation."
                    ),
                },
                {"role": "user", "content": text},
            ],
            max_tokens=512,
        )
        return content.strip() or text

    def route_to_action_plan_json(self, utterance: str) -> dict[str, Any]:
        """Ask the model for a closed-catalog ActionPlan JSON object.

        The model may only propose actions from C.ACTIONS with args constrained
        to known apps/sites/editor commands. Free-form shell is never allowed.
        """
        catalog = {
            "actions": list(C.ACTIONS),
            "apps": sorted(C.APPS.keys()),
            "sites": sorted(C.SITES.keys()),
            "editor_commands": sorted(C.EDITOR_COMMANDS.keys()),
            "snippets": sorted(C.SNIPPETS.keys()),
        }
        system = (
            "You are a Mac voice-control router. Reply with ONLY a JSON object "
            'shaped like {"actions":[{"action":"...","args":{...}}]}. '
            "Every action MUST be one of the closed catalog action ids. "
            "App ids must be from apps, site ids from sites, editor command ids "
            "from editor_commands, snippet names from snippets. "
            "Never invent shell commands, scripts, or actions outside the catalog. "
            "If unsure, use a single dictate action with the utterance as text."
        )
        user = (
            f"Closed catalog:\n{json.dumps(catalog, indent=2)}\n\n"
            f"Utterance: {utterance!r}\n\n"
            "Return ONLY the JSON object."
        )
        raw = self.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=1024,
        )
        return parse_json_object(raw)


def parse_json_object(raw: str) -> dict[str, Any]:
    """Extract a JSON object from model text (fences or bare JSON)."""
    text = (raw or "").strip()
    if not text:
        raise CommandCodeError("Empty model response")
    fence = _JSON_FENCE_RE.search(text)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise CommandCodeError(f"Model did not return JSON: {raw[:200]!r}")
        data = json.loads(text[start : end + 1])
    if not isinstance(data, dict):
        raise CommandCodeError("Model JSON root must be an object")
    return data


def validate_llm_actions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep only closed-catalog actions; drop unknown names and unsafe args."""
    raw_actions = data.get("actions") or data.get("plan") or []
    if not isinstance(raw_actions, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for item in raw_actions:
        if isinstance(item, str):
            if item in C.ACTIONS:
                cleaned.append({"action": item, "args": {}})
            continue
        if not isinstance(item, dict):
            continue
        name = item.get("action", "")
        if name not in C.ACTIONS:
            continue
        raw_args = item.get("args", {})
        if not isinstance(raw_args, dict):
            raw_args = {}
        args = _sanitize_args(name, raw_args)
        if not _args_ok(name, args):
            continue
        cleaned.append({"action": name, "args": args})
    return cleaned


def _args_ok(action: str, args: dict[str, Any]) -> bool:
    """Reject actions that are missing required closed-catalog args."""
    if action in {"open_app", "activate_app", "quit_app", "focus_editor"}:
        return "app" in args
    if action == "open_url":
        return "url" in args or "site" in args
    if action == "search_web":
        return "query" in args
    if action == "editor_command":
        return "command" in args
    if action == "code_snippet":
        return "name" in args
    if action == "dictate":
        return True  # text may be empty; still a valid no-op dictate
    if action == "say":
        return "text" in args
    return True


def _sanitize_args(action: str, args: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if action in {"open_app", "activate_app", "quit_app", "focus_editor"}:
        app = args.get("app")
        if isinstance(app, str) and app in C.APPS:
            out["app"] = app
    elif action == "new_window":
        app = args.get("app")
        if isinstance(app, str) and app in C.APPS:
            out["app"] = app
    elif action == "open_url":
        site = args.get("site")
        if isinstance(site, str) and site in C.SITES:
            out["site"] = site
            out["url"] = C.SITES[site]["url"]
        elif isinstance(site, str) and site == "url":
            url = args.get("url")
            if isinstance(url, str) and url.startswith(("http://", "https://")):
                out["site"] = "url"
                out["url"] = url
        if args.get("new_tab") is True:
            out["new_tab"] = True
        browser = args.get("browser")
        if isinstance(browser, str) and browser in C.APPS:
            out["browser"] = browser
    elif action == "search_web":
        query = args.get("query")
        if isinstance(query, str) and query.strip():
            out["query"] = query.strip()
    elif action == "dictate":
        text = args.get("text")
        if isinstance(text, str):
            out["text"] = text
    elif action == "editor_command":
        cmd = args.get("command")
        if isinstance(cmd, str) and cmd in C.EDITOR_COMMANDS:
            out["command"] = cmd
        app = args.get("app")
        if isinstance(app, str) and app in C.APPS and C.APPS[app].get("editor"):
            out["app"] = app
        line = args.get("line")
        if isinstance(line, int) and line > 0:
            out["line"] = line
    elif action == "code_snippet":
        name = args.get("name")
        if isinstance(name, str) and name in C.SNIPPETS:
            out["name"] = name
            out["template"] = C.SNIPPETS[name]
    elif action == "say":
        text = args.get("text")
        if isinstance(text, str):
            out["text"] = text
    # volume_*/mute/screenshot/tab actions take no free-form args
    return out
