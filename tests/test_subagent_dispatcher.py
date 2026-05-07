from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from server.subagent_dispatcher import (
    DispatchResult,
    PersonaNotFoundError,
    SubAgentDispatcher,
    SubAgentNotAllowedError,
)
from server.subagent_registry import SubAgentRegistry, reset_registry


@pytest.fixture
def fake_registry(tmp_path):
    """Minimal registry with two agents tied to one persona."""
    sub_yaml = tmp_path / "subagents.yaml"
    sub_yaml.write_text(
        yaml.safe_dump(
            {
                "subagents": {
                    "writer": {
                        "description": "Writes structured notes.",
                        "mode": "subagent",
                        "hidden": False,
                        "tools": {"write": True, "obsidian": True},
                        "prompt": "You are a writer sub-agent.",
                    },
                    "searcher": {
                        "description": "Runs web searches.",
                        "mode": "subagent",
                        "hidden": True,
                        "tools": {"web_search": True},
                        "prompt": "You are a searcher sub-agent.",
                    },
                    "forbidden": {
                        "description": "Not attached to any persona.",
                        "mode": "subagent",
                        "hidden": True,
                        "tools": {"read": True},
                        "prompt": "You should not be callable.",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    agents_yaml = tmp_path / "agents.yaml"
    agents_yaml.write_text(
        yaml.safe_dump(
            {
                "personas": {
                    "sabri": {
                        "name": "Sabri",
                        "role": "creative director",
                        "sub_agents": ["writer", "searcher"],
                        "llm_profile": {"model": "m1", "fallback_model": "m2"},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    reset_registry()
    return SubAgentRegistry(yaml_path=sub_yaml, agents_yaml=agents_yaml)


@pytest.fixture
def persona_loader():
    def _load():
        return {
            "sabri": {
                "persona_id": "sabri",
                "name": "Sabri",
                "role": "creative director",
                "llm_profile": {"model": "m1", "fallback_model": "m2", "model_chain": "reasoning"},
                "sub_agents": ["writer", "searcher"],
            }
        }

    return _load


@pytest.fixture
def stub_llm():
    calls: list[dict] = []

    def _llm(payload):
        calls.append(payload)
        return "stub-response-text", {
            "ok": True,
            "selected_model": "m1",
            "selected_provider": "stub",
        }

    _llm.calls = calls  # type: ignore[attr-defined]
    return _llm


def _build(fake_registry, persona_loader, stub_llm):
    return SubAgentDispatcher(
        registry=fake_registry,
        llm=stub_llm,
        persona_loader=persona_loader,
    )


# ---------- happy path ----------


def test_dispatch_success_returns_llm_output(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("sabri", "writer", "Write a brand note")
    assert isinstance(result, DispatchResult)
    assert result.ok is True
    assert result.output == "stub-response-text"
    assert result.model == "m1"
    assert result.provider == "stub"
    assert result.error is None
    assert result.duration_ms >= 0


def test_system_prompt_includes_persona_role_and_agent_prompt(
    fake_registry, persona_loader, stub_llm
):
    d = _build(fake_registry, persona_loader, stub_llm)
    d.dispatch("sabri", "writer", "task x")
    payload = stub_llm.calls[-1]
    assert "Sabri" in payload["system"]
    assert "creative director" in payload["system"]
    assert "writer sub-agent" in payload["system"]
    assert payload["messages"][0]["content"] == "task x"


def test_context_is_appended_to_user_message(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    d.dispatch("sabri", "writer", "ana görev", context={"kanal": "telegram", "zorluk": "kolay"})
    payload = stub_llm.calls[-1]
    content = payload["messages"][0]["content"]
    assert "ana görev" in content
    assert "- kanal: telegram" in content
    assert "- zorluk: kolay" in content


def test_available_lists_persona_sub_agents(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    assert d.available("sabri") == ["writer", "searcher"]


# ---------- failure modes ----------


def test_unknown_persona_returns_not_ok(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("ghost", "writer", "task")
    assert result.ok is False
    assert "persona not defined" in (result.error or "")


def test_persona_cannot_call_unattached_sub_agent(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("sabri", "forbidden", "task")
    assert result.ok is False
    assert "not authorized" in (result.error or "")


def test_empty_task_rejected(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("sabri", "writer", "   ")
    assert result.ok is False
    assert "task is empty" in (result.error or "")
    # LLM should NOT be called
    assert stub_llm.calls == []


def test_unknown_agent_name_blocked(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("sabri", "nonexistent_agent", "hi")
    assert result.ok is False
    assert "not authorized" in (result.error or "")


def test_llm_exception_is_captured_not_raised(fake_registry, persona_loader):
    def boom(payload):
        raise RuntimeError("provider-down")

    d = SubAgentDispatcher(
        registry=fake_registry,
        llm=boom,
        persona_loader=persona_loader,
    )
    result = d.dispatch("sabri", "writer", "task")
    assert result.ok is False
    assert "llm_error: provider-down" in (result.error or "")


def test_llm_returns_not_ok_trace(fake_registry, persona_loader):
    def bad_llm(payload):
        return "", {"ok": False, "error": "rate_limited"}

    d = SubAgentDispatcher(
        registry=fake_registry,
        llm=bad_llm,
        persona_loader=persona_loader,
    )
    result = d.dispatch("sabri", "writer", "task")
    assert result.ok is False
    assert result.error == "rate_limited"


# ---------- persistence ----------


def test_persist_to_brain_writes_memory_file(
    tmp_path, fake_registry, persona_loader, stub_llm, monkeypatch
):
    # Set up a real brain vault
    vault = tmp_path / "brain_vault"
    (vault / "personas" / "sabri" / "04-Memory").mkdir(parents=True)
    (vault / "personas" / "sabri" / "00-Identity.md").write_text(
        "---\npersona_id: sabri\n---\n# Sabri\n", encoding="utf-8"
    )
    monkeypatch.setenv("JARVIS_BRAIN_VAULT", str(vault))
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)

    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("sabri", "writer", "Write note X", persist_to_brain=True)
    assert result.ok is True
    assert result.memory_file is not None
    memory_path = Path(result.memory_file)
    assert memory_path.exists()
    text = memory_path.read_text(encoding="utf-8")
    assert "writer" in text
    assert "stub-response-text" in text
    assert "Write note X" in text


def test_persist_flag_off_writes_no_file(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("sabri", "writer", "task", persist_to_brain=False)
    assert result.memory_file is None


# ---------- result shape ----------


def test_result_to_dict_round_trip(fake_registry, persona_loader, stub_llm):
    d = _build(fake_registry, persona_loader, stub_llm)
    result = d.dispatch("sabri", "writer", "task one")
    data = result.to_dict()
    assert data["persona_id"] == "sabri"
    assert data["agent_name"] == "writer"
    assert data["task"] == "task one"
    assert data["ok"] is True
    assert data["model"] == "m1"
    assert "trace" in data


def test_default_dispatcher_reset(monkeypatch):
    from server.subagent_dispatcher import get_dispatcher, reset_dispatcher
    d1 = get_dispatcher()
    d2 = get_dispatcher()
    assert d1 is d2
    reset_dispatcher()
    d3 = get_dispatcher()
    assert d3 is not d1
