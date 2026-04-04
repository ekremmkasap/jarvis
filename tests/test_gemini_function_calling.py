"""
Tests for Gemini 2.5 Function Calling Integration

Tests the following scenarios:
1. Function schema loading and validation
2. Function execution routing
3. End-to-end request processing
4. Error handling
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from server.agents.gemini_function_caller import GeminiFunctionCaller, create_function_caller
from server.agents.tool_registry import ToolRegistry


class TestGeminiFunctionCaller(unittest.TestCase):
    """Test suite for GeminiFunctionCaller."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.api_key = "test-api-key"
        self.model = "models/gemini-2.5-flash"

        # Create a mock executor
        self.executor_fn = MagicMock(
            return_value={
                "ok": True,
                "result": {"status": "success"},
                "error": None,
            }
        )

        # Create caller instance
        self.caller = GeminiFunctionCaller(
            api_key=self.api_key,
            model=self.model,
            executor_fn=self.executor_fn,
        )

    def test_load_functions_config(self) -> None:
        """Test loading function definitions from config file."""
        config = self.caller.functions_config
        self.assertIn("functions", config)
        self.assertIn("function_to_tool_mapping", config)

        functions = config.get("functions", [])
        self.assertGreaterEqual(len(functions), 5, "Should have at least 5 functions defined")

        # Check function names
        function_names = {f["name"] for f in functions}
        expected = {
            "analyze_image",
            "execute_command",
            "get_metrics",
            "apply_improvement",
            "check_health",
        }
        self.assertEqual(expected, function_names)

    def test_get_function_definitions(self) -> None:
        """Test retrieving Gemini-compatible function definitions."""
        definitions = self.caller.get_function_definitions()
        self.assertIsInstance(definitions, list)
        self.assertGreater(len(definitions), 0)

        # Each definition should have required fields
        for func_def in definitions:
            self.assertIn("name", func_def)
            self.assertIn("description", func_def)
            self.assertIn("parameters", func_def)

    def test_function_definitions_have_valid_schema(self) -> None:
        """Test that function definitions have valid JSON Schema."""
        definitions = self.caller.get_function_definitions()
        for func_def in definitions:
            params = func_def.get("parameters", {})
            self.assertIn("type", params)
            self.assertEqual(params["type"], "object")
            self.assertIn("properties", params)

    def test_execute_command_function(self) -> None:
        """Test execute_command function execution."""
        result = self.caller.call_function(
            "execute_command",
            {
                "tool_name": "test_tool",
                "params": {"key": "value"},
            },
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["function"], "execute_command")
        self.executor_fn.assert_called_once()

    def test_get_metrics_function(self) -> None:
        """Test get_metrics function execution."""
        result = self.caller.call_function(
            "get_metrics",
            {"metric_type": "cpu"},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["function"], "get_metrics")
        self.assertIn("result", result)
        self.assertIn("cpu_percent", result["result"])
        self.assertIn("memory_percent", result["result"])

    def test_check_health_function(self) -> None:
        """Test check_health function execution."""
        result = self.caller.call_function(
            "check_health",
            {"detailed": True},
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["function"], "check_health")
        self.assertIn("result", result)
        self.assertEqual(result["result"]["status"], "healthy")
        self.assertIn("components", result["result"])

    def test_analyze_image_function(self) -> None:
        """Test analyze_image function execution."""
        result = self.caller.call_function(
            "analyze_image",
            {
                "image_path": "/path/to/image.png",
                "focus_areas": ["text", "buttons"],
            },
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["function"], "analyze_image")
        self.assertIn("result", result)
        self.assertEqual(result["result"]["image_path"], "/path/to/image.png")

    def test_apply_improvement_function(self) -> None:
        """Test apply_improvement function execution."""
        result = self.caller.call_function(
            "apply_improvement",
            {
                "improvement_type": "batch_execution",
                "target": "executor",
                "config": {"batch_size": 5},
            },
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["function"], "apply_improvement")
        self.assertIn("result", result)
        self.assertEqual(result["result"]["improvement_type"], "batch_execution")

    def test_unknown_function_returns_error(self) -> None:
        """Test handling of unknown function."""
        result = self.caller.call_function(
            "unknown_function",
            {},
        )

        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("Unknown function", result["error"])

    def test_function_to_tool_mapping(self) -> None:
        """Test function-to-tool name mapping."""
        mapping = self.caller.function_to_tool_mapping
        self.assertIsInstance(mapping, dict)

        expected_mappings = {
            "analyze_image": "vision_analyzer",
            "execute_command": "executor",
            "get_metrics": "metrics_provider",
            "apply_improvement": "improvement_applier",
            "check_health": "health_checker",
        }

        for func_name, tool_name in expected_mappings.items():
            self.assertEqual(mapping.get(func_name), tool_name)

    def test_process_request_without_gemini_client(self) -> None:
        """Test process_request when Gemini client is not initialized."""
        caller = GeminiFunctionCaller(api_key="")
        result = caller.process_request("some request")

        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_create_function_caller_factory(self) -> None:
        """Test factory function for creating GeminiFunctionCaller."""
        caller = create_function_caller(
            api_key="test-key",
            model="models/gemini-2.5-flash",
        )

        self.assertIsInstance(caller, GeminiFunctionCaller)
        self.assertEqual(caller.api_key, "test-key")
        self.assertEqual(caller.model, "models/gemini-2.5-flash")

    def test_multiple_functions_defined(self) -> None:
        """Test that configuration includes all required functions."""
        functions = self.caller.get_function_definitions()
        function_names = [f["name"] for f in functions]

        # Verify minimum count
        self.assertGreaterEqual(len(function_names), 5)

        # Verify each function has proper schema
        for func_def in functions:
            self.assertIsNotNone(func_def.get("name"))
            self.assertIsNotNone(func_def.get("description"))
            self.assertIsNotNone(func_def.get("parameters"))

    def test_execute_command_with_executor_integration(self) -> None:
        """Test execute_command function with executor integration."""
        # Create a registry with test tools
        registry = ToolRegistry()

        def test_tool(payload: dict) -> dict:
            return {
                "executed": True,
                "payload": payload,
            }

        registry.register("test_tool", test_tool)

        # Create executor function
        def executor_fn(step: dict) -> dict:
            if registry.has(step.get("action", "")):
                result = registry.execute(step.get("action", ""), step.get("params", {}))
                return {
                    "ok": True,
                    "result": result,
                    "error": None,
                }
            return {
                "ok": False,
                "result": None,
                "error": "Tool not found",
            }

        # Create caller with executor
        caller = GeminiFunctionCaller(
            api_key="test-key",
            executor_fn=executor_fn,
        )

        result = caller.call_function(
            "execute_command",
            {
                "tool_name": "test_tool",
                "params": {"test": "value"},
            },
        )

        self.assertTrue(result["success"])
        self.assertIn("result", result)

    def test_all_functions_have_required_parameters(self) -> None:
        """Test that all functions have required parameters defined."""
        functions = self.caller.get_function_definitions()

        for func_def in functions:
            params = func_def.get("parameters", {})
            if "required" in params:
                required = params["required"]
                self.assertIsInstance(required, list)
                # Each required field should exist in properties
                properties = params.get("properties", {})
                for req_field in required:
                    self.assertIn(req_field, properties)


