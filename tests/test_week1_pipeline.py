from __future__ import annotations

import unittest

from server.agents.error_handler_agent import ErrorHandlerAgent
from server.agents.executor_agent import ExecutorAgent
from server.agents.task_planner_agent import TaskPlannerAgent
from server.agents.tool_registry import ToolRegistry
from server.agents.week1_pipeline import Week1Pipeline
from server.voice.voice_layer import VoiceConversationManager


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def generate_content(self, *, model: str, contents: str) -> _FakeResponse:
        return _FakeResponse(f"voice:{contents}")


class _FakeClient:
    def __init__(self) -> None:
        self.models = _FakeModels()


class Week1PipelineTests(unittest.TestCase):
    def test_voice_input_flows_through_planner_executor_and_error_handler(self) -> None:
        registry = ToolRegistry()
        call_log: list[str] = []
        implement_failures = {"count": 0}

        def analyze_tool(payload: dict) -> dict:
            call_log.append("analyze")
            return {"analysis": payload["description"]}

        def implement_tool(payload: dict) -> dict:
            call_log.append("implement")
            if implement_failures["count"] == 0:
                implement_failures["count"] += 1
                raise RuntimeError("unsupported capability for implement step")
            return {"implementation": payload["description"]}

        def test_tool(payload: dict) -> dict:
            call_log.append("test")
            return {"tested": True}

        def verify_tool(payload: dict) -> dict:
            call_log.append("verify")
            return {"verified": True, "replanned_from": payload.get("replanned_from")}

        registry.register("analyze", analyze_tool)
        registry.register("implement", implement_tool)
        registry.register("test", test_tool)
        registry.register("verify", verify_tool)

        pipeline = Week1Pipeline(
            planner=TaskPlannerAgent(),
            executor=ExecutorAgent(registry),
            error_handler=ErrorHandlerAgent(max_retries=0, max_replan_attempts=2),
            tool_registry=registry,
        )
        voice = VoiceConversationManager()
        voice.start_session("42", client=_FakeClient())

        response = voice.handle_message(
            "42",
            "task: Build a three step plan",
            task_runner=lambda goal: pipeline.run(
                goal,
                requested_actions=["analyze", "implement", "test"],
            ),
        )

        self.assertIn("Task flow:", response["reply"])
        task_result = response["task_result"]
        self.assertTrue(task_result["ok"])
        self.assertEqual(task_result["recoveries"][0]["decision"], "REPLAN")
        self.assertEqual(call_log, ["analyze", "implement", "verify", "test"])


if __name__ == "__main__":
    unittest.main()
