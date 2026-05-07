from __future__ import annotations

import json
from unittest.mock import MagicMock

from server.slack_bridge import (
    SlackBridgeConfig,
    build_bridge_payload,
    check_status,
    extract_jarvis_text,
    format_slack_reply,
    redact_secret,
    should_handle_message,
    should_ignore_event,
    stable_slack_chat_id,
)


def test_redact_secret_keeps_shape_without_leaking_full_value() -> None:
    assert redact_secret("xoxb-1234567890") == "xoxb...7890"
    assert redact_secret("short") == "***"


def test_stable_slack_chat_id_is_deterministic() -> None:
    first = stable_slack_chat_id("T1", "C1", "U1")
    second = stable_slack_chat_id("T1", "C1", "U1")

    assert first == second
    assert isinstance(first, int)


def test_should_ignore_bot_and_empty_events() -> None:
    assert should_ignore_event({"bot_id": "B1", "text": "hi"}) is True
    assert should_ignore_event({"subtype": "bot_message", "text": "hi"}) is True
    assert should_ignore_event({"user": "Ubot", "text": "hi"}, bot_user_id="Ubot") is True
    assert should_ignore_event({"user": "U1", "text": ""}) is True
    assert should_ignore_event({"user": "U1", "text": "jarvis status"}) is False


def test_should_handle_dm_and_prefixed_channel_message() -> None:
    assert should_handle_message({"channel_type": "im", "text": "selam"}) is True
    assert should_handle_message({"channel_type": "channel", "text": "jarvis status"}) is True
    assert should_handle_message({"channel_type": "channel", "text": "/jarvis status"}) is True
    assert should_handle_message({"channel_type": "channel", "text": "normal mesaj"}) is False
    assert should_handle_message({"channel_type": "channel", "text": "<@Ubot> status"}, "Ubot") is True


def test_extract_jarvis_text_strips_prefix_and_mentions() -> None:
    assert extract_jarvis_text({"text": "<@Ubot> jarvis status"}, "Ubot") == "status"
    assert extract_jarvis_text({"text": "/jarvis /help"}) == "/help"
    assert extract_jarvis_text({"text": "jarvis"}) == "yardim"


def test_build_bridge_payload_contains_slack_context() -> None:
    payload = build_bridge_payload(
        {
            "team": "T1",
            "channel": "C1",
            "user": "U1",
            "thread_ts": "123.45",
            "ts": "123.45",
        },
        "status",
    )

    assert payload["message"] == "status"
    assert payload["source"] == "slack"
    assert payload["lane"] == "slack"
    assert payload["slack"]["channel_id"] == "C1"
    assert payload["chat_id"] == payload["chatId"]


def test_format_slack_reply_truncates_long_text() -> None:
    text = "x" * 5000
    reply = format_slack_reply(text)

    assert len(reply) <= 3500
    assert "kisaltti" in reply


def test_check_status_redacts_tokens(monkeypatch) -> None:
    monkeypatch.setattr("server.slack_bridge.is_bolt_available", lambda: True)
    monkeypatch.setattr("server.slack_bridge.bridge_health", lambda *_args, **_kwargs: False)
    config = SlackBridgeConfig(
        bot_token="xoxb-secret-token",
        app_token="xapp-secret-token",
        signing_secret="signing-secret",
        bridge_url="http://127.0.0.1:8081",
        bot_user_id="Ubot",
    )

    status = check_status(config)

    assert status["ok"] is True
    dumped = json.dumps(status)
    assert "secret-token" not in dumped
    assert status["bot_token_present"] is True

