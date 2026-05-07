from __future__ import annotations

from pathlib import Path


def test_generate_hook_empty_topic_returns_error(tmp_path, monkeypatch):
    from server.skills import buse_content_skill as skill

    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "buse_content.jsonl")
    result = skill.generate_hook("")

    assert result["ok"] is False
    assert result["error"] == "topic_required"


def test_generate_hook_returns_three_variants(tmp_path, monkeypatch):
    from server.skills import buse_content_skill as skill

    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "buse_content.jsonl")
    result = skill.generate_hook("AI asistan", style="linkedin")

    assert result["ok"] is True
    assert len(result["hooks"]) == 3
    assert any("AI asistan" in hook for hook in result["hooks"])


def test_generate_cta_changes_by_platform(tmp_path, monkeypatch):
    from server.skills import buse_content_skill as skill

    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "buse_content.jsonl")
    instagram = skill.generate_cta("comment_bait", "instagram")
    telegram = skill.generate_cta("comment_bait", "telegram")

    assert instagram["ok"] is True
    assert telegram["ok"] is True
    assert instagram["cta"] != telegram["cta"]


def test_content_brief_parses_pipe_format_and_saves(tmp_path, monkeypatch):
    from server.skills import buse_content_skill as skill

    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()
    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "buse_content.jsonl")

    result = skill.content_brief(
        "AI asistan | KOBI sahipleri | comment_bait",
        vault_dir=vault_dir,
    )

    assert result["ok"] is True
    assert result["saved_to"].startswith("personas/buse/content/")
    assert isinstance(result["body_outline"], list) and result["body_outline"]
    saved_file = vault_dir / Path(result["saved_to"])
    assert saved_file.exists()


def test_content_brief_graceful_when_vault_missing(tmp_path, monkeypatch):
    from server.skills import buse_content_skill as skill

    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "buse_content.jsonl")
    result = skill.content_brief(
        "AI asistan",
        "KOBI sahipleri",
        "comment_bait",
        vault_dir=tmp_path / "missing-vault",
    )

    assert result["ok"] is False
    assert "Obsidian" in result["message"]
