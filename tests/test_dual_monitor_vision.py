"""
Tests: Dual Monitor Vision Skill
tests/test_dual_monitor_vision.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

from server.skills.dual_monitor_vision_skill import (
    get_monitor_count,
    handle_vision_command,
    analyze_screen,
)


# ---------------------------------------------------------------------------
# get_monitor_count
# ---------------------------------------------------------------------------

def test_get_monitor_count_returns_positive_int() -> None:
    """En az 1 monitör algılanmalı (mss veya fallback)."""
    count = get_monitor_count()
    assert isinstance(count, int)
    assert count >= 1


# ---------------------------------------------------------------------------
# handle_vision_command — help fallback
# ---------------------------------------------------------------------------

def test_handle_vision_command_unknown_returns_help() -> None:
    msg = handle_vision_command("bilinmiyor", "")
    assert "Dual Monitor Vision" in msg or "monitör" in msg or "ekran" in msg.lower()


def test_handle_vision_command_ekrantara_no_args_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ekran yakalama başarısız olsa da çökmemeli."""
    import server.skills.dual_monitor_vision_skill as skill_module
    monkeypatch.setattr(skill_module, "capture_all_monitors", lambda: [])
    
    result = handle_vision_command("ekrantara", "")
    assert "❌" in result or "yakalanamadı" in result.lower()


def test_handle_vision_command_with_monitor_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """Belirtilen monitör indeksi iletilince analyze_screen doğru parametreyle çağrılmalı."""
    import server.skills.dual_monitor_vision_skill as skill_module
    
    captured: dict = {}
    def fake_analyze(monitor_index=None, prompt="", merge=True):
        captured["index"] = monitor_index
        return "ok"
    
    monkeypatch.setattr(skill_module, "analyze_screen", fake_analyze)
    handle_vision_command("ekrantara", "2")
    assert captured.get("index") == 2


# ---------------------------------------------------------------------------
# analyze_screen — Ollama kapalı → graceful fail
# ---------------------------------------------------------------------------

def test_analyze_screen_ollama_error_graceful(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ollama bağlantısı yoksa bile çökmemeli, hata mesajı dönmeli."""
    import server.skills.dual_monitor_vision_skill as skill_module
    
    # Ekran yakalama → sahte bir dosya dönsün
    fake_png = tmp_path / "fake_screen.png"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # minimal PNG-like
    
    monkeypatch.setattr(skill_module, "capture_all_monitors", lambda: [(1, str(fake_png))])
    monkeypatch.setattr(skill_module, "_analyze_with_ollama", lambda path, prompt: "❌ Ollama bağlantı hatası: test")
    
    result = analyze_screen()
    assert "❌" in result or "Ollama" in result or "Monitör" in result


def test_analyze_screen_no_captures_graceful(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hiç ekran yakalanamadıysa anlamlı hata mesajı döner."""
    import server.skills.dual_monitor_vision_skill as skill_module
    monkeypatch.setattr(skill_module, "capture_all_monitors", lambda: [])
    
    result = analyze_screen()
    assert "yakalanamadı" in result or "❌" in result
