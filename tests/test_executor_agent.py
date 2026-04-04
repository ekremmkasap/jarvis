from __future__ import annotations

import unittest

from server.agents.executor_agent import ExecutorAgent
from server.agents.tool_registry import ToolRegistry


class ExecutorAgentTests(unittest.TestCase):
    def test_execute_step_runs_three_skills_sequentially(self) -> None:
        registry = ToolRegistry()
        calls: list[str] = []

        def read_tool(payload: dict) -> dict:
            calls.append("read")
            return {"text": payload.get("text", "")}

        def summarize_tool(payload: dict) -> dict:
            calls.append("summarize")
            text = str(payload.get("text") or "")
            return {"summary": text[:5]}

        def notify_tool(payload: dict) -> dict:
            calls.append("notify")
            return {"sent": bool(payload.get("send"))}

        registry.register("read", read_tool)
        registry.register("summarize", summarize_tool)
        registry.register("notify", notify_tool)
        agent = ExecutorAgent(registry)

        step_1 = {"action": "read", "params": {"text": "jarvis week one"}}
        out_1 = agent.execute_step(step_1, run_id="r-1")
        self.assertTrue(out_1["ok"])
        self.assertEqual(out_1["result"]["text"], "jarvis week one")

        step_2 = {"action": "summarize", "params": {"text": out_1["result"]["text"]}}
        out_2 = agent.execute_step(step_2, run_id="r-1")
        self.assertTrue(out_2["ok"])
        self.assertEqual(out_2["result"]["summary"], "jarvi")

        step_3 = {"action": "notify", "params": {"send": True, "body": out_2["result"]["summary"]}}
        out_3 = agent.execute_step(step_3, run_id="r-1")
        self.assertTrue(out_3["ok"])
        self.assertTrue(out_3["result"]["sent"])

        self.assertEqual(calls, ["read", "summarize", "notify"])

    def test_execute_step_tracks_error_for_unknown_tool(self) -> None:
        registry = ToolRegistry()
        agent = ExecutorAgent(registry)

        out = agent.execute_step({"action": "missing", "params": {}}, run_id="r-err")
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"]["type"], "KeyError")
        self.assertIn("tool_not_registered:missing", out["error"]["message"])


if __name__ == "__main__":
    unittest.main()

