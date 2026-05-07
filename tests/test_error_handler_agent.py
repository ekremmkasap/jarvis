from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from server.agents.error_handler_agent import ErrorHandlerAgent, RecoveryDecision


class ErrorHandlerAgentTests(unittest.TestCase):
    def test_replan_then_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_dir = Path(tmp)
            agent = ErrorHandlerAgent(
                max_retries=0,
                max_replan_attempts=2,
                log_dir=log_dir,
                now_fn=lambda: datetime(2026, 4, 4, 0, 0, 0, tzinfo=timezone.utc),
            )
            try:
                def execute_step(step: dict[str, str]) -> str:
                    if step["name"] == "bad_step":
                        raise ValueError("invalid action in plan step")
                    return f"ok:{step['name']}"

                def replan_step(step: dict[str, str], error: Exception | str, attempt: int) -> dict[str, str]:
                    self.assertIn("invalid action", str(error))
                    self.assertEqual(attempt, 1)
                    return {"name": "fixed_step"}

                result = agent.execute_with_recovery(
                    step={"name": "bad_step"},
                    error=ValueError("invalid action in plan step"),
                    execute_step=execute_step,
                    replan_step=replan_step,
                )

                self.assertTrue(result.ok)
                self.assertEqual(result.decision, RecoveryDecision.REPLAN)
                self.assertEqual(result.output, "ok:fixed_step")
                self.assertEqual(result.replan_attempts, 1)
                self.assertEqual(agent.stats.recovered, 1)
                self.assertEqual(agent.stats.total_failures, 1)

                log_text = (log_dir / "error_handler_agent.log").read_text(encoding="utf-8")
                self.assertIn("ts=2026-04-04T00:00:00+00:00", log_text)
                self.assertIn("event=replanned", log_text)
                self.assertIn("event=recovered", log_text)
            finally:
                agent.close()

    def test_replan_capped_at_two_then_skip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = ErrorHandlerAgent(max_retries=0, max_replan_attempts=2, log_dir=Path(tmp))
            try:
                def execute_step(step: dict[str, str]) -> str:
                    raise RuntimeError("unsupported capability for this step")

                def replan_step(step: dict[str, str], error: Exception | str, attempt: int) -> dict[str, str]:
                    return {"name": f"still_bad_{attempt}"}

                result = agent.execute_with_recovery(
                    step={"name": "bad_step"},
                    error=RuntimeError("unsupported capability for this step"),
                    execute_step=execute_step,
                    replan_step=replan_step,
                )

                self.assertFalse(result.ok)
                self.assertEqual(result.decision, RecoveryDecision.SKIP)
                self.assertEqual(result.replan_attempts, 2)
                self.assertEqual(agent.stats.skipped, 1)
                self.assertEqual(agent.stats.total_failures, 1)
            finally:
                agent.close()


if __name__ == "__main__":
    unittest.main()
