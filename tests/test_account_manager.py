from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.account_manager import AccountManager
import server.account_manager as account_manager_module
import server.codex_quota_tracker as codex_quota_tracker


class AccountManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp())
        self.state_dir = self.temp_root / "state" / "codex-accounts"
        self.config_dir = self.temp_root / "config"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        for slot in ("atlas", "forge", "nexus", "shield", "spark"):
            (self.state_dir / f"{slot}.json").write_text(
                json.dumps({"email": f"{slot}@jarvis.local", "status": "active", "tokens": {"access_token": f"SECRET-{slot.upper()}"}}, indent=2),
                encoding="utf-8",
            )

        (self.state_dir / "registry.json").write_text(
            json.dumps(
                {
                    "atlas": {"account_id": "acc-atlas", "saved_at": "2026-04-01T10:00:00Z"},
                    "forge": {"account_id": "acc-forge", "saved_at": "2026-04-01T11:00:00Z"},
                    "nexus": {"account_id": "acc-nexus", "saved_at": "2026-04-01T11:30:00Z"},
                    "shield": {"account_id": "acc-shield", "saved_at": "2026-04-01T11:45:00Z"},
                    "spark": {"account_id": "acc-spark", "saved_at": "2026-04-01T12:00:00Z"},
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        (self.config_dir / "account_registry.json").write_text(
            json.dumps(
                {
                    "accounts": [
                        {
                            "id": "slot_atlas",
                            "label": "Atlas",
                            "provider": "openai-codex",
                            "role": "Manager/Core",
                            "status": "active",
                            "execution_slot": "atlas",
                            "runtime_account_id": "acc-atlas",
                            "remaining_estimate": "~80%",
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "last_seen": "2026-04-01 10:00 UTC",
                            "notes": "manager",
                        },
                        {
                            "id": "voice_slot",
                            "label": "Voice + Hologram",
                            "provider": "openai-codex",
                            "role": "Voice",
                            "status": "quota_exceeded",
                            "execution_slot": "forge",
                            "runtime_account_id": "acc-forge",
                            "remaining_estimate": "~0%",
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "last_seen": "2026-04-01 11:00 UTC",
                            "notes": "blocked",
                        },
                        {
                            "id": "slot_nexus",
                            "label": "Nexus",
                            "provider": "openai-codex",
                            "role": "Overflow",
                            "status": "active",
                            "execution_slot": "nexus",
                            "runtime_account_id": "acc-nexus",
                            "remaining_estimate": "~60%",
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "last_seen": "2026-04-01 11:30 UTC",
                            "notes": "overflow",
                        },
                        {
                            "id": "slot_shield",
                            "label": "Shield",
                            "provider": "openai-codex",
                            "role": "Security",
                            "status": "active",
                            "execution_slot": "shield",
                            "runtime_account_id": "acc-shield",
                            "remaining_estimate": "~70%",
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "last_seen": "2026-04-01 11:45 UTC",
                            "notes": "security",
                        },
                        {
                            "id": "slot_spark",
                            "label": "Spark",
                            "provider": "openai-codex",
                            "role": "Voice/UI",
                            "status": "active",
                            "execution_slot": "spark",
                            "runtime_account_id": "acc-spark",
                            "remaining_estimate": "~90%",
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "last_seen": "2026-04-01 12:00 UTC",
                            "notes": "ui",
                        },
                    ]
                },
                indent=2,
            ),
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
                            "last_day": "2026-04-01",
                            "last_week": "2026-W14",
                        },
                        "forge": {
                            "daily_used": 100,
                            "weekly_used": 100,
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "remaining_pct": 0,
                            "cooldown_until": None,
                            "last_task_at": None,
                            "last_day": "2026-04-01",
                            "last_week": "2026-W14",
                        },
                    }
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        self.patches = [
            patch.object(AccountManager, "ROOT_DIR", self.temp_root),
            patch.object(AccountManager, "CODEX_ACCOUNTS_PATH", self.state_dir),
            patch.object(AccountManager, "PUBLIC_REGISTRY_PATH", self.config_dir / "account_registry.json"),
        ]
        for active_patch in self.patches:
            active_patch.start()

    def tearDown(self) -> None:
        for active_patch in reversed(self.patches):
            active_patch.stop()
        account_manager_module._account_manager = None
        codex_quota_tracker._quota_tracker = None
        shutil.rmtree(self.temp_root, ignore_errors=True)

    def _build_manager(self) -> AccountManager:
        return AccountManager(vault_path=self.temp_root / "server" / "data" / ".account_vault")

    def test_get_active_account_prefers_lowest_priority_ready_slot(self) -> None:
        manager = self._build_manager()
        active = manager.get_active_account("codex")
        self.assertIsNotNone(active)
        self.assertEqual(active.runtime_slot, "atlas")

    def test_resolve_codex_accounts_skips_blocked_operator_slot_and_falls_back(self) -> None:
        manager = self._build_manager()
        selection = manager.resolve_codex_accounts(["atlas", "forge"])

        self.assertEqual(selection["requested_slots"], ["atlas", "forge"])
        self.assertEqual(selection["selected_slots"], ["atlas", "nexus"])
        self.assertEqual(selection["unavailable_slots"], ["forge"])
        self.assertEqual(selection["fallback_slots"], ["nexus"])

    def test_switch_account_reprioritizes_codex_without_disabling_other_slots(self) -> None:
        manager = self._build_manager()
        self.assertTrue(manager.switch_account("codex_spark"))

        active = manager.get_active_account("codex")
        self.assertIsNotNone(active)
        self.assertEqual(active.runtime_slot, "spark")
        self.assertEqual(manager.get_codex_account_by_slot("atlas").status, "active")

        selection = manager.resolve_codex_accounts(["atlas", "spark"])
        self.assertEqual(selection["selected_slots"], ["atlas", "spark"])

    def test_get_status_keeps_execution_and_operator_truth_in_one_contract(self) -> None:
        manager = self._build_manager()

        status = manager.get_status()
        codex = status["codex"]

        self.assertEqual(codex["total"], 5)
        self.assertEqual(codex["ready_accounts"], 4)
        self.assertEqual(codex["available_slots"], ["atlas", "nexus", "shield", "spark"])

        forge = next(
            account
            for account in codex["accounts"]
            if account["runtime_slot"] == "forge"
        )
        self.assertEqual(forge["status"], "quota_exceeded")
        self.assertEqual(forge["runtime_account_id"], "acc-forge")
        self.assertEqual(forge["operator_id"], "voice_slot")
        self.assertEqual(forge["operator_label"], "Voice + Hologram")
        self.assertEqual(forge["operator_status"], "quota_exceeded")

    def test_get_slot_returns_redacted_merged_slot_payload(self) -> None:
        manager = self._build_manager()

        slot = manager.get_slot("atlas")

        self.assertIsNotNone(slot)
        self.assertEqual(slot["slot_id"], "atlas")
        self.assertEqual(slot["label"], "Atlas")
        self.assertEqual(slot["quota_estimate"], "~80%")
        self.assertTrue(slot["is_available"])
        self.assertNotIn("tokens", json.dumps(slot))
        self.assertNotIn("access_token", json.dumps(slot))

    def test_list_slots_returns_all_five_canonical_slots(self) -> None:
        manager = self._build_manager()

        slots = manager.list_slots()

        self.assertEqual([slot["slot_id"] for slot in slots], ["atlas", "forge", "nexus", "shield", "spark"])

    def test_get_active_slot_returns_current_codex_slot_payload(self) -> None:
        manager = self._build_manager()

        slot = manager.get_active_slot()

        self.assertIsNotNone(slot)
        self.assertEqual(slot["slot_id"], "atlas")

    def test_set_slot_status_updates_execution_truth_only(self) -> None:
        manager = self._build_manager()
        before_registry = (self.config_dir / "account_registry.json").read_text(encoding="utf-8")

        updated = manager.set_slot_status("spark", "disabled")

        after_registry = (self.config_dir / "account_registry.json").read_text(encoding="utf-8")
        runtime_data = json.loads((self.state_dir / "spark.json").read_text(encoding="utf-8"))
        self.assertTrue(updated)
        self.assertEqual(runtime_data["status"], "disabled")
        self.assertEqual(before_registry, after_registry)

    def test_get_quota_estimate_reads_metadata_truth_only(self) -> None:
        manager = self._build_manager()

        self.assertEqual(manager.get_quota_estimate("shield"), "~70%")

    def test_is_slot_available_checks_status_and_cooldown_combined(self) -> None:
        manager = self._build_manager()

        self.assertTrue(manager.is_slot_available("atlas"))
        self.assertFalse(manager.is_slot_available("forge"))

    def test_match_operator_metadata_can_infer_slots_from_role_hints_when_execution_slot_missing(self) -> None:
        (self.config_dir / "account_registry.json").write_text(
            json.dumps(
                {
                    "accounts": [
                        {
                            "id": "agent_01_core",
                            "label": "Core / Manager",
                            "provider": "openai-codex",
                            "role": "Manager/Core",
                            "status": "active",
                            "execution_slot": "",
                            "runtime_account_id": "",
                            "remaining_estimate": "~80%",
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "last_seen": "2026-04-01 10:00 UTC",
                            "notes": "manager role",
                        },
                        {
                            "id": "agent_02_backend",
                            "label": "Backend Ops",
                            "provider": "openai-codex",
                            "role": "Backend Ops",
                            "status": "active",
                            "execution_slot": "",
                            "runtime_account_id": "",
                            "remaining_estimate": "~90%",
                            "daily_limit": 100,
                            "weekly_limit": 500,
                            "last_seen": "2026-04-01 11:00 UTC",
                            "notes": "n8n shell deployment",
                        },
                    ]
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        manager = self._build_manager()
        atlas = manager.get_slot("atlas")
        forge = manager.get_slot("forge")

        self.assertEqual(atlas["label"], "Core / Manager")
        self.assertEqual(forge["label"], "Backend Ops")

    def test_redact_sensitive_removes_nested_secret_like_keys(self) -> None:
        manager = self._build_manager()

        redacted = manager._redact_sensitive(
            {
                "safe": 1,
                "nested": {
                    "accessToken": "secret-value",
                    "api_key_hint": "secret-key",
                    "ok": "visible",
                },
                "items": [{"refresh_token": "hidden", "name": "visible"}],
            }
        )

        serialized = json.dumps(redacted)
        self.assertIn('"safe": 1', serialized)
        self.assertIn('"ok": "visible"', serialized)
        self.assertIn('"name": "visible"', serialized)
        self.assertNotIn("accessToken", serialized)
        self.assertNotIn("api_key_hint", serialized)
        self.assertNotIn("refresh_token", serialized)


if __name__ == "__main__":
    unittest.main()
