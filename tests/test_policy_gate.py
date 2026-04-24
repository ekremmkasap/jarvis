from __future__ import annotations

import unittest
from unittest.mock import patch

from server.security import policy_gate


class PolicyGateTests(unittest.TestCase):
    def test_safe_shell_allows_allowlisted_command(self) -> None:
        decision = policy_gate.evaluate_shell_command(
            "dir C:/Users/sergen/Desktop",
            full_access=False,
            source="test",
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, "allowed")
        self.assertEqual(decision.risk, "low")

    def test_full_shell_requires_approval_for_unrestricted_command(self) -> None:
        with patch(
            "server.security.policy_gate._request_approval",
            return_value={"id": "appr-1", "status": "pending"},
        ):
            decision = policy_gate.evaluate_shell_command(
                "git status",
                full_access=True,
                source="test",
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "approval_required")
        self.assertEqual(decision.approval_id, "appr-1")

    def test_dangerous_shell_pattern_is_denied(self) -> None:
        decision = policy_gate.evaluate_shell_command(
            "rm -rf /",
            full_access=True,
            source="test",
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "denied")
        self.assertEqual(decision.risk, "critical")

    def test_openclaw_sensitive_task_requests_approval(self) -> None:
        with patch(
            "server.security.policy_gate._request_approval",
            return_value={"id": "appr-2", "status": "pending"},
        ):
            decision = policy_gate.evaluate_openclaw_task(
                "deploy bridge.py with token rotation",
                deliver=True,
                source="test",
                runtime_warnings=["api-key-profile-present"],
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "approval_required")
        self.assertEqual(decision.risk, "high")
        self.assertEqual(decision.approval_id, "appr-2")

    def test_pc_open_app_terminal_requires_approval(self) -> None:
        with patch(
            "server.security.policy_gate._request_approval",
            return_value={"id": "appr-3", "status": "pending"},
        ):
            decision = policy_gate.evaluate_pc_action(
                "ac",
                action="open_app",
                args="powershell",
                persona_id="sabrican",
                chat_id=77,
                rule={"action": "open_app"},
                source="test",
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "approval_required")
        self.assertEqual(decision.risk, "high")
        self.assertEqual(decision.approval_id, "appr-3")

    def test_pc_low_risk_status_command_is_allowed(self) -> None:
        decision = policy_gate.evaluate_pc_action(
            "pc-durum",
            action="system_status",
            args="",
            persona_id="sabrican",
            chat_id=77,
            rule={"action": "system_status"},
            source="test",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, "allowed")
        self.assertEqual(decision.risk, "low")

    def test_persona_matrix_denies_shell_for_content_persona(self) -> None:
        decision = policy_gate.evaluate_shell_command(
            "dir C:/Users/sergen",
            full_access=False,
            source="test",
            persona_id="sabri",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "denied")
        self.assertEqual(decision.reason, "persona-policy-denied")
        self.assertEqual(decision.metadata.get("persona_matrix"), "deny")

    def test_persona_matrix_denies_pc_action_for_luna(self) -> None:
        decision = policy_gate.evaluate_pc_action(
            "pc-durum",
            action="system_status",
            args="",
            persona_id="luna",
            chat_id=5,
            rule={"action": "system_status"},
            source="test",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "denied")
        self.assertEqual(decision.reason, "persona-policy-denied")

    def test_persona_matrix_requires_approval_for_luna_openclaw_helper(self) -> None:
        with patch(
            "server.security.policy_gate._request_approval",
            return_value={"id": "appr-luna", "status": "pending"},
        ):
            decision = policy_gate.evaluate_openclaw_task(
                "simple helper task",
                deliver=False,
                source="test",
                persona_id="luna",
            )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "approval_required")
        self.assertEqual(decision.reason, "persona-policy-requires-approval")
        self.assertEqual(decision.approval_id, "appr-luna")

    def test_persona_matrix_denies_operator_action_for_content_persona(self) -> None:
        decision = policy_gate.evaluate_operator_action(
            "anydesk_accept",
            "test payload",
            source="test",
            risk="high",
            require_approval=False,
            persona_id="buse",
        )

        self.assertFalse(decision.allowed)
        self.assertEqual(decision.status, "denied")
        self.assertEqual(decision.reason, "persona-policy-denied")

    def test_persona_matrix_allows_sabrican_openclaw_helper(self) -> None:
        decision = policy_gate.evaluate_openclaw_task(
            "analyze sentiment",
            deliver=False,
            source="test",
            persona_id="sabrican",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, "allowed")
        self.assertEqual(decision.metadata.get("persona_matrix"), "allow")

    def test_custom_low_risk_operator_class_defaults_to_allow(self) -> None:
        decision = policy_gate.evaluate_operator_action(
            "dreams_snapshot",
            "capture rem report",
            source="test",
            risk="low",
            require_approval=False,
            persona_id="sabrican",
            action_class="dreams.snapshot",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, "allowed")
        self.assertEqual(decision.metadata.get("persona_matrix"), "allow")

    def test_default_persona_preserves_baseline_decision(self) -> None:
        decision = policy_gate.evaluate_shell_command(
            "dir",
            full_access=False,
            source="test",
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.status, "allowed")
        self.assertEqual(decision.metadata.get("persona_id"), "jarvis")


if __name__ == "__main__":
    unittest.main()
