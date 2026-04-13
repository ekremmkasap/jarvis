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


ROOT = Path(__file__).parent.parent
SERVER_PATH = ROOT / "server"
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
import codex_health
import codex_job_manager
import codex_orchestrator
import codex_quota_tracker
import codex_workspace
import skills.account_monitor as account_monitor


class CodexHealthTests(unittest.TestCase):
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
        self.worktree_dir = self.temp_root / ".worktrees"
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
                            "last_task_at": "2026-04-12T10:00:00+00:00",
                            "last_day": "2026-04-12",
                            "last_week": "2026-W15",
                        },
                        "forge": {
                            "daily_used": 10,
                            "weekly_used": 10,
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "remaining_pct": 90,
                            "cooldown_until": None,
                            "last_task_at": "2026-04-12T11:00:00+00:00",
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
            patch.object(codex_workspace.WorkspaceManager, "BASE", self.worktree_dir),
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

    def test_workspace_status_returns_all_slots(self) -> None:
        status = codex_workspace.WorkspaceManager().status()

        for slot in ["atlas", "forge", "nexus", "shield", "spark"]:
            self.assertIn(slot, status)
            self.assertIsInstance(status[slot], bool)

    def test_workspace_init_command_safe(self) -> None:
        command = codex_workspace.WorkspaceManager().init_command("forge")

        self.assertIn("git worktree add", command)
        self.assertIn("forge", command)
        self.assertIn('"', command)

    def test_workspace_clean_command_safe(self) -> None:
        command = codex_workspace.WorkspaceManager().clean_command("forge")

        self.assertIn("reset --hard HEAD", command)
        self.assertIn("clean -fd", command)
        self.assertIn("; if ($?) {", command)

    def test_health_watcher_starts(self) -> None:
        watcher = codex_health.CodexHealthWatcher(interval_seconds=9999)
        watcher.start()
        first_thread = watcher._thread
        watcher.start()

        self.assertIsNotNone(first_thread)
        self.assertTrue(first_thread.is_alive())
        self.assertIs(first_thread, watcher._thread)

    def test_build_codex_status_payload_includes_workspaces(self) -> None:
        payload = self.bridge._build_codex_status_payload(limit=10)

        self.assertIn("workspaces", payload)
        for slot in ["atlas", "forge", "nexus", "shield", "spark"]:
            self.assertIn(slot, payload["workspaces"])

    def test_workspace_command_lists_missing_slot_init_commands(self) -> None:
        text = self.bridge._handle_command_with_sprint_extensions(100, "/codex-workspace")

        self.assertIn("Worktree Durumu", text)
        self.assertIn("atlas", text)
        self.assertIn("Init:", text)

    def test_notify_does_not_leak_secret_values(self) -> None:
        watcher = codex_health.CodexHealthWatcher(interval_seconds=600, notify_chat_id=123)

        with patch.object(codex_health, "send_telegram_message") as send_message:
            watcher._notify("warning", "job SECRET payload access_token=abc123")

        send_message.assert_called_once()
        sent_text = send_message.call_args.args[1]
        lowered = sent_text.lower()
        self.assertNotIn("access_token", lowered)
        self.assertNotIn("secret", lowered)
        self.assertNotIn("abc123", lowered)

    def test_health_check_low_quota_triggers_notification(self) -> None:
        watcher = codex_health.CodexHealthWatcher(interval_seconds=600, notify_chat_id=123)

        with patch.object(codex_health, "get_all_quotas", return_value={"forge": {"remaining_pct": 4, "last_task_at": None}}), patch.object(
            codex_health, "get_quota_tracker"
        ) as tracker_factory, patch.object(codex_health, "list_recent_jobs", return_value=[]), patch.object(watcher, "_notify") as notify:
            tracker_factory.return_value.is_exhausted.return_value = False
            watcher._check()

        self.assertTrue(any("quota" in call.args[1].lower() for call in notify.call_args_list))

    def test_health_check_stuck_running_job_triggers_notification(self) -> None:
        watcher = codex_health.CodexHealthWatcher(interval_seconds=600, notify_chat_id=123)

        with patch.object(codex_health, "get_all_quotas", return_value={}), patch.object(
            codex_health, "get_quota_tracker"
        ) as tracker_factory, patch.object(
            codex_health,
            "list_recent_jobs",
            return_value=[
                {
                    "id": "job_123",
                    "status": "running",
                    "summary": "bridge patch",
                    "selected_slots": ["forge"],
                    "duration_seconds": 1900,
                }
            ],
        ), patch.object(watcher, "_notify") as notify:
            tracker_factory.return_value.is_exhausted.return_value = False
            watcher._check()

        self.assertTrue(any("takili" in call.args[1].lower() for call in notify.call_args_list))

    def test_health_check_all_exhausted_triggers_critical_notification(self) -> None:
        watcher = codex_health.CodexHealthWatcher(interval_seconds=600, notify_chat_id=123)

        quotas = {
            "atlas": {"remaining_pct": 0, "last_task_at": None},
            "forge": {"remaining_pct": 0, "last_task_at": None},
        }
        with patch.object(codex_health, "get_all_quotas", return_value=quotas), patch.object(
            codex_health, "get_quota_tracker"
        ) as tracker_factory, patch.object(codex_health, "list_recent_jobs", return_value=[]), patch.object(watcher, "_notify") as notify:
            tracker_factory.return_value.is_exhausted.return_value = True
            watcher._check()

        self.assertTrue(any("exhausted" in call.args[1].lower() for call in notify.call_args_list))


if __name__ == "__main__":
    unittest.main()
