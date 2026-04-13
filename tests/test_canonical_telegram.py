from __future__ import annotations

import importlib
import os
import sys
import types
import unittest
from pathlib import Path


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


class CanonicalTelegramRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_env = os.environ.copy()
        os.environ["JARVIS_ENABLE_TELEGRAM"] = "0"
        os.environ["TELEGRAM_BOT_TOKEN"] = ""
        os.environ["TELEGRAM_CHAT_ID"] = "0"
        cls.bridge = importlib.reload(bridge_module)

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.clear()
        os.environ.update(cls.original_env)

    def test_plan_yap_routes_to_planner(self) -> None:
        self.assertEqual(self.bridge._detect_agent_from_text("Lutfen plan yap"), "planner")

    def test_hata_var_routes_to_debug(self) -> None:
        self.assertEqual(self.bridge._detect_agent_from_text("Sistemde hata var, debug et"), "debug")

    def test_unknown_keyword_returns_none(self) -> None:
        self.assertIsNone(self.bridge._detect_agent_from_text("bugun hava guzel"))

    def test_run_canonical_agent_wraps_planner_success(self) -> None:
        result = self.bridge._run_canonical_agent("planner", "Jarvis test plani yap", {})

        self.assertTrue(result["ok"])
        self.assertEqual(result["agent"], "planner")
        self.assertTrue(result["result"])

    def test_agents_health_payload_reports_all_canonical_agents(self) -> None:
        payload = self.bridge._build_agents_health_payload()

        self.assertEqual(payload["total"], 9)
        self.assertEqual(payload["healthy"], 9)
        self.assertEqual(len(payload["agents"]), 9)
        self.assertTrue(all(item["status"] == "ok" for item in payload["agents"]))


if __name__ == "__main__":
    unittest.main()
