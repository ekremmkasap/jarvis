from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


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
import persona_manager
from server.skills import persona_obsidian_skill


class _MemoryStub:
    def __init__(self) -> None:
        self.items: list[tuple[int, str, str, str | None]] = []

    def add_message(
        self, chat_id: int, role: str, content: str, source: str | None = None
    ) -> None:
        self.items.append((chat_id, role, content, source))

    def get_history(self, chat_id: int) -> list[dict[str, str]]:
        return []


class _VoiceManagerStub:
    def get_status(self, chat_id: int) -> SimpleNamespace:
        return SimpleNamespace(active=False)


@pytest.fixture
def persona_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    active_path = tmp_path / "active_agent.json"
    world_path = tmp_path / "agent_world.json"
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", str(vault_dir))
    monkeypatch.setattr(persona_manager, "ACTIVE_AGENT_PATH", active_path)
    monkeypatch.setattr(persona_manager, "AGENT_WORLD_PATH", world_path)

    original_active_agents = dict(bridge_module.ACTIVE_AGENTS)
    bridge_module.ACTIVE_AGENTS.clear()
    try:
        yield vault_dir
    finally:
        bridge_module.ACTIVE_AGENTS.clear()
        bridge_module.ACTIVE_AGENTS.update(original_active_agents)


@pytest.fixture
def bridge_runtime(monkeypatch: pytest.MonkeyPatch) -> _MemoryStub:
    memory = _MemoryStub()
    monkeypatch.setattr(bridge_module, "memory", memory)
    monkeypatch.setattr(
        bridge_module, "get_voice_test_manager", lambda: _VoiceManagerStub()
    )
    monkeypatch.setattr(bridge_module, "INTENT_ENABLED", False)
    monkeypatch.setattr(bridge_module, "should_use_team_mode", lambda text: False)
    monkeypatch.setattr(
        bridge_module, "_dispatch_canonical_message", lambda chat_id, text: None
    )
    monkeypatch.setattr(bridge_module, "get_relevant_knowledge", lambda text: "")
    monkeypatch.setattr(bridge_module, "get_user_context", lambda chat_id: "")
    monkeypatch.setattr(bridge_module, "reme_get_context", lambda text: "")
    monkeypatch.setattr(bridge_module, "reme_save", lambda text, response: None)
    monkeypatch.setattr(bridge_module, "get_selected_candidate", lambda model: str(model))
    return memory


def test_write_persona_note_creates_file_and_ignores_path_traversal(
    persona_state: Path,
) -> None:
    note = persona_obsidian_skill.write_persona_note("mert", "../evil", "icerik")

    assert note is not None
    assert note["title"] == "evil"
    assert note["path"].startswith("personas/mert/")
    assert ".." not in note["path"]
    assert "/" not in Path(note["path"]).name.replace("\\", "/")
    assert (persona_state / note["path"]).exists()


def test_obsidian_helpers_gracefully_fail_without_vault(
    persona_state: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    older = persona_obsidian_skill.write_persona_note("mert", "ilk not", "birinci")
    newer = persona_obsidian_skill.write_persona_note("mert", "son not", "ikinci")

    assert older is not None and newer is not None
    os.utime(persona_state / older["path"], (1_700_000_000, 1_700_000_000))
    os.utime(persona_state / newer["path"], (1_800_000_000, 1_800_000_000))

    notes = persona_obsidian_skill.read_persona_notes("mert")

    assert [note["title"] for note in notes[:2]] == ["son not", "ilk not"]

    monkeypatch.delenv("OBSIDIAN_VAULT_PATH", raising=False)

    assert (
        persona_obsidian_skill.write_persona_note("mert", "env yok", "icerik") is None
    )
    assert persona_obsidian_skill.read_persona_notes("mert") == []
    assert persona_obsidian_skill.get_persona_context("mert") == ""


def test_get_persona_context_formats_recent_notes(persona_state: Path) -> None:
    persona_obsidian_skill.write_persona_note(
        "mert",
        "Arastirma notu",
        "Rakip fiyatlari once premium sonra indirim stratejisi izliyor.",
    )

    context = persona_obsidian_skill.get_persona_context("mert")

    assert context.startswith("[Not: Arastirma notu (")
    assert "Rakip fiyatlari" in context


def test_process_message_handles_obsidian_save_intent(
    persona_state: Path,
    bridge_runtime: _MemoryStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persona_manager.switch_persona("mert", lane="web")
    monkeypatch.setattr(
        bridge_module,
        "_autonomous_maybe_write_obsidian",
        lambda *args, **kwargs: None,
    )

    response = bridge_module.process_message(
        bridge_module.WEB_CHAT_ID,
        "bunu kaydet: Arastirma Notu | Rakip kampanya dili daha agresif.",
    )

    saved_notes = persona_obsidian_skill.read_persona_notes("mert", limit=1)
    assert "Obsidian'a kaydettim (mert):" in response
    assert saved_notes
    assert saved_notes[0]["title"] == "Arastirma Notu"
    assert any(item[3] == "obsidian/save" for item in bridge_runtime.items)


def test_process_message_injects_obsidian_context_into_persona_prompt(
    persona_state: Path,
    bridge_runtime: _MemoryStub,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persona_obsidian_skill.write_persona_note(
        "mert",
        "Gecmis arastirma",
        "Bu not yeni sorguda baglam olarak kullanilmali.",
    )
    persona_manager.switch_persona("mert", lane="web")

    call_mock = Mock(return_value="baglamli cevap")
    monkeypatch.setattr(bridge_module, "call_ollama", call_mock)

    response = bridge_module.process_message(
        bridge_module.WEB_CHAT_ID,
        "bu konuda ne biliyorsun?",
    )

    assert response == "[MERT] baglamli cevap"
    system_prompt = call_mock.call_args.args[2]
    assert "Aktif persona icin Obsidian baglami" in system_prompt
    assert "Gecmis arastirma" in system_prompt


def test_handle_command_ajanlarin_ozeti_lists_latest_notes(
    persona_state: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persona_manager.switch_persona("seda", lane="web")

    memory_skill = SimpleNamespace(
        get_all_agents_summary=lambda: {
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
        },
        format_agents_summary_text=lambda summary: (
            "Aktif persona: seda\n\n"
            "- Seda: last_active=2026-04-14T10:00:00Z | notes=1 | last_note=Kod ozeti\n"
            "- Mert: last_active=henuz aktif degil | notes=0 | last_note=not yok"
        ),
    )
    monkeypatch.setattr(
        bridge_module,
        "_autonomous_load_skill",
        lambda module_name: (
            memory_skill if module_name == "agent_memory_skill" else None
        ),
    )

    result = bridge_module.handle_command(
        bridge_module.WEB_CHAT_ID,
        "/ajanlarin-ozeti",
    )

    assert "Aktif persona: seda" in result
    assert (
        "- Seda: last_active=2026-04-14T10:00:00Z | notes=1 | last_note=Kod ozeti"
        in result
    )
    assert "- Mert: last_active=henuz aktif degil | notes=0 | last_note=not yok" in result
