"""
Integration tests for Vision Analyzer with ExecutorAgent
Tests UI validation hooks in executor for vision-based step execution
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.agents.executor_agent import ExecutorAgent
from server.agents.tool_registry import ToolRegistry
from server.agents.vision_analyzer import VisionAnalyzer


class VisionExecutorIntegrationTests(unittest.TestCase):
    """Test suite for Vision Analyzer integration with ExecutorAgent."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.registry = ToolRegistry()
        self.test_image_path = Path(__file__).parent / "fixtures" / "test_screenshot.png"
        self.test_image_path.parent.mkdir(parents=True, exist_ok=True)

        # Create minimal test PNG
        png_data = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
            b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        self.test_image_path.write_bytes(png_data)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        if self.test_image_path.exists():
            self.test_image_path.unlink()

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_executor_with_vision_analyzer_integration(self, mock_genai: MagicMock) -> None:
        """Test ExecutorAgent with integrated VisionAnalyzer."""
        # Setup vision analyzer mock
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "current_state": {"page_status": "ready"},
                "detected_changes": [],
                "user_actions_available": ["click"],
            }
        )
        mock_model.generate_content.return_value = mock_response
        mock_genai.upload_file.return_value = MagicMock()

        # Setup registry with a vision-enabled action
        def click_button(payload: dict) -> dict:
            return {"clicked": True, "button": payload.get("button_id")}

        self.registry.register("vision_click", click_button)

        # Create executor with vision analyzer
        vision_analyzer = VisionAnalyzer(api_key="test-key")
        executor = ExecutorAgent(self.registry, vision_analyzer=vision_analyzer)

        # Execute step with vision validation
        step = {
            "action": "vision_click",
            "params": {
                "button_id": "submit-btn",
                "screenshot_path": str(self.test_image_path),
            },
        }

        result = executor.execute_step(step, run_id="test-run-1")

        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "vision_click")
        self.assertTrue(result["result"]["clicked"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_executor_without_vision_analyzer(self, mock_genai: MagicMock) -> None:
        """Test ExecutorAgent works normally without vision analyzer."""
        # Setup registry
        def simple_action(payload: dict) -> dict:
            return {"result": "success"}

        self.registry.register("simple_action", simple_action)

        # Create executor without vision analyzer
        executor = ExecutorAgent(self.registry)

        step = {"action": "simple_action", "params": {}}
        result = executor.execute_step(step, run_id="test-run-2")

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"]["result"], "success")

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_executor_vision_hook_graceful_failure(self, mock_genai: MagicMock) -> None:
        """Test that vision validation failure doesn't prevent step execution."""
        # Setup vision analyzer mock to fail
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps({})
        mock_model.generate_content.return_value = mock_response
        mock_genai.upload_file.return_value = MagicMock()

        # Setup registry
        def action_with_vision(payload: dict) -> dict:
            return {"executed": True}

        self.registry.register("vision_action", action_with_vision)

        # Create executor with vision analyzer
        vision_analyzer = VisionAnalyzer(api_key="test-key")
        executor = ExecutorAgent(self.registry, vision_analyzer=vision_analyzer)

        step = {
            "action": "vision_action",
            "params": {"screenshot_path": str(self.test_image_path)},
        }

        result = executor.execute_step(step, run_id="test-run-3")

        # Step should still execute even if vision validation fails
        self.assertTrue(result["ok"])
        self.assertTrue(result["result"]["executed"])

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_executor_vision_state_caching(self, mock_genai: MagicMock) -> None:
        """Test that executor caches visual state between steps."""
        # Setup vision analyzer mock
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        # First call returns ready state
        mock_response_1 = MagicMock()
        mock_response_1.text = json.dumps(
            {
                "current_state": {"page_status": "ready"},
                "detected_changes": ["form_loaded"],
            }
        )

        # Second call should have previous state available
        mock_response_2 = MagicMock()
        mock_response_2.text = json.dumps(
            {
                "current_state": {"page_status": "submitted"},
                "detected_changes": ["form_submitted"],
            }
        )

        mock_model.generate_content.side_effect = [mock_response_1, mock_response_2]
        mock_genai.upload_file.return_value = MagicMock()

        # Setup registry
        def action_1(payload: dict) -> dict:
            return {"step": 1}

        def action_2(payload: dict) -> dict:
            return {"step": 2}

        self.registry.register("vision_step_1", action_1)
        self.registry.register("vision_step_2", action_2)

        # Create executor with vision analyzer
        vision_analyzer = VisionAnalyzer(api_key="test-key")
        executor = ExecutorAgent(self.registry, vision_analyzer=vision_analyzer)

        # Execute first step
        step_1 = {
            "action": "vision_step_1",
            "params": {"screenshot_path": str(self.test_image_path)},
        }
        result_1 = executor.execute_step(step_1, run_id="test-run-4")

        self.assertTrue(result_1["ok"])
        self.assertIsNotNone(executor._last_visual_state)

        # Execute second step
        step_2 = {
            "action": "vision_step_2",
            "params": {"screenshot_path": str(self.test_image_path)},
        }
        result_2 = executor.execute_step(step_2, run_id="test-run-4")

        self.assertTrue(result_2["ok"])

    def test_executor_vision_skip_without_screenshot(self) -> None:
        """Test that vision validation is skipped if no screenshot provided."""
        # Setup registry
        def action(payload: dict) -> dict:
            return {"executed": True}

        self.registry.register("vision_action", action)

        # Mock vision analyzer that should NOT be called
        mock_vision = MagicMock(spec=VisionAnalyzer)

        executor = ExecutorAgent(self.registry, vision_analyzer=mock_vision)

        step = {
            "action": "vision_action",
            "params": {},  # No screenshot_path
        }

        result = executor.execute_step(step, run_id="test-run-5")

        # Action should execute without vision validation
        self.assertTrue(result["ok"])
        mock_vision.track_visual_state.assert_not_called()

    @patch("server.agents.vision_analyzer.genai")
    @patch("server.agents.vision_analyzer.HAS_GEMINI", True)
    def test_executor_multiple_vision_steps(self, mock_genai: MagicMock) -> None:
        """Test executor handles multiple vision-enabled steps."""
        # Setup vision analyzer mock
        mock_model = MagicMock()
        mock_genai.GenerativeModel.return_value = mock_model

        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "current_state": {"page_status": "ready"},
                "detected_changes": [],
                "user_actions_available": [],
            }
        )
        mock_model.generate_content.return_value = mock_response
        mock_genai.upload_file.return_value = MagicMock()

        # Setup registry
        actions_executed = []

        def vision_click(payload: dict) -> dict:
            actions_executed.append("click")
            return {"clicked": True}

        def vision_fill_form(payload: dict) -> dict:
            actions_executed.append("fill_form")
            return {"filled": True}

        def vision_submit(payload: dict) -> dict:
            actions_executed.append("submit")
            return {"submitted": True}

        self.registry.register("vision_click", vision_click)
        self.registry.register("vision_fill_form", vision_fill_form)
        self.registry.register("vision_submit", vision_submit)

        # Create executor with vision analyzer
        vision_analyzer = VisionAnalyzer(api_key="test-key")
        executor = ExecutorAgent(self.registry, vision_analyzer=vision_analyzer)

        # Execute sequence of vision-enabled steps
        steps = [
            {
                "action": "vision_click",
                "params": {"target": "input", "screenshot_path": str(self.test_image_path)},
            },
            {
                "action": "vision_fill_form",
                "params": {"form_id": "login", "screenshot_path": str(self.test_image_path)},
            },
            {
                "action": "vision_submit",
                "params": {"form_id": "login", "screenshot_path": str(self.test_image_path)},
            },
        ]

        for step in steps:
            result = executor.execute_step(step, run_id="test-run-6")
            self.assertTrue(result["ok"])

        # Verify all actions executed in order
        self.assertEqual(actions_executed, ["click", "fill_form", "submit"])


if __name__ == "__main__":
    unittest.main()
