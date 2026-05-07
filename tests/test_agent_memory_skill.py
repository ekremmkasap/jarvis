from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.skills import agent_memory_skill


def _build_registry() -> dict[str, dict[str, str]]:
    return {
        "seda": {
            "id": "seda",
            "name": "Seda",
            "obsidian_folder": "personas/seda",
        },
        "mert": {
            "id": "mert",
            "name": "Mert",
            "obsidian_folder": "personas/mert",
        },
    }


@pytest.fixture
def persona_runtime(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, str]]:
    registry = _build_registry()

    def resolve_persona_name(value: str) -> str | None:
        normalized = str(value or "").strip().lower()
        mapping = {
            "seda": "seda",
            "seda hanim": "seda",
            "kodcu seda": "seda",
            "mert": "mert",
        }
        return mapping.get(normalized)

    monkeypatch.setattr(agent_memory_skill, "load_personas", lambda: registry)
    monkeypatch.setattr(agent_memory_skill, "resolve_persona_name", resolve_persona_name)
    monkeypatch.setattr(agent_memory_skill, "get_active_persona", lambda: {"id": "seda"})
    return registry


def _write_history(
    persona_dir: Path,
    filename: str,
    entries: list[dict[str, str]],
) -> None:
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / filename).write_text(
        "\n".join(json.dumps(entry) for entry in entries),
        encoding="utf-8",
    )


def test_get_persona_memory_resolves_alias_and_reads_latest_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    persona_runtime: dict[str, dict[str, str]],
) -> None:
    seda_dir = tmp_path / "seda"
    _write_history(
        seda_dir,
        "conversation_123.jsonl",
        [
            {
                "timestamp": "2026-04-14T10:00:00Z",
                "role": "user",
                "content": "ilk mesaj",
            },
            {
                "timestamp": "2026-04-14T10:01:00Z",
                "role": "assistant",
                "content": "son mesaj",
            },
        ],
    )

    monkeypatch.setattr(agent_memory_skill, "get_memory_path", lambda persona_id: tmp_path / persona_id)
    monkeypatch.setattr(agent_memory_skill, "get_obsidian_vault_dir", lambda: None)

    snapshot = agent_memory_skill.get_persona_memory("Seda Hanim", limit=1)

    assert snapshot["persona_id"] == "seda"
    assert snapshot["persona_name"] == persona_runtime["seda"]["name"]
    assert snapshot["recent_messages"] == [
        {
            "role": "assistant",
            "content": "son mesaj",
            "ts": "2026-04-14T10:01:00Z",
        }
    ]
    assert snapshot["last_active"] == "2026-04-14T10:01:00Z"
    assert snapshot["message_count"] == 2
    assert snapshot["obsidian_note_count"] == 0
    assert snapshot["last_obsidian_note"] is None


def test_get_persona_memory_unknown_persona_raises_key_error(
    monkeypatch: pytest.MonkeyPatch,
    persona_runtime: dict[str, dict[str, str]],
) -> None:
    monkeypatch.setattr(agent_memory_skill, "get_obsidian_vault_dir", lambda: None)

    with pytest.raises(KeyError):
        agent_memory_skill.get_persona_memory("bilinmeyen")


def test_get_persona_memory_reports_obsidian_note_count_and_last_note(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    persona_runtime: dict[str, dict[str, str]],
) -> None:
    vault_dir = tmp_path / "vault"
    note_dir = vault_dir / "personas" / "seda"
    note_dir.mkdir(parents=True, exist_ok=True)

    older_note = note_dir / "2026-04-13-arastirma.md"
    older_note.write_text("# Arastirma", encoding="utf-8")
    latest_note = note_dir / "2026-04-14-debug-notu.md"
    latest_note.write_text("# Debug", encoding="utf-8")

    older_ts = 1_700_000_000
    latest_ts = 1_800_000_000
    older_note.touch()
    latest_note.touch()
    older_note.stat()
    latest_note.stat()
    import os

    os.utime(older_note, (older_ts, older_ts))
    os.utime(latest_note, (latest_ts, latest_ts))

    monkeypatch.setattr(agent_memory_skill, "get_memory_path", lambda persona_id: tmp_path / "memory" / persona_id)
    monkeypatch.setattr(agent_memory_skill, "get_obsidian_vault_dir", lambda: vault_dir)

    snapshot = agent_memory_skill.get_persona_memory("seda")

    assert snapshot["persona_id"] == "seda"
    assert snapshot["recent_messages"] == []
    assert snapshot["obsidian_note_count"] == 2
    assert snapshot["last_obsidian_note"] == "2026-04-14-debug-notu"


def test_format_persona_memory_text_handles_empty_history() -> None:
    text = agent_memory_skill.format_persona_memory_text(
        {
            "persona_name": "Seda",
            "recent_messages": [],
        }
    )

    assert text == "Seda: henuz konusma gecmisi yok"


def test_get_all_agents_summary_includes_active_persona_and_generated_at(
    monkeypatch: pytest.MonkeyPatch,
    persona_runtime: dict[str, dict[str, str]],
) -> None:
    snapshots = {
        "seda": {
            "persona_id": "seda",
            "persona_name": "Seda",
            "recent_messages": [],
            "last_active": "2026-04-14T10:00:00Z",
            "message_count": 3,
            "last_obsidian_note": "Kod ozeti",
            "obsidian_note_count": 1,
        },
        "mert": {
            "persona_id": "mert",
            "persona_name": "Mert",
            "recent_messages": [],
            "last_active": None,
            "message_count": 0,
            "last_obsidian_note": None,
            "obsidian_note_count": 0,
        },
    }

    monkeypatch.setattr(
        agent_memory_skill,
        "get_persona_memory",
        lambda persona_id, limit=5: snapshots[persona_id],
    )
    monkeypatch.setattr(agent_memory_skill, "get_active_persona", lambda: {"id": "mert"})

    summary = agent_memory_skill.get_all_agents_summary()

    assert summary["active_persona"] == "mert"
    assert [agent["persona_id"] for agent in summary["agents"]] == ["mert", "seda"]
    assert summary["generated_at"].endswith("Z")


def test_format_agents_summary_text_formats_active_persona_and_agent_rows() -> None:
    text = agent_memory_skill.format_agents_summary_text(
        {
            "active_persona": "seda",
            "agents": [
                {
                    "persona_name": "Seda",
                    "last_active": "2026-04-14T10:00:00Z",
                    "obsidian_note_count": 1,
                    "last_obsidian_note": "Kod ozeti",
                },
                {
                    "persona_name": "Mert",
                    "last_active": None,
                    "obsidian_note_count": 0,
                    "last_obsidian_note": None,
                },
            ],
        }
    )

    assert text.startswith("Aktif persona: seda")
    assert (
        "- Seda: last_active=2026-04-14T10:00:00Z | notes=1 | last_note=Kod ozeti"
        in text
    )
    assert "- Mert: last_active=henuz aktif degil | notes=0 | last_note=not yok" in text
