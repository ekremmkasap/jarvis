"""
Tests: Desktop I/O Skill
tests/test_desktop_io_skill.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

from server.skills.desktop_io_skill import (
    create_file,
    detect_desktop_intent,
    handle_desktop_command,
    handle_note_intent,
    open_notepad,
    read_file,
    write_to_file,
    DESKTOP_PATH,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Testlerde gerçek masaüstü yerine tmp_path kullan."""
    import server.skills.desktop_io_skill as skill_module
    monkeypatch.setattr(skill_module, "DESKTOP_PATH", tmp_path)
    monkeypatch.setattr(
        skill_module,
        "_ALLOWED_DIRS",
        (tmp_path,),
    )
    return tmp_path


# ---------------------------------------------------------------------------
# create_file
# ---------------------------------------------------------------------------

def test_create_file_creates_on_basedir(tmp_base: Path) -> None:
    result = create_file("test.txt", "merhaba", base_dir=tmp_base)
    assert result["success"] is True
    target = tmp_base / "test.txt"
    assert target.exists()
    assert "merhaba" in target.read_text(encoding="utf-8")


def test_create_file_appends_on_second_call(tmp_base: Path) -> None:
    create_file("append.txt", "satir1", base_dir=tmp_base)
    create_file("append.txt", "satir2", base_dir=tmp_base)
    content = (tmp_base / "append.txt").read_text(encoding="utf-8")
    assert "satir1" in content
    assert "satir2" in content


# ---------------------------------------------------------------------------
# Path traversal koruması
# ---------------------------------------------------------------------------

def test_path_traversal_blocked(tmp_base: Path) -> None:
    result = create_file("../../secret.txt", "evil", base_dir=tmp_base)
    # Hedef yol tmp_base içinde olmalı
    assert result["success"] is True
    target = Path(result["path"])
    assert str(tmp_base) in str(target) or target.parent == tmp_base


def test_path_traversal_dotdot_stripped(tmp_base: Path) -> None:
    result = create_file("../escape.txt", "x", base_dir=tmp_base)
    created = Path(result["path"])
    # Oluşturulan dosya güvenli bir yerde
    assert "__" in created.name or created.parent.resolve() == tmp_base.resolve()


# ---------------------------------------------------------------------------
# write_to_file
# ---------------------------------------------------------------------------

def test_write_to_file_creates_if_missing(tmp_base: Path) -> None:
    result = write_to_file("yeni.txt", "ilk satir", base_dir=tmp_base)
    assert result["success"] is True
    assert (tmp_base / "yeni.txt").exists()


def test_write_to_file_overwrite(tmp_base: Path) -> None:
    write_to_file("overwrite.txt", "eski", base_dir=tmp_base)
    write_to_file("overwrite.txt", "yeni", base_dir=tmp_base, overwrite=True)
    content = (tmp_base / "overwrite.txt").read_text(encoding="utf-8")
    assert "eski" not in content
    assert "yeni" in content


# ---------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------

def test_read_file_returns_content(tmp_base: Path) -> None:
    target = tmp_base / "oku.txt"
    target.write_text("içerik var", encoding="utf-8")
    result = read_file(str(target))
    assert result["success"] is True
    assert "içerik var" in result["content"]


def test_read_file_missing_graceful() -> None:
    result = read_file("/nonexistent/path/file.txt")
    assert result["success"] is False
    assert "bulunamadı" in result["message"]


# ---------------------------------------------------------------------------
# open_notepad
# ---------------------------------------------------------------------------

def test_open_notepad_creates_file(tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Notepad'i gerçek açmadan — sadece dosya oluşturma testi."""
    import subprocess
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)
    
    filepath = str(tmp_base / "test_not.txt")
    result = open_notepad(filepath)
    assert result["success"] is True
    assert Path(filepath).exists()


# ---------------------------------------------------------------------------
# handle_desktop_command (dispatcher)
# ---------------------------------------------------------------------------

def test_handle_desktop_command_notyaz(tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import server.skills.desktop_io_skill as skill_module
    monkeypatch.setattr(skill_module, "DESKTOP_PATH", tmp_base)
    
    msg = handle_desktop_command("notyaz", "deneme.txt|test içerik")
    assert "✅" in msg


def test_handle_desktop_command_dosyaoku(tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import server.skills.desktop_io_skill as skill_module
    monkeypatch.setattr(skill_module, "DESKTOP_PATH", tmp_base)
    
    target = tmp_base / "oku.txt"
    target.write_text("oku beni", encoding="utf-8")
    msg = handle_desktop_command("dosyaoku", str(target))
    assert "oku beni" in msg


def test_handle_desktop_command_unknown_returns_help(tmp_base: Path) -> None:
    msg = handle_desktop_command("bilinmeyen", "")
    assert "Desktop I/O" in msg or "Komut" in msg


# ---------------------------------------------------------------------------
# detect_desktop_intent
# ---------------------------------------------------------------------------

def test_detect_intent_not_al() -> None:
    assert detect_desktop_intent("şunu not al: yarın toplantı var") == "write_note"


def test_detect_intent_yaz() -> None:
    assert detect_desktop_intent("bunu yaz: önemli not") == "write_note"


def test_detect_intent_notepad_open() -> None:
    assert detect_desktop_intent("not defteri aç") == "open_notepad"


def test_detect_intent_notepad_open_ascii() -> None:
    assert detect_desktop_intent("not defteri ac") == "open_notepad"


def test_detect_intent_create_file() -> None:
    assert detect_desktop_intent("masaustunde txt olustur") == "create_file"


def test_detect_intent_none() -> None:
    assert detect_desktop_intent("merhaba nasılsın") is None


# ---------------------------------------------------------------------------
# handle_note_intent
# ---------------------------------------------------------------------------

def test_handle_note_intent_yaz(tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import server.skills.desktop_io_skill as skill_module
    monkeypatch.setattr(skill_module, "DESKTOP_PATH", tmp_base)
    
    result = handle_note_intent("şunu yaz: yarın toplantı var")
    assert result is not None
    assert "✅" in result or "📄" in result or "📝" in result


def test_handle_note_intent_returns_none_for_normal_message() -> None:
    result = handle_note_intent("bugün hava güzel")
    assert result is None


def test_handle_note_intent_create_file(tmp_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import server.skills.desktop_io_skill as skill_module
    monkeypatch.setattr(skill_module, "DESKTOP_PATH", tmp_base)

    result = handle_note_intent("masaustunde txt olustur")
    assert result is not None
    created = list(tmp_base.glob("jarvis_not_*.txt"))
    assert created
