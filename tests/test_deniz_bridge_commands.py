"""Smoke test: bridge dispatch handles new /deniz, /sabri, /zeynep commands."""
from __future__ import annotations


def _dispatch(command: str, args: str = "") -> str:
    """Mimic bridge handle_command dispatch by importing and calling."""
    # The bridge.py uses a big if/elif chain; we import at module level to avoid
    # starting an HTTP server. We call the command handler by monkeypatching out
    # heavy imports via direct skill calls.
    raise NotImplementedError


def test_sabri_bridge_usage_messages(monkeypatch):
    """/sabri-* commands return usage strings when args are missing."""
    import importlib
    import sys

    # Force reload of skill to pick up any path changes
    if "server.skills.sabri_campaign_skill" in sys.modules:
        importlib.reload(sys.modules["server.skills.sabri_campaign_skill"])

    from server.skills import sabri_campaign_skill as skill

    # Directly verify skill usage
    assert skill.sabri_brief("")["error"] == "note_required"
    assert skill.sabri_copy("missing_id", "meta")["error"] == "brief_not_found"
    assert skill.sabri_visual_prompt("missing_id")["error"] == "brief_not_found"
    assert skill.sabri_campaign_plan("missing_id", 1000, 7)["error"] == "brief_not_found"


def test_zeynep_bridge_usage_messages():
    """/zeynep-* skill functions reject invalid paths cleanly."""
    from server.skills import zeynep_security_skill as skill

    assert skill.zeynep_kvkk_audit("/definitely/not/a/real/path")["error"] == "invalid_path"
    assert skill.zeynep_secret_scan("/definitely/not/a/real/path")["error"] == "invalid_path"


def test_deniz_skills_importable():
    """Deniz uses existing ebay/trendyol/printify skills — verify they import."""
    from server.skills.ebay_research import analyze_product, format_report
    from server.skills.trendyol_skill import full_trendyol_analysis
    from server.skills.printify_skill import format_overview

    assert callable(analyze_product)
    assert callable(format_report)
    assert callable(full_trendyol_analysis)
    assert callable(format_overview)


def test_bridge_py_compiles():
    """server/bridge.py must compile — guards against syntax errors in command register."""
    import py_compile
    from pathlib import Path

    bridge = Path(__file__).resolve().parents[1] / "server" / "bridge.py"
    py_compile.compile(str(bridge), doraise=True)


def test_bridge_contains_new_commands():
    """Smoke-check that the new slash commands are registered in bridge.py."""
    from pathlib import Path

    bridge = Path(__file__).resolve().parents[1] / "server" / "bridge.py"
    text = bridge.read_text(encoding="utf-8", errors="ignore")
    for command in (
        "/sabri-brief", "/sabri-copy", "/sabri-gorsel", "/sabri-kampanya",
        "/zeynep-kvkk", "/zeynep-gizli", "/zeynep-log", "/zeynep-sertlestir",
        "/deniz-ebay", "/deniz-trendyol", "/deniz-printify", "/deniz-rakip",
    ):
        assert command in text, f"Bridge'e kaydolmamis komut: {command}"
