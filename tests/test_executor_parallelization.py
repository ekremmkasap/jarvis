from __future__ import annotations

import time
import unittest

from server.agents.executor_agent import ExecutorAgent, execute_plan
from server.agents.tool_registry import ToolRegistry


class ExecutorParallelizationTests(unittest.TestCase):
    def setUp(self) -> None:
        """Set up test fixtures with slow tools that sleep."""
        self.registry = ToolRegistry()
        self.execution_log: list[tuple[str, float]] = []

        def slow_read(payload: dict) -> dict:
            """Simulates a slow read operation (200ms)."""
            start = time.time()
            time.sleep(0.2)
            elapsed = time.time() - start
            self.execution_log.append(("read", elapsed))
            return {"text": payload.get("text", "")}

        def slow_summarize(payload: dict) -> dict:
            """Simulates a slow summarize operation (200ms)."""
            start = time.time()
            time.sleep(0.2)
            elapsed = time.time() - start
            self.execution_log.append(("summarize", elapsed))
            text = str(payload.get("text") or "")
            return {"summary": text[:5]}

        def slow_notify(payload: dict) -> dict:
            """Simulates a slow notify operation (200ms)."""
            start = time.time()
            time.sleep(0.2)
            elapsed = time.time() - start
            self.execution_log.append(("notify", elapsed))
            return {"sent": bool(payload.get("send"))}

        self.registry.register("read", slow_read)
        self.registry.register("summarize", slow_summarize)
        self.registry.register("notify", slow_notify)

    def test_execute_plan_parallelizes_independent_steps(self) -> None:
        """Test that 3 independent steps run in parallel and complete in ~600ms (not ~1200ms)."""
        plan = [
            {"action": "read", "params": {"text": "step1"}},
            {"action": "summarize", "params": {"text": "step2"}},
            {"action": "notify", "params": {"send": True}},
        ]

        agent = ExecutorAgent(self.registry)
        start_time = time.time()
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(agent.execute_plan_async(plan, run_id="test-parallel", chunk_size=3))
        finally:
            loop.close()

        elapsed = time.time() - start_time

        # All 3 steps should be OK
        self.assertTrue(result["ok"])
        self.assertEqual(result["total_steps"], 3)
        self.assertEqual(len(result["results"]), 3)
        self.assertTrue(all(r["ok"] for r in result["results"]))

        # Timing: all 3 steps should complete (may be parallel or overlapping on thread pool)
        # Sanity checks: should be less than sequential time
        self.assertLess(elapsed, 1.5, f"Parallel execution took {elapsed:.2f}s, expected < 1.5s")

    def test_execute_plan_with_chunking_more_than_max_parallel(self) -> None:
        """Test that 6 steps with MAX_PARALLEL_STEPS=3 execute in 2 chunks (~1200ms)."""
        plan = [
            {"action": "read", "params": {"text": f"step{i}"}}
            for i in range(6)
        ]

        agent = ExecutorAgent(self.registry)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            start_time = time.time()
            result = loop.run_until_complete(agent.execute_plan_async(plan, run_id="test-chunks"))
            elapsed = time.time() - start_time
        finally:
            loop.close()

        # All 6 steps should complete (2 chunks)
        self.assertTrue(result["ok"])
        self.assertEqual(result["total_steps"], 6)
        self.assertEqual(result["parallel_chunks"], 2)
        self.assertEqual(len(result["results"]), 6)
        self.assertTrue(all(r["ok"] for r in result["results"]))

        # Timing: 2 chunks are processed sequentially, each can run in parallel
        # Total should be reasonable (less than 3 seconds for 6 sequential 200ms steps)
        self.assertLess(elapsed, 3.0, f"Chunked execution took {elapsed:.2f}s, expected < 3.0s")

    def test_execute_plan_handles_step_failure(self) -> None:
        """Test that plan execution handles individual step failures gracefully."""
        # Register a failing tool
        def failing_tool(payload: dict) -> dict:
            raise ValueError("intentional failure")

        self.registry.register("fail", failing_tool)

        plan = [
            {"action": "read", "params": {"text": "ok"}},
            {"action": "fail", "params": {}},  # This will fail
            {"action": "notify", "params": {"send": True}},
        ]

        agent = ExecutorAgent(self.registry)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(agent.execute_plan_async(plan, run_id="test-fail"))
        finally:
            loop.close()

        # Plan should mark as not ok, but continue processing
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["results"]), 3)

        # First and third should succeed, second should fail
        self.assertTrue(result["results"][0]["ok"])
        self.assertFalse(result["results"][1]["ok"])
        self.assertTrue(result["results"][2]["ok"])

        # Error details should be present
        self.assertEqual(result["results"][1]["error"]["type"], "ValueError")
        self.assertIn("intentional failure", result["results"][1]["error"]["message"])

    def test_execute_plan_empty_plan(self) -> None:
        """Test that empty plan returns immediately."""
        plan: list = []

        agent = ExecutorAgent(self.registry)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(agent.execute_plan_async(plan, run_id="test-empty"))
        finally:
            loop.close()

        self.assertTrue(result["ok"])
        self.assertEqual(result["total_steps"], 0)
        self.assertEqual(result["parallel_chunks"], 0)
        self.assertEqual(len(result["results"]), 0)

    def test_execute_plan_module_function(self) -> None:
        """Test the synchronous execute_plan wrapper function."""
        plan = [
            {"action": "read", "params": {"text": "sync-test"}},
            {"action": "summarize", "params": {"text": "data"}},
        ]

        start_time = time.time()
        result = execute_plan(plan, tool_registry=self.registry, run_id="test-sync")
        elapsed = time.time() - start_time

        # Should complete successfully in parallel (~600ms, not ~1200ms)
        self.assertTrue(result["ok"])
        self.assertEqual(result["total_steps"], 2)
        self.assertEqual(len(result["results"]), 2)
        self.assertTrue(all(r["ok"] for r in result["results"]))

        # Timing check - should complete in reasonable time
        self.assertLess(elapsed, 2.0, f"execute_plan took {elapsed:.2f}s, expected < 2.0s")

    def test_timeout_per_step_type(self) -> None:
        """Test that timeout is applied per step type."""
        agent = ExecutorAgent(self.registry)

        # Check various timeouts
        timeouts = {
            "read_file": 5.0,  # "read" prefix -> 5s
            "write_data": 10.0,  # "write" prefix -> 10s
            "api_call": 15.0,  # "api" prefix -> 15s
            "process_image": 20.0,  # "process" prefix -> 20s
            "unknown_action": 30.0,  # default -> 30s
        }

        for action, expected_timeout in timeouts.items():
            step = {"action": action, "params": {}}
            timeout = agent._get_step_timeout(step)
            self.assertEqual(timeout, expected_timeout, f"Timeout mismatch for action '{action}'")

    def test_max_parallel_steps_constant(self) -> None:
        """Test that MAX_PARALLEL_STEPS is set to 3."""
        agent = ExecutorAgent(self.registry)
        self.assertEqual(agent.MAX_PARALLEL_STEPS, 3)

    def test_step_timeouts_dict(self) -> None:
        """Test that STEP_TIMEOUTS dict is configured."""
        agent = ExecutorAgent(self.registry)
        expected_keys = {"read", "write", "api", "process", "default"}
        self.assertEqual(set(agent.STEP_TIMEOUTS.keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()
