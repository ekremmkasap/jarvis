from pathlib import Path

from server.skills import obsidian_auto_writer


def test_auto_write_research_writes_persona_note(tmp_path, monkeypatch):
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(tmp_path))

    result = obsidian_auto_writer.auto_write_research(
        "mert",
        "eBay fiyat analizi",
        "Rakipler premium fiyatla acilis yapiyor.",
    )

    assert result is not None
    assert result["ok"] is True
    assert result["persona_id"] == "mert"
    assert result["path"].startswith("personas/mert/")
    note_path = tmp_path / result["path"]
    assert note_path.exists()
    content = note_path.read_text(encoding="utf-8")
    assert "## Sorgu" in content
    assert "eBay fiyat analizi" in content
    assert "## Sonuc" in content
    assert "Rakipler premium fiyatla acilis yapiyor." in content


def test_auto_write_research_gracefully_fails_without_vault(monkeypatch):
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)

    result = obsidian_auto_writer.auto_write_research(
        "mert",
        "test sorgu",
        "test sonuc",
    )

    assert result is None


def test_auto_write_pc_action_writes_into_actions_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(obsidian_auto_writer, "get_obsidian_vault_dir", lambda: tmp_path)

    result = obsidian_auto_writer.auto_write_pc_action(
        "ac",
        "chrome acildi",
        args="chrome",
    )

    assert result is not None
    assert result["ok"] is True
    assert result["persona_id"] == "sabrican"
    assert result["path"].replace("\\", "/").startswith("personas/sabrican/actions/")
    note_path = tmp_path / Path(result["path"])
    assert note_path.exists()
    body = note_path.read_text(encoding="utf-8")
    assert "## Komut" in body
    assert "ac" in body
    assert "## Arguman" in body
    assert "chrome" in body
    assert "## Sonuc" in body
    assert "chrome acildi" in body


def test_auto_write_pc_action_gracefully_fails_without_vault(monkeypatch):
    monkeypatch.setattr(obsidian_auto_writer, "get_obsidian_vault_dir", lambda: None)

    result = obsidian_auto_writer.auto_write_pc_action(
        "ac",
        "chrome acildi",
        args="chrome",
    )

    assert result is None
