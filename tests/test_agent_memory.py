from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from server.agents.canonical.debug_agent import DebugAgent
from server.agents.canonical.planner import PlannerAgent


class AgentMemoryTests(unittest.TestCase):
    def test_remember_writes_json_file(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root_dir = Path(temp_dir)
            agent = PlannerAgent(root_dir=root_dir)

            agent.remember("key", "value")

            memory_path = root_dir / "state" / "agent_memory" / "planner.json"
            self.assertTrue(memory_path.exists())
            payload = json.loads(memory_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["key"], "value")

    def test_recall_returns_saved_value(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            agent = PlannerAgent(root_dir=Path(temp_dir))
            agent.remember("key", "value")

            self.assertEqual(agent.recall("key"), "value")

    def test_recall_returns_none_for_missing_key(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            agent = PlannerAgent(root_dir=Path(temp_dir))

            self.assertIsNone(agent.recall("missing"))

    def test_agents_use_separate_memory_files(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            root_dir = Path(temp_dir)
            planner = PlannerAgent(root_dir=root_dir)
            debug = DebugAgent(root_dir=root_dir)

            planner.remember("shared", "planner-value")
            debug.remember("shared", "debug-value")

            self.assertEqual(planner.recall("shared"), "planner-value")
            self.assertEqual(debug.recall("shared"), "debug-value")
            self.assertNotEqual(planner._memory_path, debug._memory_path)

    def test_run_persists_last_task_and_timestamp(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
            agent = PlannerAgent(root_dir=Path(temp_dir))

            asyncio.run(agent.run("Test gorevi", {}))

            self.assertEqual(agent.recall("last_task"), "Test gorevi")
            self.assertIsNotNone(agent.recall("last_run"))


if __name__ == "__main__":
    unittest.main()
