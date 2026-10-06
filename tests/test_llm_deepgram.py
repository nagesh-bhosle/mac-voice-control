"""Tests for Command Code LLM validation and Deepgram client wiring (mocked HTTP)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from mac_voice.brain.jev_router import plan_from_llm_payload, route_utterance
from mac_voice.config import Settings, load_settings
from mac_voice.llm.command_code import (
    COMMAND_CODE_CHAT_URL,
    CommandCodeClient,
    CommandCodeError,
    parse_json_object,
    validate_llm_actions,
)
from mac_voice.stt.deepgram_engine import (
    DEEPGRAM_LISTEN_URL,
    DeepgramEngine,
    DeepgramNotConfiguredError,
)


def test_validate_llm_actions_keeps_closed_catalog_only():
    data = {
        "actions": [
            {"action": "open_app", "args": {"app": "chrome"}},
            {"action": "run_shell", "args": {"cmd": "rm -rf /"}},  # rejected
            {"action": "open_url", "args": {"site": "facebook", "new_tab": True}},
            {"action": "open_app", "args": {"app": "not_a_real_app"}},  # app dropped
            "dictate",
        ]
    }
    cleaned = validate_llm_actions(data)
    assert [c["action"] for c in cleaned] == ["open_app", "open_url", "dictate"]
    assert cleaned[0]["args"] == {"app": "chrome"}
    assert cleaned[1]["args"]["site"] == "facebook"
    assert cleaned[1]["args"]["url"] == "https://www.facebook.com"
    assert cleaned[1]["args"]["new_tab"] is True
    assert cleaned[2]["args"] == {}


def test_validate_rejects_unknown_and_shellish_args():
    cleaned = validate_llm_actions(
        {
            "actions": [
                {"action": "search_web", "args": {"query": "jev docs", "shell": "echo hi"}},
                {"action": "editor_command", "args": {"command": "save"}},
                {"action": "code_snippet", "args": {"name": "main"}},
            ]
        }
    )
    assert cleaned[0]["args"] == {"query": "jev docs"}
    assert cleaned[1]["args"]["command"] == "save"
    assert cleaned[2]["args"]["name"] == "main"
    assert "template" in cleaned[2]["args"]


def test_parse_json_object_from_fence():
    raw = 'Sure.\n```json\n{"actions":[{"action":"mute","args":{}}]}\n```\n'
    data = parse_json_object(raw)
    assert data["actions"][0]["action"] == "mute"


def test_plan_from_llm_payload_sets_via_llm():
    plan = plan_from_llm_payload(
        "open chrome",
        {"actions": [{"action": "open_app", "args": {"app": "chrome"}}]},
    )
    assert plan.via == "llm"
    assert plan.actions[0].action == "open_app"
    assert plan.actions[0].args["app"] == "chrome"


def test_plan_from_llm_empty_falls_back_local():
    plan = plan_from_llm_payload("open chrome", {"actions": [{"action": "hack"}]})
    assert plan.via == "local-fallback(llm-empty)"
    assert plan.actions[0].action == "open_app"


def test_route_utterance_use_llm_without_key_falls_back():
    settings = Settings(command_code_api_key="")
    plan = route_utterance("open chrome", settings, use_llm=True)
    assert plan.via == "local"
    assert plan.actions[0].action == "open_app"


def test_command_code_chat_url_and_headers():
    client = CommandCodeClient(api_key="cc-test-key", model="meta/muse-spark-1.3-contributor")
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "choices": [{"message": {"content": '{"actions":[{"action":"mute","args":{}}]}'}}]
        }
        return resp

    with patch("mac_voice.llm.command_code.httpx.post", side_effect=fake_post):
        text = client.chat([{"role": "user", "content": "mute"}])
    assert captured["url"] == COMMAND_CODE_CHAT_URL
    assert captured["headers"]["Authorization"] == "Bearer cc-test-key"
    assert captured["json"]["model"] == "meta/muse-spark-1.3-contributor"
    assert "mute" in text


def test_command_code_requires_key():
    client = CommandCodeClient(api_key="")
    with pytest.raises(CommandCodeError):
        client.chat([{"role": "user", "content": "hi"}])


def test_deepgram_url_and_auth_headers():
    engine = DeepgramEngine(api_key="dg-test-key", model="nova-3")
    assert engine.listen_url().startswith(DEEPGRAM_LISTEN_URL)
    assert "model=nova-3" in engine.listen_url()
    headers = engine.auth_headers()
    assert headers["Authorization"] == "Token dg-test-key"


def test_deepgram_transcribe_bytes_mocked():
    engine = DeepgramEngine(api_key="dg-test-key", model="nova-2")
    captured = {}

    def fake_post(url, headers=None, content=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["content"] = content
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "results": {
                "channels": [
                    {"alternatives": [{"transcript": "open chrome"}]}
                ]
            }
        }
        return resp

    with patch("mac_voice.stt.deepgram_engine.httpx.post", side_effect=fake_post):
        text = engine.transcribe_bytes(b"RIFF....", content_type="audio/wav")
    assert text == "open chrome"
    assert captured["url"].startswith(DEEPGRAM_LISTEN_URL)
    assert "model=nova-2" in captured["url"]
    assert captured["headers"]["Authorization"] == "Token dg-test-key"
    assert captured["headers"]["Content-Type"] == "audio/wav"
    assert captured["content"] == b"RIFF...."


def test_deepgram_requires_key():
    engine = DeepgramEngine(api_key="")
    with pytest.raises(DeepgramNotConfiguredError):
        engine.transcribe_bytes(b"x")


def test_load_settings_reads_command_code_and_deepgram(monkeypatch):
    monkeypatch.setenv("DEEPGRAM_API_KEY", "dg-abc")
    monkeypatch.setenv("CMD_API_KEY", "cc-from-alias")
    monkeypatch.setenv("MAC_VOICE_MODEL", "poolside/laguna-s-2.1-free")
    monkeypatch.setenv("MAC_VOICE_STT", "deepgram")
    monkeypatch.setenv("MAC_VOICE_USE_LLM", "1")
    monkeypatch.delenv("COMMAND_CODE_API_KEY", raising=False)
    settings = load_settings()
    assert settings.deepgram_api_key == "dg-abc"
    assert settings.command_code_api_key == "cc-from-alias"
    assert settings.llm_model == "poolside/laguna-s-2.1-free"
    assert settings.stt_provider == "deepgram"
    assert settings.llm_enabled is True


def test_route_via_llm_mocked_http():
    settings = Settings(
        command_code_api_key="cc-key",
        llm_model="meta/muse-spark-1.3-contributor",
    )

    def fake_post(url, headers=None, json=None, timeout=None):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": (
                            '{"actions":[{"action":"open_app","args":{"app":"chrome"}}]}'
                        )
                    }
                }
            ]
        }
        return resp

    with patch("mac_voice.llm.command_code.httpx.post", side_effect=fake_post):
        plan = route_utterance("open chrome please", settings, use_llm=True)
    assert plan.via == "llm"
    assert plan.actions[0].action == "open_app"
    assert plan.actions[0].args["app"] == "chrome"
