from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from server.skills import persona_obsidian_skill


def test_write_note_uses_persona_folder_and_can_be_recalled(tmp_path, monkeypatch):
    monkeypatch.setattr(
        persona_obsidian_skill,
        "_load_persona_profile",
        lambda persona_id: {
            "id": persona_id,
            "obsidian_folder": f"personas/{persona_id}",
        },
    )

    note = persona_obsidian_skill.write_persona_note(
        "mert",
        "Pazar arastirmasi",
        "Rakiplerin fiyatlama dili daha agresif.",
        vault_dir=tmp_path,
    )

    assert note["path"].startswith("personas/mert/")
    assert (tmp_path / note["path"]).exists()

    recalled = persona_obsidian_skill.recall_persona_notes(
        "mert", "fiyatlama", vault_dir=tmp_path
    )
    assert len(recalled) == 1
    assert recalled[0]["title"] == "Pazar arastirmasi"
    assert (
        persona_obsidian_skill.recall_persona_notes(
            "seda", "fiyatlama", vault_dir=tmp_path
        )
        == []
    )


def test_persona_note_dir_rejects_paths_outside_vault(tmp_path, monkeypatch):
    monkeypatch.setattr(
        persona_obsidian_skill,
        "_load_persona_profile",
        lambda persona_id: {"id": persona_id, "obsidian_folder": "../shared"},
    )

    with pytest.raises(persona_obsidian_skill.UnsafeNotePathError):
        persona_obsidian_skill.persona_note_dir("luna", vault_dir=tmp_path)