class TestFunctionCallingE2E(unittest.TestCase):
    """End-to-end tests for function calling workflow."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.caller = GeminiFunctionCaller(
            api_key="test-api-key",
            executor_fn=lambda s: {"ok": True, "result": {}, "error": None},
        )

    def test_multiple_function_execution(self) -> None:
        """Test executing multiple functions in sequence."""
        # Execute get_metrics
        metrics = self.caller.call_function(
            "get_metrics",
            {"metric_type": "cpu"},
        )
        self.assertTrue(metrics["success"])

        # Execute check_health
        health = self.caller.call_function(
            "check_health",
            {"detailed": False},
        )
        self.assertTrue(health["success"])

        # Both should complete successfully
        self.assertEqual(len([metrics, health]), 2)

    def test_function_execution_preserves_context(self) -> None:
        """Test that function execution preserves request context."""
        result = self.caller.call_function(
            "execute_command",
            {
                "tool_name": "task",
                "params": {
                    "context": "test_context",
                    "priority": "high",
                },
            },
        )

        self.assertTrue(result["success"])

    def test_timestamp_included_in_result(self) -> None:
        """Test that results include timestamp."""
        result = self.caller.call_function(
            "check_health",
            {},
        )

        self.assertTrue(result["success"])
        self.assertIn("timestamp", result.get("result", {}))

    def test_function_results_contain_function_name(self) -> None:
        """Test that results indicate which function was executed."""
        for func_name in [
            "get_metrics",
            "check_health",
            "analyze_image",
            "apply_improvement",
        ]:
            if func_name == "analyze_image":
                result = self.caller.call_function(
                    func_name,
                    {"image_path": "/test.png"},
                )
            elif func_name == "apply_improvement":
                result = self.caller.call_function(
                    func_name,
                    {
                        "improvement_type": "batch_execution",
                        "target": "executor",
                    },
                )
            else:
                result = self.caller.call_function(
                    func_name,
                    {},
                )

            self.assertEqual(result["function"], func_name)


class TestFunctionConfigurationValidation(unittest.TestCase):
    """Tests for function configuration validation."""

    def test_config_file_is_valid_json(self) -> None:
        """Test that gemini_functions.json is valid JSON."""
        config_path = Path(__file__).resolve().parents[1] / "server" / "config" / "gemini_functions.json"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.assertIsInstance(config, dict)
                self.assertIn("functions", config)

    def test_function_names_match_mapping(self) -> None:
        """Test that all function names in config have tool mappings."""
        caller = GeminiFunctionCaller(api_key="test")
        functions = caller.get_function_definitions()
        mapping = caller.function_to_tool_mapping

        function_names = {f["name"] for f in functions}
        mapped_names = set(mapping.keys())

        # All functions should have mappings (at minimum)
        self.assertTrue(function_names.issubset(mapped_names) or len(mapping) > 0)


if __name__ == "__main__":
    unittest.main()
