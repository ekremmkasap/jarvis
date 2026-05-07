from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from pathlib import Path
from types import MethodType
from unittest.mock import patch


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

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


class PersonaApiEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bridge = importlib.reload(bridge_module)

    def _make_handler(self):
        class _FakeHandler:
            def __init__(self) -> None:
                self.payload = None
                self.status_code = None

            def _json(self, data, code=200):
                self.payload = data
                self.status_code = code

        handler = _FakeHandler()
        handler._handle_personas_endpoint = MethodType(
            self.bridge.WebHandler._handle_personas_endpoint, handler
        )
        return handler

    def test_build_personas_payload_returns_public_personas_by_default(self) -> None:
        with patch.dict(
            os.environ,
            {"JARVIS_DEV_MODE": "", "JARVIS_ADMIN_MODE": ""},
            clear=False,
        ):
            payload = self.bridge._build_personas_payload()

        self.assertIn("personas", payload)
        personas = payload["personas"]
        ids = {item["id"] for item in personas}
        self.assertEqual(
            ids,
            {"sabri", "luna", "buse", "deniz", "eren", "mert", "zeynep"},
        )
        self.assertNotIn("seda", ids)
        self.assertNotIn("sabrican", ids)
        expected_keys = {
            "id",
            "name",
            "role",
            "color",
            "voice",
            "skills",
            "codex_slot",
            "greeting",
        }
        for persona in personas:
            self.assertEqual(set(persona.keys()), expected_keys)

    def test_personas_endpoint_can_include_internal_personas_when_flags_enabled(self) -> None:
        handler = self._make_handler()

        with patch.dict(
            os.environ,
            {"JARVIS_DEV_MODE": "1", "JARVIS_ADMIN_MODE": "1"},
            clear=False,
        ):
            handler._handle_personas_endpoint()

        self.assertEqual(handler.status_code, 200)
        ids = {item["id"] for item in handler.payload["personas"]}
        self.assertIn("seda", ids)
        self.assertIn("sabrican", ids)


if __name__ == "__main__":
    unittest.main()
