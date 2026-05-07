from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys


SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import persona_manager


class PersonaManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        self.config_path = self.temp_root / "agents.yaml"
        self.active_path = self.temp_root / "active_agent.json"
        self.world_path = self.temp_root / "agent_world.json"
        self.memory_dir = self.temp_root / "agent_memory"

        self.config_path.write_text(
            """
personas:
  seda:
    name: "Seda"
    visibility: internal
    requires_flag: JARVIS_DEV_MODE
    color: "#00ff88"
    voice: "AhmetNeural"
    role: "Kod/Debug/PR"
    skills: ["code_review", "implementer"]
  mert:
    name: "Mert"
    color: "#ffdd00"
    voice: "AhmetNeural"
    role: "Arastirma/Rakip"
    skills: ["research", "web_search"]
  buse:
    name: "Buse"
    color: "#ff69b4"
    voice: "EmelNeural"
    role: "Pazarlama/Landing"
    skills: ["content", "seo"]
  deniz:
    name: "Deniz"
    color: "#1abc9c"
    voice: "AhmetNeural"
    role: "E-ticaret"
    skills: ["e_ticaret", "trendyol", "pazaryeri"]
  eren:
    name: "Eren"
    color: "#ff8c00"
    voice: "AhmetNeural"
    role: "Veri/Dashboard"
    skills: ["data_analysis"]
  luna:
    name: "Luna"
    color: "#9b59b6"
    voice: "EmelNeural"
    role: "Guvenlik/Audit"
    skills: ["security"]
  zeynep:
    name: "Zeynep"
    color: "#34495e"
    voice: "EmelNeural"
    role: "Guvenlik/KVKK"
    skills: ["security", "kvkk", "audit"]
  sabrican:
    name: "Sabrican"
    visibility: internal
    requires_flag: JARVIS_ADMIN_MODE
    color: "#95a5a6"
    voice: "AhmetNeural"
    role: "Operasyon/Otomasyon"
    skills: ["deploy", "ops", "openclaw_helper", "octogent_helper"]
    sub_agents: ["deploy_runner", "ci_monitor", "service_watcher", "openclaw_integrator"]
    codex_subagents: ["devops-engineer", "deployment-engineer", "sre-engineer", "llm-architect"]
    skill_surfaces: ["gateway_health", "channel_delivery", "auth_profile_sync", "wrapper_control", "tentacle_control", "terminal_control"]
    secondary_runtimes:
      - id: "openclaw"
        mode: "helper_only"
        ownership: "secondary"
        canonical_runtime: false
        bridge_module: "server.openclaw_bridge"
        sub_agents: ["openclaw_integrator", "gateway_health_watcher", "channel_delivery_operator", "auth_profile_sync"]
        skill_surfaces: ["gateway_health", "channel_delivery", "auth_profile_sync", "wrapper_control"]
      - id: "octogent"
        mode: "helper_only"
        ownership: "secondary"
        canonical_runtime: false
        bridge_module: "server.octogent_bridge"
        sub_agents: ["tentacle_orchestrator", "terminal_supervisor", "todo_swarm_manager", "channel_messenger"]
        skill_surfaces: ["tentacle_control", "terminal_control", "todo_orchestration", "channel_messaging", "monitor_feed"]
  sabri:
    name: "Sabri"
    color: "#e74c3c"
    voice: "AhmetNeural"
    role: "Wildcard/Yaratici"
    skills: ["general"]
""".strip(),
            encoding="utf-8",
        )

        self.patches = [
            patch.object(persona_manager, "PERSONA_CONFIG_PATH", self.config_path),
            patch.object(persona_manager, "ACTIVE_AGENT_PATH", self.active_path),
            patch.object(persona_manager, "AGENT_WORLD_PATH", self.world_path),
            patch.object(persona_manager, "AGENT_MEMORY_DIR", self.memory_dir),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_switch_persona_updates_state(self) -> None:
        result = persona_manager.switch_persona("buse")

        self.assertTrue(result["ok"])
        active = persona_manager.get_active_persona()
        self.assertEqual(active["id"], "buse")
        self.assertEqual(active["voice"], "EmelNeural")
        self.assertTrue(self.active_path.exists())
        self.assertTrue(self.world_path.exists())

    def test_unknown_persona_returns_error(self) -> None:
        result = persona_manager.switch_persona("arif")

        self.assertFalse(result["ok"])
        self.assertIn("Bu isimde bir ajan tanimlamadim", result["error"])

    def test_get_active_defaults_to_jarvis(self) -> None:
        active = persona_manager.get_active_persona()

        self.assertEqual(active["id"], "jarvis")
        self.assertEqual(active["name"], "Jarvis")

    def test_switch_persona_is_scoped_by_lane(self) -> None:
        web_result = persona_manager.switch_persona("buse", lane="web")
        telegram_result = persona_manager.switch_persona("luna", lane="telegram")

        web_active = persona_manager.get_active_persona(lane="web")
        telegram_active = persona_manager.get_active_persona(lane="telegram")
        default_active = persona_manager.get_active_persona()
        saved_state = json.loads(self.active_path.read_text(encoding="utf-8"))

        self.assertTrue(web_result["ok"])
        self.assertTrue(telegram_result["ok"])
        self.assertEqual(web_active["id"], "buse")
        self.assertEqual(telegram_active["id"], "luna")
        self.assertEqual(default_active["id"], "luna")
        self.assertEqual(saved_state["lanes"]["web"]["id"], "buse")
        self.assertEqual(saved_state["lanes"]["telegram"]["id"], "luna")

    def test_remember_and_recall(self) -> None:
        persona_manager.remember(
            "buse", "Landing A/B test sonucu: kirmizi buton %12 daha iyi"
        )
        persona_manager.remember("buse", "Instagram reels hook fikri denensin")

        recalled = persona_manager.recall("buse", "landing", top_k=5)

        self.assertGreaterEqual(len(recalled), 1)
        self.assertIn("Landing A/B test sonucu", recalled[0]["text"])

    def test_list_personas_returns_7(self) -> None:
        with patch.dict(
            os.environ,
            {"JARVIS_DEV_MODE": "", "JARVIS_ADMIN_MODE": ""},
            clear=False,
        ):
            personas = persona_manager.list_personas()

        self.assertEqual(len(personas), 7)
        self.assertEqual(
            {item["id"] for item in personas},
            {"sabri", "luna", "buse", "deniz", "eren", "mert", "zeynep"},
        )

    def test_internal_personas_are_hidden_without_flags(self) -> None:
        with patch.dict(
            os.environ,
            {"JARVIS_DEV_MODE": "", "JARVIS_ADMIN_MODE": ""},
            clear=False,
        ):
            personas = persona_manager.list_personas()
            result = persona_manager.switch_persona("seda")

        ids = {item["id"] for item in personas}
        self.assertNotIn("seda", ids)
        self.assertNotIn("sabrican", ids)
        self.assertFalse(result["ok"])

    def test_internal_persona_switch_enabled_by_flag(self) -> None:
        with patch.dict(os.environ, {"JARVIS_DEV_MODE": "1"}, clear=False):
            personas = persona_manager.list_personas()
            result = persona_manager.switch_persona("seda")

        self.assertIn("seda", {item["id"] for item in personas})
        self.assertTrue(result["ok"])
        self.assertEqual(result["id"], "seda")

    def test_detect_switch_from_text(self) -> None:
        self.assertEqual(
            persona_manager.detect_switch_from_text("Buse ile konus"), "buse"
        )
        self.assertEqual(persona_manager.detect_switch_from_text("Luna'ya gec"), "luna")
        self.assertIsNone(persona_manager.detect_switch_from_text("hava nasil bugun"))

    def test_sabrican_keeps_openclaw_runtime_metadata(self) -> None:
        sabrican = persona_manager.load_personas()["sabrican"]

        self.assertIn("deploy_runner", sabrican["sub_agents"])
        self.assertIn("ci_monitor", sabrican["sub_agents"])
        self.assertIn("service_watcher", sabrican["sub_agents"])
        self.assertIn("openclaw_integrator", sabrican["sub_agents"])
        self.assertIn("devops-engineer", sabrican["codex_subagents"])
        self.assertIn("sre-engineer", sabrican["codex_subagents"])
        self.assertIn("gateway_health", sabrican["skill_surfaces"])
        self.assertIn("auth_profile_sync", sabrican["skill_surfaces"])
        self.assertIn("octogent_helper", sabrican["skills"])
        runtimes = {item["id"]: item for item in sabrican["secondary_runtimes"]}
        self.assertEqual(runtimes["openclaw"]["id"], "openclaw")
        self.assertEqual(
            runtimes["openclaw"]["mode"], "helper_only"
        )
        self.assertFalse(runtimes["openclaw"]["canonical_runtime"])
        self.assertEqual(
            runtimes["openclaw"]["ownership"], "secondary"
        )
        self.assertIn(
            "channel_delivery_operator",
            runtimes["openclaw"]["sub_agents"],
        )
        self.assertEqual(runtimes["octogent"]["mode"], "helper_only")
        self.assertFalse(runtimes["octogent"]["canonical_runtime"])
        self.assertIn("tentacle_orchestrator", runtimes["octogent"]["sub_agents"])
        self.assertIn("tentacle_control", runtimes["octogent"]["skill_surfaces"])


if __name__ == "__main__":
    unittest.main()
