from __future__ import annotations

import importlib
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
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
        cls.original_telegram_intelligence_module = sys.modules.get(
            "telegram.telegram_intelligence"
        )
        os.environ["JARVIS_ENABLE_TELEGRAM"] = "0"
        os.environ["TELEGRAM_BOT_TOKEN"] = ""
        os.environ["TELEGRAM_CHAT_ID"] = "0"

        telegram_package = types.ModuleType("telegram")
        telegram_intelligence_module = types.ModuleType(
            "telegram.telegram_intelligence"
        )

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
            sys.modules["telegram.telegram_intelligence"] = (
                cls.original_telegram_intelligence_module
            )

    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        self.state_dir = self.temp_root / "state" / "codex-accounts"
        self.config_dir = self.temp_root / "config"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        today_key = now.date().isoformat()
        week_key = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"

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
                            "last_day": today_key,
                            "last_week": week_key,
                        },
                        "forge": {
                            "daily_used": 100,
                            "weekly_used": 100,
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "remaining_pct": 0,
                            "cooldown_until": None,
                            "last_task_at": None,
                            "last_day": today_key,
                            "last_week": week_key,
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
            patch.object(
                account_manager.AccountManager, "CODEX_ACCOUNTS_PATH", self.state_dir
            ),
            patch.object(
                account_manager.AccountManager,
                "PUBLIC_REGISTRY_PATH",
                self.config_dir / "account_registry.json",
            ),
            patch.object(account_monitor, "ROOT", self.temp_root),
            patch.object(
                account_monitor,
                "REGISTRY_PATH",
                self.config_dir / "account_registry.json",
            ),
        ]
        for active_patch in self.patches:
            active_patch.start()

        account_manager._account_manager = account_manager.AccountManager(
            vault_path=self.temp_root / "server" / "data" / ".account_vault"
        )
        codex_quota_tracker._quota_tracker = codex_quota_tracker.CodexQuotaTracker(
            root_dir=self.temp_root
        )
        codex_job_manager._job_manager = codex_job_manager.CodexJobManager(
            root_dir=self.temp_root
        )
        codex_orchestrator._jobs = {}

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        account_manager._account_manager = None
        codex_quota_tracker._quota_tracker = None
        codex_job_manager._job_manager = None
        codex_orchestrator._jobs = {}
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def _make_web_handler(self, path: str):
        class _FakeHandler:
            def __init__(self, request_path: str) -> None:
                self.path = request_path
                self.payload = None
                self.status_code = None

            def _json(self, data, code=200):
                self.payload = data
                self.status_code = code

        return _FakeHandler(path)

    def test_job_lifecycle_persists_to_queue_file(self) -> None:
        manager = codex_job_manager.CodexJobManager(root_dir=self.temp_root)
        job = manager.create_job(
            task="bridge endpointlerini tamamla",
            status="queued",
            requested_slots=["forge"],
            selected_slots=["atlas"],
            agents={
                "atlas": {
                    "status": "pending",
                    "output": None,
                    "started_at": None,
                    "finished_at": None,
                }
            },
        )

        manager.update_agent_state(
            job["id"], "atlas", status="running", started_at="2026-04-12T10:00:00+00:00"
        )
        manager.update_agent_state(
            job["id"],
            "atlas",
            status="done",
            output="tamamlandi",
            finished_at="2026-04-12T10:05:00+00:00",
        )
        manager.finalize_job(job["id"], status="done", result_summary="tamamlandi")

        saved = manager.get_job(job["id"])
        self.assertIsNotNone(saved)
        self.assertEqual(saved["status"], "done")
        self.assertEqual(saved["result_summary"], "tamamlandi")
        self.assertTrue((self.state_dir / "job_queue.json").exists())

    def test_route_keywords_match_expected_slots(self) -> None:
        self.assertEqual(
            codex_task_router.route_keywords("bridge.py guncelle"), ["forge"]
        )
        self.assertEqual(
            codex_task_router.route_keywords("voice stack duzelt"), ["spark"]
        )
        self.assertEqual(
            codex_task_router.route_keywords("guvenlik audit yap"), ["shield"]
        )

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
        self.assertTrue(
            any(item["slot"] == "atlas" for item in status_payload["runtime_slots"])
        )
        self.assertTrue(any(item["id"] == job["id"] for item in status_payload["jobs"]))
        self.assertEqual(status_code, 200)
        self.assertEqual(result_payload["result"], "dashboard tamam")

    def test_codex_status_command_formats_runtime_summary(self) -> None:
        status_text = self.bridge._handle_codex_status_command(100)

        self.assertIn("CODEX DURUM", status_text)
        self.assertIn("ATLAS", status_text)
        self.assertIn("FORGE", status_text)

    def test_new_codex_operator_payloads_expose_slots_queue_health_and_audit(
        self,
    ) -> None:
        manager = codex_job_manager.get_job_manager()
        pending_id = manager.enqueue(
            {
                "role": "backend",
                "task": {
                    "description": "pending bridge",
                    "type": "backend",
                    "payload": {},
                },
            }
        )
        running_id = manager.enqueue(
            {
                "role": "backend",
                "task": {
                    "description": "running bridge",
                    "type": "backend",
                    "payload": {},
                },
            }
        )
        codex_orchestrator.dispatch(running_id)
        codex_orchestrator.set_cooldown("forge", minutes=5, reason="drain")

        slots_payload = self.bridge._build_codex_slots_payload()
        queue_payload = self.bridge._build_codex_queue_payload()
        health_payload = self.bridge._build_codex_health_payload()
        audit_payload = self.bridge._build_codex_audit_payload(limit=50)

        self.assertEqual(len(slots_payload["slots"]), 5)
        self.assertTrue(
            any(slot["slot_id"] == "forge" for slot in slots_payload["slots"])
        )
        self.assertTrue(
            any(job["job_id"] == pending_id for job in queue_payload["jobs"])
        )
        self.assertIn("slots", health_payload)
        self.assertTrue(audit_payload["entries"])

    def test_dispatch_codex_job_returns_pending_contract(self) -> None:
        payload = self.bridge._dispatch_codex_job(
            task_description="bridge endpoint ekle", role="backend", priority=7
        )

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["status"], "pending")
        self.assertTrue(payload["job_id"])
        self.assertIn(payload["slot_id"], {"forge", "nexus"})

    def test_control_codex_plane_can_drain_and_clear_cooldowns(self) -> None:
        drain_result = self.bridge._control_codex_plane(
            action="drain", slot_id="forge", job_id=None
        )
        self.assertTrue(drain_result["ok"])
        self.assertTrue(codex_orchestrator.is_in_cooldown("forge"))

        clear_result = self.bridge._control_codex_plane(
            action="clear_cooldowns", slot_id=None, job_id=None
        )
        self.assertTrue(clear_result["ok"])
        self.assertFalse(codex_orchestrator.is_in_cooldown("forge"))

    def test_codex_telegram_commands(self) -> None:
        with (
            patch.object(
                self.bridge, "_handle_codex_slots_command", return_value="slots"
            ) as slots_handler,
            patch.object(
                self.bridge, "_handle_codex_queue_command", return_value="queue"
            ) as queue_handler,
            patch.object(
                self.bridge, "_handle_codex_health_command", return_value="health"
            ) as health_handler,
            patch.object(
                self.bridge, "_handle_codex_start_command", return_value="started"
            ) as start_handler,
            patch.object(
                self.bridge, "_handle_codex_stop_command", return_value="stopped"
            ) as stop_handler,
            patch.object(
                self.bridge,
                "_handle_codex_clear_cooldowns_command",
                return_value="cleared",
            ) as clear_handler,
        ):
            status_result = self.bridge.handle_command(101, "/codex-durum")
            self.assertTrue(status_result.startswith("slots"))
            self.assertIn("Persona Slotlari:", status_result)
            self.assertEqual(self.bridge.handle_command(102, "/codex-kuyruk"), "queue")
            self.assertEqual(self.bridge.handle_command(103, "/codex-saglik"), "health")
            self.assertEqual(
                self.bridge.handle_command(
                    104, "/codex-baslat backend bridge endpointlerini tamamla"
                ),
                "started",
            )
            self.assertEqual(
                self.bridge.handle_command(105, "/codex-durdur"), "stopped"
            )
            self.assertEqual(
                self.bridge.handle_command(106, "/codex-cooldown-temizle"), "cleared"
            )

        slots_handler.assert_called_once_with(101)
        queue_handler.assert_called_once_with(102)
        health_handler.assert_called_once_with(103)
        start_handler.assert_called_once_with(
            104, "backend bridge endpointlerini tamamla"
        )
        stop_handler.assert_called_once_with(105)
        clear_handler.assert_called_once_with(106)

    def test_codex_result_command_returns_missing_message(self) -> None:
        result_text = self.bridge._handle_codex_result_command(100, "job_missing")

        self.assertIn("Job bulunamadi", result_text)

    def test_autonomous_memory_command_uses_active_persona_by_default(self) -> None:
        fake_skill = SimpleNamespace(
            get_persona_memory=lambda persona_id, limit=5: {
                "persona_id": persona_id,
                "persona_name": "Seda",
                "recent_messages": [{"role": "assistant", "content": "son mesaj"}],
                "message_count": 1,
            },
            format_persona_memory_text=lambda snapshot: f"MEMORY::{snapshot['persona_id']}",
        )

        with (
            patch.object(self.bridge, "_autonomous_load_skill", return_value=fake_skill),
            patch.object(
                self.bridge,
                "_get_active_persona_payload",
                return_value={"id": "seda", "name": "Seda"},
            ),
        ):
            result = self.bridge.handle_command(201, "/hafiza")

        self.assertEqual(result, "MEMORY::seda")

    def test_autonomous_agents_summary_command_uses_memory_skill_formatter(self) -> None:
        fake_summary = {
            "agents": [{"persona_id": "seda", "persona_name": "Seda"}],
            "active_persona": "seda",
            "generated_at": "2026-04-14T10:00:00Z",
        }
        fake_skill = SimpleNamespace(
            get_all_agents_summary=lambda: fake_summary,
            format_agents_summary_text=lambda summary: "SUMMARY::seda",
        )

        with patch.object(self.bridge, "_autonomous_load_skill", return_value=fake_skill):
            result = self.bridge.handle_command(202, "/ajanlarin-ozeti")

        self.assertEqual(result, "SUMMARY::seda")

    def test_autonomous_persona_memory_api_returns_snapshot(self) -> None:
        fake_handler = self._make_web_handler("/api/persona/seda/memory?limit=7")
        fake_skill = SimpleNamespace(
            get_persona_memory=lambda persona_id, limit=5: {
                "persona_id": persona_id,
                "limit_used": limit,
                "recent_messages": [{"role": "assistant", "content": "ok"}],
            }
        )

        with patch.object(self.bridge, "_autonomous_load_skill", return_value=fake_skill):
            self.bridge._do_get_with_autonomous_endpoints(fake_handler)

        self.assertEqual(fake_handler.status_code, 200)
        self.assertEqual(fake_handler.payload["persona_id"], "seda")
        self.assertEqual(fake_handler.payload["limit_used"], 7)

    def test_autonomous_agents_summary_api_returns_payload(self) -> None:
        fake_handler = self._make_web_handler("/api/agents/summary")
        fake_skill = SimpleNamespace(
            get_all_agents_summary=lambda: {
                "agents": [{"persona_id": "seda", "persona_name": "Seda"}],
                "active_persona": "seda",
            }
        )

        with patch.object(self.bridge, "_autonomous_load_skill", return_value=fake_skill):
            self.bridge._do_get_with_autonomous_endpoints(fake_handler)

        self.assertEqual(fake_handler.status_code, 200)
        self.assertEqual(fake_handler.payload["active_persona"], "seda")
        self.assertTrue(fake_handler.payload["generated_at"])

    def test_autonomous_pc_status_api_returns_gateway_status(self) -> None:
        fake_handler = self._make_web_handler("/api/pc/status")
        fake_gateway = SimpleNamespace(
            get_system_status=lambda: {"cpu_percent": 11.5, "ram_used_mb": 2048}
        )

        with patch.object(self.bridge, "_autonomous_load_skill", return_value=fake_gateway):
            self.bridge._do_get_with_autonomous_endpoints(fake_handler)

        self.assertEqual(fake_handler.status_code, 200)
        self.assertEqual(fake_handler.payload["cpu_percent"], 11.5)
        self.assertEqual(fake_handler.payload["ram_used_mb"], 2048)

    def test_codex_dispatch_uses_active_persona_slot_automatically(self) -> None:
        with (
            patch.object(
                self.bridge,
                "_get_active_persona_payload",
                return_value={"id": "seda", "name": "Seda", "codex_slot": "forge"},
            ),
            patch.object(
                codex_orchestrator,
                "dispatch_job",
                return_value={
                    "ok": True,
                    "job_id": "job-123",
                    "status": "pending",
                    "selected_slots": ["forge"],
                    "message": "queued",
                },
            ) as dispatch_job,
        ):
            result = self.bridge.handle_command(203, '/codex-dispatch "bridge endpointini tamamla"')

        dispatch_job.assert_called_once_with(
            "bridge endpointini tamamla",
            swarm=False,
            requested_slots=["forge"],
        )
        self.assertIn("Seda -> FORGE", result)
        self.assertIn("Job: job-123", result)
        self.assertIn("Slot: FORGE", result)

    def test_accounts_update_only_changes_public_registry(self) -> None:
        forge_state_before = (self.state_dir / "forge.json").read_text(encoding="utf-8")

        payload, status_code = self.bridge._update_codex_account_payload(
            "slot_forge", "status", "limited"
        )

        forge_state_after = (self.state_dir / "forge.json").read_text(encoding="utf-8")
        public_registry = json.loads(
            (self.config_dir / "account_registry.json").read_text(encoding="utf-8")
        )
        forge_public = next(
            item for item in public_registry["accounts"] if item["id"] == "slot_forge"
        )

        self.assertEqual(status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(forge_public["status"], "limited")
        self.assertEqual(forge_state_before, forge_state_after)


if __name__ == "__main__":
    unittest.main()
