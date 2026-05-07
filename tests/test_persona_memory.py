from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

import persona_memory


def test_append_turn_writes_persona_scoped_conversation_file(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_memory, "AGENT_MEMORY_DIR", tmp_path / "agent_memory")

    entry = persona_memory.append_turn(
        "Seda",
        42,
        "assistant",
        "Auth tarafinda null guard eksik.",
        source="bridge/openrouter",
    )

    target = tmp_path / "agent_memory" / "seda" / "conversation_42.jsonl"
    assert target.exists()
    assert entry["persona_id"] == "seda"
    assert entry["chat_id"] == "42"


def test_get_history_returns_role_content_pairs(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_memory, "AGENT_MEMORY_DIR", tmp_path / "agent_memory")

    persona_memory.append_turn("buse", "web-main", "user", "Landing fikri ver")
    persona_memory.append_turn(
        "buse",
        "web-main",
        "assistant",
        "Hero metninde tek teklif kalsin.",
    )

    history = persona_memory.get_history("buse", "web-main")

    assert history == [
        {"role": "user", "content": "Landing fikri ver"},
        {"role": "assistant", "content": "Hero metninde tek teklif kalsin."},
    ]


def test_load_turns_ignores_invalid_json_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(persona_memory, "AGENT_MEMORY_DIR", tmp_path / "agent_memory")
    target = persona_memory.conversation_path("mert", 7)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "not-json\n"
        '{"timestamp":"2026-04-13T00:00:00+00:00","chat_id":"7","persona_id":"mert","role":"user","content":"Pazar trendi"}\n',
        encoding="utf-8",
    )

    turns = persona_memory.load_turns("mert", 7)

    assert len(turns) == 1
    assert turns[0]["content"] == "Pazar trendi"
