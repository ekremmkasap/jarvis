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


class _FakeHandler:
    def __init__(self) -> None:
        self.payload = None
        self.status_code = None

    def _json(self, payload, status_code=200) -> None:
        self.payload = payload
        self.status_code = status_code


class TestPersonaUS1:
    def setup_method(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        self.active_path = self.temp_root / "active_agent.json"
        self.world_path = self.temp_root / "agent_world.json"
        # seda is gated behind JARVIS_DEV_MODE; enable it so switch_persona resolves
        # instead of falling back to the stripped default jarvis persona.
        self.env_patch = patch.dict(os.environ, {"JARVIS_DEV_MODE": "1"}, clear=False)
        self.env_patch.start()
        self.patches = [
            patch.object(persona_manager, "ACTIVE_AGENT_PATH", self.active_path),
            patch.object(persona_manager, "AGENT_WORLD_PATH", self.world_path),
        ]
        for current_patch in self.patches:
            current_patch.start()

    def teardown_method(self) -> None:
        for current_patch in reversed(self.patches):
            current_patch.stop()
        self.env_patch.stop()
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_seda_prompt_is_technical(self) -> None:
        persona_manager.switch_persona("seda", lane="web")

        active = persona_manager.get_active_persona(lane="web")
        prompt = str(active.get("system_prompt") or active.get("prompt") or "").lower()

        assert active["id"] == "seda"
        assert "python" in prompt or "typescript" in prompt or "debug" in prompt

    def test_buse_prompt_differs_and_has_fallback_guidance(self) -> None:
        persona_manager.switch_persona("seda", lane="web")
        seda_prompt = bridge_module._build_persona_system_prompt(
            persona_manager.get_active_persona(lane="web")
        )

        persona_manager.switch_persona("buse", lane="web")
        buse = persona_manager.get_active_persona(lane="web")
        buse_prompt = bridge_module._build_persona_system_prompt(buse)

        assert buse["id"] == "buse"
        assert buse_prompt != seda_prompt
        lowered = buse_prompt.lower()
        assert any(term in lowered for term in ("sosyal", "instagram", "reels", "hashtag"))
        assert "fallback_persona=sabri" in buse_prompt

    def test_active_persona_endpoint_returns_expected_schema(self) -> None:
        persona_manager.switch_persona("buse", lane="web")
        handler = _FakeHandler()

        bridge_module.WebHandler._handle_persona_active_endpoint(
            handler,
            query={"lane": ["web"], "chatId": [str(bridge_module.WEB_CHAT_ID)]},
        )

        assert handler.status_code == 200
        assert isinstance(handler.payload, dict)
        for key in (
            "id",
            "name",
            "color",
            "voice",
            "role",
            "skills",
            "greeting",
            "activated_at",
        ):
            assert key in handler.payload
        assert handler.payload["id"] == "buse"
        assert handler.payload["name"] == "Buse"
