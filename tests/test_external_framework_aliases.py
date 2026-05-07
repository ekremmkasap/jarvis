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

import skills.crewai_skill as crewai_skill
import skills.upondhand_skill as upondhand_skill


class ExternalFrameworkSkillTests(unittest.TestCase):
    def test_crewai_status_mentions_expected_install_requirements(self) -> None:
        result = crewai_skill.run_crewai("durum")

        self.assertIn("CrewAI durum", result)
        self.assertIn("external-repos/crewAI", result)
        self.assertIn('crewai==0.28.8', result)
        self.assertIn("langchain-google-genai>=0.0.9", result)
        self.assertIn("Python: 3.11 uyumlu", result)

    def test_upondhand_status_reports_repo_and_runtime_paths(self) -> None:
        result = upondhand_skill.run_upondhand("durum")

        self.assertIn("upondhand durum", result)
        self.assertIn("external-repos/OpenHands", result)
        self.assertIn("openhands/workspace", result)
        self.assertIn("openhands/config.toml", result)


class ExternalRepoRegistryTests(unittest.TestCase):
    def test_external_repo_search_returns_openhands_entry(self) -> None:
        from services.external_repo_registry import build_external_repo_report

        result = build_external_repo_report("openhands")

        self.assertIn("EXTERNAL REPO ARAMA", result)
        self.assertIn("OpenHands", result)
        self.assertIn("external-repos/OpenHands", result)

    def test_external_repo_search_returns_octogent_entry(self) -> None:
        from services.external_repo_registry import build_external_repo_report

        result = build_external_repo_report("octogent")

        self.assertIn("EXTERNAL REPO ARAMA", result)
        self.assertIn("Octogent", result)
        self.assertIn("external-repos/octogent", result)

    def test_external_repo_recommendation_uses_youtube_stack(self) -> None:
        from services.external_repo_registry import (
            build_external_repo_recommendation_report,
        )

        result = build_external_repo_recommendation_report("youtube transcript cek")

        self.assertIn("REPO ONERI", result)
        self.assertIn("MCP / Ingestion", result)
        self.assertTrue(
            "YouTube Transcript API" in result
            or "MCP YouTube Transcript" in result
            or "YouTube MCP Server" in result
        )


class BridgeAliasCommandTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_env = os.environ.copy()
        cls.original_telegram_module = sys.modules.get("telegram")
        cls.original_telegram_intelligence_module = sys.modules.get("telegram.telegram_intelligence")
        os.environ["JARVIS_ENABLE_TELEGRAM"] = "0"
        os.environ["TELEGRAM_BOT_TOKEN"] = ""
        os.environ["TELEGRAM_CHAT_ID"] = "0"

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

        cls.bridge = importlib.reload(bridge_module)

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.clear()
        os.environ.update(cls.original_env)
        if cls.original_telegram_module is None:
            sys.modules.pop("telegram", None)
        else:
            sys.modules["telegram"] = cls.original_telegram_module
        if cls.original_telegram_intelligence_module is None:
            sys.modules.pop("telegram.telegram_intelligence", None)
        else:
            sys.modules["telegram.telegram_intelligence"] = cls.original_telegram_intelligence_module

    def test_bridge_crewai_alias_returns_status(self) -> None:
        result = self.bridge.handle_command(100, "/crewai durum")

        self.assertIn("CrewAI durum", result)
        self.assertIn("crewai==0.28.8", result)

    def test_bridge_upondhand_alias_returns_repo_path(self) -> None:
        result = self.bridge.handle_command(100, "/upondhand durum")

        self.assertIn("upondhand durum", result)
        self.assertIn("external-repos/OpenHands", result)

    def test_bridge_repo_alias_returns_catalog_report(self) -> None:
        result = self.bridge.handle_command(100, "/repo openhands")

        self.assertIn("EXTERNAL REPO ARAMA", result)
        self.assertIn("OpenHands", result)

    def test_bridge_repo_oner_alias_returns_recommendations(self) -> None:
        result = self.bridge.handle_command(100, "/repo-oner youtube transcript cek")

        self.assertIn("REPO ONERI", result)
        self.assertIn("MCP / Ingestion", result)

    def test_bridge_octogent_alias_returns_status(self) -> None:
        result = self.bridge.handle_command(100, "/octogent durum")

        self.assertIn("Octogent durum", result)
        self.assertIn("external-repos/octogent", result)


if __name__ == "__main__":
    unittest.main()
