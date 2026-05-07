from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from server import persona_brain
from server.persona_brain import (
    BrainNotInitializedError,
    PersonaBrain,
    UnsafeNotePathError,
    VaultUnavailableError,
    brain_available,
    iter_available_personas,
)


@pytest.fixture
def brain_vault(tmp_path, monkeypatch) -> Path:
    """Build a minimal vault with two persona brains: sabri and luna."""
    monkeypatch.delenv("JARVIS_BRAIN_VAULT", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_DIR", raising=False)
    monkeypatch.delenv("OBSIDIAN_PATH", raising=False)
    monkeypatch.setenv("JARVIS_BRAIN_VAULT", str(tmp_path))

    for pid, name in (("sabri", "Sabri"), ("luna", "Luna")):
        base = tmp_path / "personas" / pid
        (base / "02-Knowledge").mkdir(parents=True)
        (base / "03-Projects").mkdir()
        (base / "04-Memory").mkdir()
        (base / "05-Skills-Refs").mkdir()
        (base / "00-Identity.md").write_text(
            f"---\npersona_id: {pid}\nname: {name}\nrole: test\n---\n\n"
            f"# {name} — Dijital Kimlik\n\nTest identity body.\n",
            encoding="utf-8",
        )
        (base / "01-Daily-Log.md").write_text(
            f"# {name} — Günlük Log\n\n### 2026-04-17 10:00 UTC\n- seed entry\n",
            encoding="utf-8",
        )
        (base / "02-Knowledge" / "marka-dna.md").write_text(
            "# Marka DNA\n\nMarka fiyatlama dili ve ton rehberi.\n",
            encoding="utf-8",
        )
    return tmp_path


def test_iter_available_personas_lists_folders(brain_vault: Path) -> None:
    personas = list(iter_available_personas())
    assert personas == ["luna", "sabri"]


def test_brain_available_true_for_seeded_persona(brain_vault: Path) -> None:
    assert brain_available("sabri") is True
    assert brain_available("unknown_persona_999") is False


def test_init_raises_when_vault_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("JARVIS_BRAIN_VAULT", raising=False)
    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)
    monkeypatch.setenv("JARVIS_BRAIN_VAULT", str(tmp_path / "does_not_exist"))
    with pytest.raises(VaultUnavailableError):
        PersonaBrain("sabri")


def test_init_raises_when_persona_folder_missing(brain_vault: Path) -> None:
    with pytest.raises(BrainNotInitializedError):
        PersonaBrain("ghost_persona")


