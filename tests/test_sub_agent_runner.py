from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

os.environ.setdefault("JARVIS_ENABLE_TELEGRAM", "0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")

if "telegram" not in sys.modules:
    telegram_package = types.ModuleType("telegram")
    telegram_intelligence_module = types.ModuleType("telegram.telegram_intelligence")

    class _DummyTelegramIntelligence:
        def __init__(self, *args, **kwargs) -> None:
            pass

    telegram_intelligence_module.TelegramIntelligence = _DummyTelegramIntelligence
    telegram_package.telegram_intelligence = telegram_intelligence_module
    sys.modules["telegram"] = telegram_package
    sys.modules["telegram.telegram_intelligence"] = telegram_intelligence_module

import bridge as bridge_module
from server.skills import sub_agent_runner


def test_is_multi_step_detects_complex_prompt() -> None:
    assert sub_agent_runner.is_multi_step("analiz et ve ozetle") is True


def test_is_multi_step_rejects_simple_prompt() -> None:
    assert sub_agent_runner.is_multi_step("merhaba") is False


def test_run_file_reader_gracefully_handles_missing_file() -> None:
    result = sub_agent_runner._run_file_reader({"path": "nonexistent-file.py"})

    assert "Dosya okunamadi:" in result
    assert "nonexistent-file.py" in result


def test_run_summarizer_uses_openai_sdk_for_groq(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    class _FakeCompletions:
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="kisa ozet")
                    )
                ]
            )

    class _FakeClient:
        def __init__(self, **kwargs) -> None:
            captured["init"] = kwargs
            self.chat = SimpleNamespace(completions=_FakeCompletions())
            captured["client"] = self

    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setattr(sub_agent_runner, "OpenAI", _FakeClient)

    result = sub_agent_runner._run_summarizer({"text": "Uzun bir metni kisalt."})

    assert result == "kisa ozet"
    assert captured["init"] == {
        "api_key": "groq-test-key",
        "base_url": "https://api.groq.com/openai/v1",
        "timeout": 30,
    }
    completion_call = captured["client"].chat.completions.calls[0]
    assert completion_call["model"] == sub_agent_runner.DEFAULT_GROQ_MODEL
    assert completion_call["messages"][1]["content"].startswith("Ozetle:")


def test_run_sub_agents_continues_after_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sub_agent_runner,
        "_RUNNER_IMPLS",
        {
            "file_reader": lambda payload: (_ for _ in ()).throw(
                sub_agent_runner.SubAgentRunnerError("boom")
            ),
            "summarizer": lambda payload: "toparlanan sonuc",
        },
    )

    result = sub_agent_runner.run_sub_agents(
        "seda",
        "analiz et ve ozetle",
        ["file_reader", "summarizer"],
    )

    assert "[file_reader] adimda sorun cikti: boom" in result
    assert "[summarizer] toparlanan sonuc" in result


def test_bridge_swarm_hook_prefixes_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_SWARM_PROCESS_MESSAGE",
        lambda chat_id, text: "[SEDA] nihai cevap",
    )
    monkeypatch.setattr(
        bridge_module,
        "_get_active_persona_payload",
        lambda chat_id=None, lane=None: {
            "id": "seda",
            "sub_agents": ["file_reader", "summarizer"],
        },
    )
    monkeypatch.setattr(sub_agent_runner, "is_multi_step", lambda message: True)
    monkeypatch.setattr(
        sub_agent_runner,
        "run_sub_agents",
        lambda persona_id, task, agent_types=None: "[file_reader] bridge\n\n[summarizer] ozet",
    )

    response = bridge_module.process_message(
        bridge_module.WEB_CHAT_ID,
        "analiz et ve ozetle",
    )

    assert response.startswith("Alt ajan bulgulari:")
    assert "[file_reader] bridge" in response
    assert "[SEDA] nihai cevap" in response
