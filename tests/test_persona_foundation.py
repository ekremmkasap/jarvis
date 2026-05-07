from __future__ import annotations

import os
import shutil
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"

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
import persona_memory


class TestPersonaFoundation:
    def setup_method(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        self.active_path = self.temp_root / "active_agent.json"
        self.world_path = self.temp_root / "agent_world.json"
        self.memory_dir = self.temp_root / "agent_memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self.persona_patches = [
            patch.object(persona_manager, "ACTIVE_AGENT_PATH", self.active_path),
            patch.object(persona_manager, "AGENT_WORLD_PATH", self.world_path),
            patch.object(persona_manager, "AGENT_MEMORY_DIR", self.memory_dir),
            patch.object(persona_memory, "AGENT_MEMORY_DIR", self.memory_dir),
        ]
        for current_patch in self.persona_patches:
            current_patch.start()

        self.original_active_agents = dict(bridge_module.ACTIVE_AGENTS)
        bridge_module.ACTIVE_AGENTS.clear()

    def teardown_method(self) -> None:
        bridge_module.ACTIVE_AGENTS.clear()
        bridge_module.ACTIVE_AGENTS.update(self.original_active_agents)
        for current_patch in reversed(self.persona_patches):
            current_patch.stop()
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_get_active_persona_returns_non_empty_system_prompt_for_seda(self) -> None:
        persona_manager.switch_persona("seda", lane="web")

        active = persona_manager.get_active_persona(lane="web")

        assert active["id"] == "seda"
        assert active["system_prompt"].strip()

    def test_memory_path_changes_with_persona(self) -> None:
        seda_path = persona_memory.get_memory_path("seda")
        buse_path = persona_memory.get_memory_path("buse")

        assert seda_path != buse_path
        assert seda_path == self.memory_dir / "seda"
        assert buse_path == self.memory_dir / "buse"

    def test_sync_persona_session_populates_active_agent_system_prompt(self) -> None:
        persona_manager.switch_persona("seda", lane="web")

        bridge_module._sync_persona_session_for_chat(bridge_module.WEB_CHAT_ID)

        session = bridge_module.ACTIVE_AGENTS[str(bridge_module.WEB_CHAT_ID)]
        assert session["persona_id"] == "seda"
        assert session["system_prompt"].strip()
        assert "restricted_topics=" in session["system_prompt"]
