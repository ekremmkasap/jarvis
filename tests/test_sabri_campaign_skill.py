from __future__ import annotations

from pathlib import Path


def _patch_paths(monkeypatch, tmp_path):
    from server.skills import sabri_campaign_skill as skill

    monkeypatch.setattr(skill, "STATE_DIR", tmp_path / "briefs")
    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "sabri_campaign.jsonl")
    return skill


def test_sabri_brief_requires_note(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)

    result = skill.sabri_brief("")
    assert result["ok"] is False
    assert result["error"] == "note_required"


def test_sabri_brief_extracts_fields_and_saves(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)

    result = skill.sabri_brief(
        "Premium bir restoran zinciri için Instagram kampanyası, bütçe 15000 TL, hedef yeni müşteri",
        client_name="Lezzet Durağı",
    )

    assert result["ok"] is True
    assert result["tone"] == "premium"
    assert result["goal"] in {"awareness", "conversion"}
    assert result["budget_try"] == 15000.0
    assert result["brief_id"].startswith("lezzet-durag")  # Turkish chars slugified
    saved_path = (tmp_path / "briefs" / f"{result['brief_id']}.json")
    assert saved_path.exists()


def test_sabri_copy_returns_three_variants_for_valid_brief(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)

    brief = skill.sabri_brief("Gençlik için TikTok kampanyası, satış hedefli", client_name="Acme")
    copy_result = skill.sabri_copy(brief["brief_id"], "tiktok")

    assert copy_result["ok"] is True
    assert copy_result["platform"] == "tiktok"
    assert len(copy_result["variants"]) == 3
    for v in copy_result["variants"]:
        assert {"angle", "headline", "primary", "cta"} <= v.keys()
        assert len(v["headline"]) <= skill.CHAR_LIMITS["tiktok"]["headline"]


def test_sabri_copy_rejects_unknown_platform(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)
    brief = skill.sabri_brief("Test brief", client_name="X")

    result = skill.sabri_copy(brief["brief_id"], "myspace")
    assert result["ok"] is False
    assert result["error"] == "unsupported_platform"


def test_sabri_copy_rejects_missing_brief(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)
    result = skill.sabri_copy("nonexistent_id_123", "meta")
    assert result["ok"] is False
    assert result["error"] == "brief_not_found"


def test_sabri_visual_prompt_returns_three(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)
    brief = skill.sabri_brief("Kurumsal B2B SaaS lead kampanyası", client_name="Acme B2B")

    result = skill.sabri_visual_prompt(brief["brief_id"])
    assert result["ok"] is True
    assert len(result["prompts"]) == 3
    assert all("Acme B2B" in p or "Acme" in p for p in result["prompts"])


def test_sabri_campaign_plan_mix_and_phases(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)
    brief = skill.sabri_brief("Satış odaklı kampanya", client_name="Shop")

    result = skill.sabri_campaign_plan(brief["brief_id"], 10000, 30)
    assert result["ok"] is True
    assert result["budget_try"] == 10000.0
    assert result["duration_days"] == 30
    assert result["channel_mix"]  # non-empty
    total_pct = sum(ch["percent"] for ch in result["channel_mix"])
    assert total_pct == 100
    total_budget = sum(ch["budget_try"] for ch in result["channel_mix"])
    assert abs(total_budget - 10000.0) < 1.0  # rounding tolerance
    assert len(result["phases"]) == 4


def test_sabri_campaign_plan_rejects_invalid_budget(tmp_path, monkeypatch):
    skill = _patch_paths(monkeypatch, tmp_path)
    brief = skill.sabri_brief("Test", client_name="X")

    result = skill.sabri_campaign_plan(brief["brief_id"], "abc", 30)
    assert result["ok"] is False
    assert result["error"] == "invalid_numeric"
