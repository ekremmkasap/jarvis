from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
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

import account_manager
import bridge as bridge_module
import codex_job_manager
import codex_orchestrator
import codex_quota_tracker
import codex_task_router
import skills.account_monitor as account_monitor


class CodexManagementTests(unittest.TestCase):
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

    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        self.state_dir = self.temp_root / "state" / "codex-accounts"
        self.config_dir = self.temp_root / "config"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        registry_payload = {}
        public_accounts = []
        slot_roles = {
            "atlas": "Manager/Core",
            "forge": "Backend Ops",
            "nexus": "Voice + Hologram",
            "shield": "Security / Audit",
            "spark": "Web UI / Frontend",
        }

        for slot, role in slot_roles.items():
            registry_payload[slot] = {
                "account_id": f"acc-{slot}",
                "saved_at": "2026-04-12T10:00:00+00:00",
            }
            (self.state_dir / f"{slot}.json").write_text(
                json.dumps(
                    {
                        "auth_mode": "chatgpt",
                        "status": "active",
                        "last_used": "2026-04-12T10:00:00+00:00",
                        "tokens": {"access_token": f"SECRET-{slot.upper()}"},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            public_accounts.append(
                {
                    "id": f"slot_{slot}",
                    "label": slot.upper(),
                    "provider": "openai-codex",
                    "role": role,
                    "status": "active",
                    "execution_slot": slot,
                    "runtime_account_id": f"acc-{slot}",
                    "daily_limit": 100,
                    "weekly_limit": 500,
                    "remaining_estimate": "~90%",
                    "last_seen": "-",
                    "notes": f"{slot} ready",
                }
            )

        (self.state_dir / "registry.json").write_text(
            json.dumps(registry_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (self.config_dir / "account_registry.json").write_text(
            json.dumps({"accounts": public_accounts}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (self.state_dir / "quota.json").write_text(
            json.dumps(
                {
                    "slots": {
                        "atlas": {
                            "daily_used": 0,
                            "weekly_used": 0,
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "remaining_pct": 100,
                            "cooldown_until": None,
                            "last_task_at": None,
                            "last_day": "2026-04-12",
                            "last_week": "2026-W15",
                        },
                        "forge": {
                            "daily_used": 100,
                            "weekly_used": 100,
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "remaining_pct": 0,
                            "cooldown_until": None,
                            "last_task_at": None,
                            "last_day": "2026-04-12",
                            "last_week": "2026-W15",
                        },
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self.patches = [
            patch.object(account_manager.AccountManager, "ROOT_DIR", self.temp_root),
            patch.object(account_manager.AccountManager, "CODEX_ACCOUNTS_PATH", self.state_dir),
            patch.object(account_manager.AccountManager, "PUBLIC_REGISTRY_PATH", self.config_dir / "account_registry.json"),
            patch.object(account_monitor, "ROOT", self.temp_root),
            patch.object(account_monitor, "REGISTRY_PATH", self.config_dir / "account_registry.json"),
        ]
        for active_patch in self.patches:
            active_patch.start()

        account_manager._account_manager = account_manager.AccountManager(vault_path=self.temp_root / "server" / "data" / ".account_vault")
        codex_quota_tracker._quota_tracker = codex_quota_tracker.CodexQuotaTracker(root_dir=self.temp_root)
        codex_job_manager._job_manager = codex_job_manager.CodexJobManager(root_dir=self.temp_root)
        codex_orchestrator._jobs = {}

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        account_manager._account_manager = None
        codex_quota_tracker._quota_tracker = None
        codex_job_manager._job_manager = None
        codex_orchestrator._jobs = {}
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_job_lifecycle_persists_to_queue_file(self) -> None:
        manager = codex_job_manager.CodexJobManager(root_dir=self.temp_root)
        job = manager.create_job(
            task="bridge endpointlerini tamamla",
            status="queued",
            requested_slots=["forge"],
            selected_slots=["atlas"],
            agents={"atlas": {"status": "pending", "output": None, "started_at": None, "finished_at": None}},
        )

        manager.update_agent_state(job["id"], "atlas", status="running", started_at="2026-04-12T10:00:00+00:00")
        manager.update_agent_state(job["id"], "atlas", status="done", output="tamamlandi", finished_at="2026-04-12T10:05:00+00:00")
        manager.finalize_job(job["id"], status="done", result_summary="tamamlandi")

        saved = manager.get_job(job["id"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved["status"], "done")
        self.assertEqual(saved["result_summary"], "tamamlandi")
        self.assertTrue((self.state_dir / "job_queue.json").exists())

    def test_route_keywords_match_expected_slots(self) -> None:
        self.assertEqual(codex_task_router.route_keywords("bridge.py guncelle"), ["forge"])
        self.assertEqual(codex_task_router.route_keywords("voice stack duzelt"), ["nexus"])
        self.assertEqual(codex_task_router.route_keywords("guvenlik audit yap"), ["shield"])

    def test_quota_exhausted_slot_falls_back_to_atlas(self) -> None:
        selection = codex_orchestrator._resolve_slots(["forge"])

        self.assertEqual(selection["requested_slots"], ["forge"])
        self.assertEqual(selection["selected_slots"], ["atlas"])
        self.assertIn("forge", selection["quota_exhausted_slots"])

    def test_bridge_accounts_payload_does_not_leak_runtime_tokens(self) -> None:
        payload = self.bridge._build_codex_accounts_payload()
        serialized = json.dumps(payload, ensure_ascii=False)

        self.assertIn("accounts", payload)
        self.assertNotIn("SECRET-FORGE", serialized)
        self.assertNotIn("tokens", serialized)
        self.assertNotIn("access_token", serialized)

    def test_bridge_status_and_result_payloads_use_persistent_job_state(self) -> None:
        manager = codex_job_manager.get_job_manager()
        job = manager.create_job(
            task="dashboard polling duzelt",
            status="done",
            requested_slots=["spark"],
            selected_slots=["spark"],
            result_summary="dashboard tamam",
            agents={
                "spark": {
                    "status": "done",
                    "output": "dashboard tamam",
                    "started_at": "2026-04-12T10:00:00+00:00",
                    "finished_at": "2026-04-12T10:03:00+00:00",
                }
            },
        )

        status_payload = self.bridge._build_codex_status_payload(limit=10)
        result_payload, status_code = self.bridge._build_codex_result_payload(job["id"])

        self.assertIn("runtime_slots", status_payload)
        self.assertTrue(any(item["slot"] == "atlas" for item in status_payload["runtime_slots"]))
        self.assertTrue(any(item["id"] == job["id"] for item in status_payload["jobs"]))
        self.assertEqual(status_code, 200)
        self.assertEqual(result_payload["result"], "dashboard tamam")

    def test_codex_status_command_formats_runtime_summary(self) -> None:
        status_text = self.bridge._handle_codex_status_command(100)

        self.assertIn("CODEX DURUM", status_text)
        self.assertIn("ATLAS", status_text)
        self.assertIn("FORGE", status_text)

    def test_codex_result_command_returns_missing_message(self) -> None:
        result_text = self.bridge._handle_codex_result_command(100, "job_missing")

        self.assertIn("Job bulunamadi", result_text)

    def test_accounts_update_only_changes_public_registry(self) -> None:
        forge_state_before = (self.state_dir / "forge.json").read_text(encoding="utf-8")

        payload, status_code = self.bridge._update_codex_account_payload("slot_forge", "status", "limited")

        forge_state_after = (self.state_dir / "forge.json").read_text(encoding="utf-8")
        public_registry = json.loads((self.config_dir / "account_registry.json").read_text(encoding="utf-8"))
        forge_public = next(item for item in public_registry["accounts"] if item["id"] == "slot_forge")

        self.assertEqual(status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(forge_public["status"], "limited")
        self.assertEqual(forge_state_before, forge_state_after)


if __name__ == "__main__":
    unittest.main()
