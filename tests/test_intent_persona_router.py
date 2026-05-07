from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace

from server.skills import intent_persona_router


def test_research_message_routes_to_mert():
    result = intent_persona_router.analyze_message(
        "eBay'de laptop fiyatlarina bak ve arastir",
        current_persona="jarvis",
    )

    assert result["detected_intent"] == "research"
    assert result["target_persona"] == "mert"
    assert result["auto_switched"] is True
    assert intent_persona_router.route_to_persona(result, "jarvis") == "mert"


def test_code_message_routes_to_seda():
    result = intent_persona_router.analyze_message(
        "Su Python kodunu incele, stack trace hatasini duzelt",
        current_persona="jarvis",
    )

    assert result["detected_intent"] == "code"
    assert result["target_persona"] == "seda"
    assert intent_persona_router.route_to_persona(result, "jarvis") == "seda"


def test_same_persona_does_not_switch_again():
    result = intent_persona_router.analyze_message(
        "kodu incele ve testleri duzelt",
        current_persona="seda",
    )

    assert result["detected_intent"] == "code"
    assert result["target_persona"] == "seda"
    assert result["auto_switched"] is False
    assert intent_persona_router.route_to_persona(result, "seda") is None


def test_low_confidence_keeps_current_persona():
    result = intent_persona_router.analyze_message(
        "bir bakar misin",
        current_persona="jarvis",
    )

    assert result["confidence"] < intent_persona_router.CONFIDENCE_THRESHOLD
    assert result["target_persona"] is None
    assert intent_persona_router.route_to_persona(result, "jarvis") is None


def test_security_intent_routes_to_luna():
    result = intent_persona_router.analyze_message(
        "security audit yap, token loglarini kontrol et",
        current_persona="jarvis",
    )

    assert result["detected_intent"] == "security"
    assert result["target_persona"] == "luna"
    assert intent_persona_router.route_to_persona(result, "jarvis") == "luna"


def _load_bridge_module():
    server_path = Path(__file__).resolve().parents[1] / "server"
    if str(server_path) not in sys.path:
        sys.path.insert(0, str(server_path))
    return importlib.import_module("bridge")


def _run_bridge_flow(
    monkeypatch,
    *,
    message: str,
    current_persona: str,
    original_response: str = "tamam",
):
    bridge = _load_bridge_module()
    switch_calls: list[tuple[int, str]] = []

    def fake_load_skill(module_name: str):
        if module_name == "pc_control_gateway":
            return SimpleNamespace(infer_pc_command=lambda _text: None)
        if module_name == "intent_persona_router":
            return intent_persona_router
        raise AssertionError(f"unexpected skill request: {module_name}")

    def fake_switch(chat_id: int, persona_name: str) -> dict:
        switch_calls.append((chat_id, persona_name))
        return {
            "ok": True,
            "id": persona_name,
            "name": persona_name.capitalize(),
        }

    monkeypatch.setattr(bridge, "_autonomous_load_skill", fake_load_skill)
    monkeypatch.setattr(bridge, "_autonomous_handle_wiki_intent", lambda chat_id, text: None)
    monkeypatch.setattr(
        bridge,
        "_load_persona_manager_module",
        lambda: SimpleNamespace(detect_switch_from_text=lambda text: False),
    )
    monkeypatch.setattr(
        bridge,
        "_get_active_persona_payload",
        lambda chat_id=None: {"id": current_persona},
    )
    monkeypatch.setattr(bridge, "_switch_persona_for_chat", fake_switch)
    monkeypatch.setattr(
        bridge,
        "_ORIGINAL_AUTONOMOUS_PROCESS_MESSAGE",
        lambda chat_id, text: original_response,
    )
    monkeypatch.setattr(
        bridge,
        "_autonomous_record_persona_turns",
        lambda chat_id, clean_user_text, clean_response, source="bridge": None,
    )
    monkeypatch.setattr(
        bridge,
        "_autonomous_maybe_write_obsidian",
        lambda chat_id, text, response, intent_result=None: None,
    )

    response = bridge._process_message_with_autonomous_layer(101, message)
    return response, switch_calls


def test_bridge_security_intent_switches_to_luna(monkeypatch):
    response, switch_calls = _run_bridge_flow(
        monkeypatch,
        message="security audit yap ve token loglarini tara",
        current_persona="jarvis",
        original_response="guvenlik sonucu hazir",
    )

    assert switch_calls == [(101, "luna")]
    assert response.startswith("Luna moduna geciyorum - guvenlik modu.")
    assert response.endswith("guvenlik sonucu hazir")


def test_bridge_same_persona_does_not_switch(monkeypatch):
    response, switch_calls = _run_bridge_flow(
        monkeypatch,
        message="kodu incele ve testleri duzelt",
        current_persona="seda",
        original_response="kod analizi tamam",
    )

    assert switch_calls == []
    assert response == "kod analizi tamam"


def test_bridge_low_confidence_does_not_switch(monkeypatch):
    response, switch_calls = _run_bridge_flow(
        monkeypatch,
        message="bir bakar misin",
        current_persona="jarvis",
        original_response="genel yardim cevabi",
    )

    assert switch_calls == []
    assert response == "genel yardim cevabi"