def test_identity_reads_frontmatter(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    ident = b.identity()
    assert ident["persona_id"] == "sabri"
    assert ident["frontmatter"].get("name") == "Sabri"
    assert ident["frontmatter"].get("role") == "test"
    assert any("Dijital Kimlik" in line for line in ident["body_preview"])


def test_daily_log_append_and_tail(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    before = b.read_daily_log(tail=50)
    b.append_daily_log("- first appended entry")
    b.append_daily_log("- second appended entry")
    after = b.read_daily_log(tail=50)
    joined = "\n".join(after)
    assert "first appended entry" in joined
    assert "second appended entry" in joined
    assert len(after) > len(before)


def test_memory_write_creates_dated_file(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    path = b.write_memory("telegram turn", "kullanıcı reklam brief istedi", channel="telegram")
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "telegram turn" in text
    assert "_channel: telegram_" in text
    assert "kullanıcı reklam brief istedi" in text


def test_memory_append_same_day_keeps_previous(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    b.write_memory("first turn", "alpha content")
    b.write_memory("second turn", "beta content")
    days = b.list_memory_days()
    assert len(days) == 1
    file_path = brain_vault / "personas" / "sabri" / "04-Memory" / f"{days[0]}.md"
    body = file_path.read_text(encoding="utf-8")
    assert "alpha content" in body
    assert "beta content" in body


def test_memory_isolation_between_personas(brain_vault: Path) -> None:
    sabri = PersonaBrain("sabri")
    luna = PersonaBrain("luna")
    sabri.write_memory("sabri secret", "only sabri should see this")
    luna.write_memory("luna recon", "osint finding")

    sabri_memdir = brain_vault / "personas" / "sabri" / "04-Memory"
    luna_memdir = brain_vault / "personas" / "luna" / "04-Memory"

    sabri_blob = "\n".join(p.read_text(encoding="utf-8") for p in sabri_memdir.glob("*.md"))
    luna_blob = "\n".join(p.read_text(encoding="utf-8") for p in luna_memdir.glob("*.md"))

    assert "only sabri should see this" in sabri_blob
    assert "only sabri should see this" not in luna_blob
    assert "osint finding" in luna_blob
    assert "osint finding" not in sabri_blob


def test_path_traversal_persona_id_is_sanitized(brain_vault: Path) -> None:
    with pytest.raises(BrainNotInitializedError):
        PersonaBrain("../../etc/passwd")


def test_empty_memory_topic_rejected(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    with pytest.raises(ValueError):
        b.write_memory("  ", "content here")


def test_empty_memory_content_rejected(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    with pytest.raises(ValueError):
        b.write_memory("topic", "   ")


def test_search_knowledge_finds_term_case_insensitive(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    hits = b.search_knowledge("MARKA")
    assert hits
    assert "marka-dna.md" in hits[0]["path"]
    assert hits[0]["matches"]


def test_search_knowledge_empty_query_returns_nothing(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    assert b.search_knowledge("") == []
    assert b.search_knowledge("   ") == []


def test_search_knowledge_skips_readme(brain_vault: Path) -> None:
    b = PersonaBrain("luna")
    (brain_vault / "personas" / "luna" / "02-Knowledge" / "README.md").write_text(
        "# README\n\nscan keyword here\n", encoding="utf-8"
    )
    hits = b.search_knowledge("scan keyword")
    assert hits == []


def test_list_projects_returns_md_only(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    projects_dir = brain_vault / "personas" / "sabri" / "03-Projects"
    (projects_dir / "campaign-alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (projects_dir / "campaign-beta.md").write_text("# Beta\n", encoding="utf-8")
    (projects_dir / "README.md").write_text("# readme\n", encoding="utf-8")
    (projects_dir / "notes.txt").write_text("ignored\n", encoding="utf-8")
    names = [p["name"] for p in b.list_projects()]
    assert names == ["campaign-alpha", "campaign-beta"]


def test_snapshot_returns_aggregated_state(brain_vault: Path) -> None:
    b = PersonaBrain("sabri")
    b.write_memory("turn 1", "content one")
    b.append_daily_log("- new decision")
    snap = b.snapshot()
    d = snap.to_dict()
    assert d["persona_id"] == "sabri"
    assert d["memory_days"] == 1
    assert d["knowledge_count"] == 1
    assert d["last_memory_file"] is not None
    assert any("new decision" in line for line in d["daily_log_tail"])


def test_vault_env_precedence_brain_wins_over_obsidian(tmp_path, monkeypatch) -> None:
    brain_dir = tmp_path / "brain"
    (brain_dir / "personas" / "sabri").mkdir(parents=True)
    (brain_dir / "personas" / "sabri" / "00-Identity.md").write_text("---\n---\n# Sabri", encoding="utf-8")

    obsidian_dir = tmp_path / "obsidian"
    obsidian_dir.mkdir()

    monkeypatch.setenv("JARVIS_BRAIN_VAULT", str(brain_dir))
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(obsidian_dir))

    b = PersonaBrain("sabri")
    assert b.vault_root == brain_dir.resolve()


def test_explicit_vault_arg_overrides_env(tmp_path, monkeypatch) -> None:
    arg_dir = tmp_path / "explicit"
    (arg_dir / "personas" / "sabri").mkdir(parents=True)
    (arg_dir / "personas" / "sabri" / "00-Identity.md").write_text("---\n---\n# Sabri", encoding="utf-8")

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.setenv("JARVIS_BRAIN_VAULT", str(other_dir))

    b = PersonaBrain("sabri", vault_dir=arg_dir)
    assert b.vault_root == arg_dir.resolve()
