from __future__ import annotations

import os
import sys
import types
import io
import json
from pathlib import Path


REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

os.environ.setdefault("JARVIS_ENABLE_TELEGRAM", "0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")

if "telegram" not in sys.modules:
    telegram_package = types.ModuleType("telegram")
    telegram_intelligence_module = types.ModuleType("telegram.telegram_intelligence")

    class _DummyTelegramIntelligence:
        def __init__(self, *args, **kwargs) -> None:
            pass

    telegram_intelligence_module.TelegramIntelligence = _DummyTelegramIntelligence
    telegram_package.telegram_intelligence = telegram_intelligence_module
    sys.modules["telegram"] = telegram_package
    sys.modules["telegram.telegram_intelligence"] = telegram_intelligence_module

import bridge as bridge_module


class _FakeDesktopSkill:
    def handle_desktop_command(self, command: str, args: str) -> str:
        return f"desktop-command:{command}:{args}"

    def handle_note_intent(self, text: str, persona_id: str = "jarvis") -> str | None:
        if "yaz" not in text:
            return None
        return f"desktop-intent:{persona_id}:{text}"


def test_bridge_handle_command_routes_desktop_io(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_DESKTOP_IO_HANDLE_COMMAND",
        lambda chat_id, cmd: "fallback-command",
    )
    monkeypatch.setattr(
        bridge_module,
        "_load_desktop_io_bridge_skill",
        lambda: _FakeDesktopSkill(),
    )

    result = bridge_module.handle_command(101, "/notyaz deneme.txt|icerik")

    assert result == "desktop-command:/notyaz:deneme.txt|icerik"


def test_bridge_process_message_routes_desktop_intent(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_DESKTOP_IO_PROCESS_MESSAGE",
        lambda chat_id, text: "fallback-process",
    )
    monkeypatch.setattr(
        bridge_module,
        "_load_desktop_io_bridge_skill",
        lambda: _FakeDesktopSkill(),
    )
    monkeypatch.setattr(
        bridge_module,
        "_get_active_persona_payload",
        lambda chat_id=None, lane=None: {"id": "seda"},
    )

    result = bridge_module.process_message(102, "şunu yaz: toplanti notu")

    assert result == "desktop-intent:seda:şunu yaz: toplanti notu"


def test_bridge_process_message_keeps_normal_flow(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_DESKTOP_IO_PROCESS_MESSAGE",
        lambda chat_id, text: "fallback-process",
    )
    monkeypatch.setattr(
        bridge_module,
        "_load_desktop_io_bridge_skill",
        lambda: _FakeDesktopSkill(),
    )

    result = bridge_module.process_message(103, "bugun hava guzel")

    assert result == "fallback-process"


def test_bridge_status_check_telegram(monkeypatch) -> None:
    monkeypatch.setitem(bridge_module.CONFIG, "enable_telegram", True)

    result = bridge_module.handle_command(104, "/status_check Telegram bridge connection")

    assert "Telegram bridge aktif" in result


def test_bridge_status_check_obsidian(monkeypatch, tmp_path: Path) -> None:
    def _fake_vault():
        return tmp_path

    monkeypatch.setattr(bridge_module, "_ORIGINAL_STATUS_CHECK_HANDLE_COMMAND", lambda chat_id, cmd: "fallback-status")
    import server.skills.obsidian_sync_skill as obsidian_sync_skill
    monkeypatch.setattr(obsidian_sync_skill, "get_obsidian_vault_dir", _fake_vault)

    result = bridge_module.handle_command(105, "/status_check Obsidian connection")

    assert "Obsidian baglantisi aktif" in result


def test_bridge_command_endpoint_keeps_string_args(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def _fake_handle_command(chat_id: int, cmd: str) -> str:
        captured["chat_id"] = chat_id
        captured["cmd"] = cmd
        return "ok"

    monkeypatch.setattr(bridge_module, "handle_command", _fake_handle_command)

    body = json.dumps(
        {
            "command": "/status_check",
            "args": "Telegram bridge connection",
            "chat_id": "77",
        }
    ).encode("utf-8")

    class _FakeHandler:
        path = "/command"

        def __init__(self) -> None:
            self.headers = {"Content-Length": str(len(body))}
            self.rfile = io.BytesIO(body)
            self.response: tuple[int, dict[str, object]] | None = None

        def _json(self, payload: dict[str, object], status: int = 200) -> None:
            self.response = (status, payload)

    handler = _FakeHandler()
    bridge_module.WebHandler.do_POST(handler)

    assert captured == {"chat_id": 77, "cmd": "/status_check Telegram bridge connection"}
    assert handler.response == (200, {"ok": True, "result": "ok"})


def test_bridge_handle_command_opens_obsidian(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_OBSIDIAN_OPEN_HANDLE_COMMAND",
        lambda chat_id, cmd: "fallback-open",
    )
    monkeypatch.setattr(
        bridge_module,
        "_open_obsidian_from_bridge",
        lambda: "Obsidian aciliyor. Vault: C:/vault",
    )

    result = bridge_module.handle_command(106, "/obsidian-ac")

    assert result == "Obsidian aciliyor. Vault: C:/vault"


def test_bridge_handle_command_obsidian_save_uses_lane_persona(monkeypatch) -> None:
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_LANE_AWARE_OBSIDIAN_HANDLE_COMMAND",
        lambda chat_id, cmd: "fallback-obsidian-save",
    )
    monkeypatch.setattr(
        bridge_module,
        "_get_active_persona_payload",
        lambda chat_id=None, lane=None: {"id": "jarvis"},
    )

    import server.skills.persona_obsidian_skill as persona_obsidian_skill

    def _fake_write_persona_note(persona_id: str, title: str, content: str):
        captured["persona_id"] = persona_id
        captured["title"] = title
        captured["content"] = content
        return {"path": f"personas/{persona_id}/test.md"}

    monkeypatch.setattr(
        persona_obsidian_skill,
        "write_persona_note",
        _fake_write_persona_note,
    )

    result = bridge_module.handle_command(
        bridge_module.VOICE_CHAT_ID,
        "/obsidian-kaydet Merkezi Beyin | kalici not",
    )

    assert captured == {
        "persona_id": "jarvis",
        "title": "Merkezi Beyin",
        "content": "kalici not",
    }
    assert result == "Obsidian'a kaydedildi (jarvis): Merkezi Beyin"


def test_bridge_handle_command_obsidian_read_uses_lane_persona(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_LANE_AWARE_OBSIDIAN_HANDLE_COMMAND",
        lambda chat_id, cmd: "fallback-obsidian-read",
    )
    monkeypatch.setattr(
        bridge_module,
        "_get_active_persona_payload",
        lambda chat_id=None, lane=None: {"id": "jarvis"},
    )

    import server.skills.persona_obsidian_skill as persona_obsidian_skill

    monkeypatch.setattr(
        persona_obsidian_skill,
        "recall_persona_notes",
        lambda persona_id, query: [{"persona_id": persona_id, "title": query}],
    )

    result = bridge_module.handle_command(
        bridge_module.VOICE_CHAT_ID,
        "/obsidian-oku toplanti",
    )

    assert "*jarvis notlari (toplanti):*" in result
    assert '"persona_id": "jarvis"' in result
