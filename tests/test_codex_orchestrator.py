from __future__ import annotations

import importlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).parent.parent
SERVER_PATH = ROOT / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import account_manager
import codex_job_manager
import codex_orchestrator as codex_orchestrator_module
import codex_quota_tracker


class CodexOrchestratorTests(unittest.TestCase):
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
            "nexus": "Overflow/Reserve",
            "shield": "Security / Audit",
            "spark": "Voice / Video",
        }
        for slot, role in slot_roles.items():
            registry_payload[slot] = {"account_id": f"acc-{slot}", "saved_at": "2026-04-12T10:00:00+00:00"}
            (self.state_dir / f"{slot}.json").write_text(json.dumps({"auth_mode": "chatgpt", "status": "active"}, indent=2), encoding="utf-8")
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

        (self.state_dir / "registry.json").write_text(json.dumps(registry_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.config_dir / "account_registry.json").write_text(json.dumps({"accounts": public_accounts}, ensure_ascii=False, indent=2), encoding="utf-8")
        (self.state_dir / "quota.json").write_text(
            json.dumps(
                {
                    "slots": {
                        slot: {
                            "daily_used": 0,
                            "weekly_used": 0,
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "remaining_pct": 100,
                            "cooldown_until": None,
                            "last_task_at": None,
                            "last_day": "2026-04-12",
                            "last_week": "2026-W15",
                        }
                        for slot in slot_roles
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
        ]
        for active_patch in self.patches:
            active_patch.start()

        account_manager._account_manager = account_manager.AccountManager(vault_path=self.temp_root / "server" / "data" / ".account_vault")
        codex_quota_tracker._quota_tracker = codex_quota_tracker.CodexQuotaTracker(root_dir=self.temp_root)
        codex_job_manager._job_manager = codex_job_manager.CodexJobManager(root_dir=self.temp_root)

        self.orchestrator = importlib.reload(codex_orchestrator_module)
        self.orchestrator.ROOT = self.temp_root
        self.orchestrator.SERVER_DIR = self.temp_root / "server"
        self.orchestrator.LOG_DIR = self.temp_root / "server" / "logs"
        self.orchestrator.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.orchestrator.LEGACY_JOBS_FILE = self.orchestrator.LOG_DIR / "codex_jobs.json"
        self.orchestrator.DISPATCH_AUDIT_PATH = self.orchestrator.LOG_DIR / "codex_dispatch_audit.jsonl"
        self.orchestrator.COOLDOWN_PATH = self.temp_root / "state" / "codex_cooldowns.json"
        self.orchestrator._jobs = {}

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        account_manager._account_manager = None
        codex_quota_tracker._quota_tracker = None
        codex_job_manager._job_manager = None
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def test_dispatch_selects_first_available_affinity_slot_and_writes_audit(self) -> None:
        job_id = codex_job_manager.get_job_manager().enqueue({"role": "backend", "task": {"description": "bridge patch", "type": "backend", "payload": {}}})

        selected = self.orchestrator.dispatch(job_id)
        job = codex_job_manager.get_job_manager().get_job(job_id)
        audit = self.orchestrator.read_dispatch_audit(limit=5)

        self.assertEqual(selected, "forge")
        self.assertEqual(job["status"], "running")
        self.assertEqual(job["selected_slots"], ["forge"])
        self.assertTrue(audit)
        self.assertEqual(audit[-1]["selected_slot"], "forge")

    def test_dispatch_requeues_when_no_slot_available(self) -> None:
        with patch.object(account_manager.get_account_manager(), "is_slot_available", return_value=False):
            job_id = codex_job_manager.get_job_manager().enqueue({"role": "backend", "task": {"description": "bridge patch", "type": "backend", "payload": {}}})
            selected = self.orchestrator.dispatch(job_id)

        job = codex_job_manager.get_job_manager().get_job(job_id)
        self.assertIsNone(selected)
        self.assertEqual(job["status"], "pending")
        self.assertEqual(job["failure_reason"], "no_slot_available")
        self.assertTrue(job.get("dispatch_after"))

    def test_set_and_clear_cooldown_persist_state(self) -> None:
        cooldown = self.orchestrator.set_cooldown("forge", minutes=5, reason="manual_pause")
        self.assertTrue(cooldown["active"])
        self.assertTrue(self.orchestrator.is_in_cooldown("forge"))
        self.orchestrator.clear_cooldown("forge")
        self.assertFalse(self.orchestrator.is_in_cooldown("forge"))

    def test_failover_job_selects_next_affinity_slot(self) -> None:
        job_manager = codex_job_manager.get_job_manager()
        job_id = job_manager.enqueue(
            {
                "role": "backend",
                "selected_slots": ["forge"],
                "slot_id": "forge",
                "status": "running",
                "task": {"description": "bridge patch", "type": "backend", "payload": {}},
            }
        )
        job_manager.update_agent_state(job_id, "forge", status="failed", output="boom", finished_at="2026-04-12T10:05:00+00:00")

        with patch.object(self.orchestrator, "_spawn_slot_thread") as spawn_thread:
            selected = self.orchestrator._failover_job(job_id, "forge", "forge_execution_failed", "bridge patch")

        job = job_manager.get_job(job_id)
        self.assertEqual(selected, "nexus")
        self.assertEqual(job["status"], "running")
        self.assertIn("nexus", job["selected_slots"])
        spawn_thread.assert_called_once_with(job_id, "nexus", "bridge patch")


if __name__ == "__main__":
    unittest.main()
