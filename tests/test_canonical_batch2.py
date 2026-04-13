from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from server.agents.canonical import CANONICAL_AGENTS
from server.agents.canonical.debug_agent import DebugAgent
from server.agents.canonical.reviewer import ReviewerAgent


class FakeRouter:
    def __init__(self, response: str = "", ok: bool = False) -> None:
        self.response = response
        self.ok = ok

    def chat(self, **_: object) -> tuple[str, dict[str, object]]:
        return self.response, {
            "ok": self.ok,
            "selected_candidate": "fake/model",
            "fallback_used": False,
            "attempts": [],
        }


class CanonicalBatch2Tests(unittest.TestCase):
    def test_registry_contains_batch2_agents(self) -> None:
        self.assertTrue({"planner", "repo_analyst", "developer", "reviewer", "debug"}.issubset(set(CANONICAL_AGENTS.keys())))

    def test_reviewer_parses_llm_json(self) -> None:
        router = FakeRouter(
            response=json.dumps(
                {
                    "issues": [
                        {
                            "severity": "major",
                            "file": "server/bridge.py",
                            "title": "Unsafe shell call",
                            "details": "Shell execution path lacks validation.",
                        }
                    ],
                    "suggestions": ["Add input validation before shell execution."],
                    "severity_counts": {"critical": 0, "major": 1, "minor": 0},
                    "overall_verdict": "request_changes",
                }
            ),
            ok=True,
        )
        agent = ReviewerAgent(router=router)
        result = asyncio.run(agent.run("review diff", {}))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["overall_verdict"], "request_changes")
        self.assertEqual(result["severity_counts"]["major"], 1)
        self.assertEqual(result["issues"][0]["file"], "server/bridge.py")

    def test_reviewer_falls_back_on_secret_like_diff(self) -> None:
        diff_text = """
diff --git a/server/example.py b/server/example.py
index 1111111..2222222 100644
--- a/server/example.py
+++ b/server/example.py
@@
+API_TOKEN = "secret-value"
+print("debug")
"""
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            agent = ReviewerAgent(router=FakeRouter(), root_dir=Path(temp_dir))
            with patch.object(ReviewerAgent, "_run_command", side_effect=["", diff_text]):
                result = asyncio.run(agent.run("review working tree", {}))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["overall_verdict"], "request_changes")
        self.assertGreaterEqual(result["severity_counts"]["critical"], 1)
        self.assertTrue(result["issues"])

    def test_debug_parses_llm_json(self) -> None:
        router = FakeRouter(
            response=json.dumps(
                {
                    "error_type": "TypeError",
                    "likely_cause": "Nullable payload field reached arithmetic branch.",
                    "affected_files": ["server/task_runner.py"],
                    "suggested_fix": "Validate the payload before the branch.",
                    "confidence": "high",
                }
            ),
            ok=True,
        )
        agent = DebugAgent(router=router)
        result = asyncio.run(agent.run("debug this", {"error_message": "TypeError: unsupported operand type"}))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["error_type"], "TypeError")
        self.assertEqual(result["confidence"], "high")
        self.assertIn("server/task_runner.py", result["affected_files"])

    def test_debug_falls_back_from_stack_trace(self) -> None:
        agent = DebugAgent(router=FakeRouter())
        stack_trace = """
Traceback (most recent call last):
  File "server/bridge.py", line 10, in <module>
    from missing_module import thing
ModuleNotFoundError: No module named 'missing_module'
"""
        result = asyncio.run(agent.run("module import issue", {"stack_trace": stack_trace}))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["error_type"], "ImportError")
        self.assertEqual(result["confidence"], "high")
        self.assertIn("server/bridge.py", result["affected_files"])
        self.assertIn("missing module", result["likely_cause"].lower())


if __name__ == "__main__":
    unittest.main()
