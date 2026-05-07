from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server import openclaw_bridge
from server.security.policy_gate import PolicyDecision


class OpenClawBridgeTests(unittest.TestCase):
    def test_descriptor_is_owned_by_sabrican(self) -> None:
        descriptor = openclaw_bridge.describe_openclaw_helper_runtime()

        self.assertEqual(descriptor["owner_persona"], "sabrican")
        self.assertEqual(descriptor["mode"], "helper_only")
        self.assertFalse(descriptor["canonical_runtime"])
        self.assertIn("openclaw_integrator", descriptor["sub_agents"])
        self.assertIn("gateway_health", descriptor["skill_surfaces"])

    def test_health_snapshot_reports_helper_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile_dir = Path(tmp) / "main"
            profile_dir.mkdir(parents=True, exist_ok=True)
            auth_dir = profile_dir / "agent"
            auth_dir.mkdir(parents=True, exist_ok=True)
            (auth_dir / "auth-profiles.json").write_text('{"profiles": {}}', encoding="utf-8")

            with patch.object(openclaw_bridge, "OPENCLAW_COMMAND", "openclaw.cmd"):
                with patch.object(openclaw_bridge, "OPENCLAW_PROFILE", ""):
                    with patch.object(openclaw_bridge, "JARVIS_CHAT_ID", "12345"):
                        with patch(
                            "server.openclaw_bridge.shutil.which",
                            return_value="C:\\tools\\openclaw.cmd",
                        ):
                            with patch(
                                "server.openclaw_bridge._profile_state_path",
                                return_value=profile_dir,
                            ):
                                snapshot = (
                                    openclaw_bridge.build_openclaw_health_snapshot()
                                )

        self.assertEqual(snapshot["status"], "healthy")
        self.assertEqual(snapshot["owner_persona"], "sabrican")
        self.assertTrue(snapshot["capabilities"]["gateway_health"]["ok"])
        self.assertTrue(snapshot["capabilities"]["channel_delivery"]["ok"])
        self.assertTrue(snapshot["capabilities"]["auth_profile_sync"]["ok"])
        self.assertIn("wrapper_control", snapshot["capabilities"])

    def test_run_agent_task_returns_blocked_when_policy_gate_holds_action(self) -> None:
        blocked = PolicyDecision(
            allowed=False,
            status="approval_required",
            risk="high",
            reason="openclaw-task-requires-approval",
            action="openclaw_agent_run",
            audit_id="audit-1",
            approval_id="appr-42",
        )

        with patch.object(openclaw_bridge, "JARVIS_CHAT_ID", "12345"):
            with patch(
                "server.openclaw_bridge.build_openclaw_health_snapshot",
                return_value={"auth": {"warnings": ["api-key-profile-present"]}},
            ):
                with patch(
                    "server.openclaw_bridge.evaluate_openclaw_task",
                    return_value=blocked,
                ):
                    result = asyncio.run(
                        openclaw_bridge.run_agent_task(
                            "deploy bridge.py with token rotation",
                            deliver=True,
                        )
                    )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["error"], "policy_gate")
        self.assertEqual(result["approval_id"], "appr-42")
        self.assertEqual(result["risk"], "high")


if __name__ == "__main__":
    unittest.main()
