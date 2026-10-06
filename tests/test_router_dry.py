"""Dry-run router tests: fixtures in, typed actions out. No AX calls."""

from __future__ import annotations

import json
from pathlib import Path

from mac_voice.brain import candidates as C
from mac_voice.brain.jev_router import route_local, route_utterance

FIXTURES = json.loads((Path(__file__).parent / "fixtures" / "utterances.json").read_text())


def check_case(case):
    plan = route_local(case["utterance"])
    expected = case["actions"]
    got = [a.action for a in plan.actions]
    want = [e["action"] for e in expected]
    assert got == want, f"{case['utterance']!r}: got {got}, want {want}"
    for action, exp in zip(plan.actions, expected):
        assert action.action in C.ACTIONS
        for key, value in exp.get("args", {}).items():
            assert action.args.get(key) == value, (
                f"{case['utterance']!r}: {action.action} arg {key!r} "
                f"is {action.args.get(key)!r}, want {value!r}"
            )
    return plan


def test_fixture_utterances():
    assert len(FIXTURES) >= 8
    for case in FIXTURES:
        check_case(case)


def test_route_utterance_matches_local_without_jev():
    for case in FIXTURES:
        local = route_local(case["utterance"])
        via = route_utterance(case["utterance"])
        assert via.via == "local"
        assert [a.action for a in via.actions] == [a.action for a in local.actions]


def test_compound_chrome_facebook():
    plan = route_local("open chrome and open facebook in a tab")
    assert [a.action for a in plan.actions] == ["open_app", "open_url"]
    assert plan.actions[0].args["app"] == "chrome"
    assert plan.actions[1].args["site"] == "facebook"


def test_intellij_dictate():
    plan = route_local("in intellij type public static void main")
    assert [a.action for a in plan.actions] == ["focus_editor", "dictate"]
    assert plan.actions[0].args["app"] == "intellij"
    assert plan.actions[1].args["text"] == "public static void main"


def test_all_actions_from_closed_set():
    for case in FIXTURES:
        plan = route_local(case["utterance"])
        for action in plan.actions:
            assert action.action in C.ACTIONS
