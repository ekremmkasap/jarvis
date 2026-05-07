from __future__ import annotations

import unittest

from server.agents.action_registry import ActionRegistry
from server.agents.task_planner_agent import TaskPlannerAgent


class TaskPlannerAgentTests(unittest.TestCase):
    def test_plan_three_steps_and_validate_actions(self) -> None:
        registry = ActionRegistry.from_actions(["analyze", "implement", "test"])
        planner = TaskPlannerAgent(action_registry=registry)

        result = planner.plan(
            "Ship a small feature safely",
            requested_actions=["analyze", "implement", "test"],
        )

        self.assertTrue(result.ok)
        self.assertEqual(len(result.steps), 3)
        self.assertTrue(all(registry.is_allowed(step.action) for step in result.steps))

    def test_plan_never_exceeds_seven_steps(self) -> None:
        planner = TaskPlannerAgent()
        result = planner.plan("Build full release workflow", max_steps=20)

        self.assertTrue(result.ok)
        self.assertLessEqual(len(result.steps), 7)


if __name__ == "__main__":
    unittest.main()

