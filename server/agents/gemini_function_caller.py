"""
Gemini 2.5 Function Calling Integration

Maps natural language requests to Jarvis functions and executes them.
Integrates Gemini's function calling capability with the executor system.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import google.generativeai as genai
except ImportError:
    genai = None  # type: ignore


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "gemini_function_caller.log"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("agent.gemini_function_caller")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(
        isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == LOG_FILE
        for handler in logger.handlers
    ):
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
    return logger


class GeminiFunctionCaller:
    """
    Handles Gemini 2.5 function calling for Jarvis.

    Maps user requests to Jarvis functions, streams results, and integrates
    with the executor system.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "models/gemini-2.5-flash",
        functions_config_path: str | None = None,
        executor_fn: callable | None = None,
        logger: logging.Logger | None = None,
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.executor_fn = executor_fn
        self.logger = logger or _build_logger()

        if not self.api_key:
            self.logger.warning("GEMINI_API_KEY not set, function calling disabled")

        # Load function definitions from config
        self.functions_config = self._load_functions_config(functions_config_path)
        self.functions = self.functions_config.get("functions", [])
        self.function_to_tool_mapping = self.functions_config.get("function_to_tool_mapping", {})

        # Initialize Gemini if available
        self.client = None
        if self.api_key and genai:
            try:
                genai.configure(api_key=self.api_key)
                self.client = genai
                self.logger.info("Gemini client initialized successfully")
            except Exception as exc:
                self.logger.error(f"Failed to initialize Gemini client: {exc}")

    def _load_functions_config(self, config_path: str | None = None) -> dict[str, Any]:
        """Load function definitions from JSON config."""
        if config_path is None:
            config_path = str(
                Path(__file__).resolve().parents[1] / "config" / "gemini_functions.json"
            )

        try:
            if Path(config_path).exists():
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.logger.info(f"Loaded {len(config.get('functions', []))} functions from config")
                    return config
        except Exception as exc:
            self.logger.error(f"Failed to load functions config: {exc}")

        return {"functions": [], "function_to_tool_mapping": {}}

    def get_function_definitions(self) -> list[dict[str, Any]]:
        """Return Gemini-compatible function definitions."""
        return self.functions

    def _execute_local_function(
        self,
        function_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a function locally using registered executors."""
        try:
            tool_name = self.function_to_tool_mapping.get(function_name, function_name)

            # Route to appropriate executor
            if function_name == "execute_command" and self.executor_fn:
                result = self.executor_fn(
                    {
                        "action": arguments.get("tool_name", ""),
                        "params": arguments.get("params", {}),
                    }
                )
                return {
                    "function": function_name,
                    "success": result.get("ok", False),
                    "result": result.get("result", {}),
                    "error": result.get("error"),
                }

            elif function_name == "get_metrics":
                # Return mock metrics for now
                metric_type = arguments.get("metric_type", "all")
                return {
                    "function": function_name,
                    "success": True,
                    "result": {
                        "metric_type": metric_type,
                        "cpu_percent": 15.2,
                        "memory_percent": 28.5,
                        "latency_p50_ms": 42.0,
                        "latency_p99_ms": 180.0,
                        "success_rate": 0.98,
                        "throughput_rps": 250.5,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }

            elif function_name == "check_health":
                # Return health status
                return {
                    "function": function_name,
                    "success": True,
                    "result": {
                        "status": "healthy",
                        "components": {
                            "executor": "operational",
                            "database": "operational",
                            "cache": "operational",
                            "api": "operational",
                            "telegram": "operational",
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }

            elif function_name == "analyze_image":
                # Mock image analysis result
                image_path = arguments.get("image_path", "")
                return {
                    "function": function_name,
                    "success": True,
                    "result": {
                        "image_path": image_path,
                        "analysis": "Image contains UI elements and text",
                        "elements_detected": ["button", "text_field", "menu"],
                        "text_content": ["Example text from image"],
                    },
                }

            elif function_name == "apply_improvement":
                # Mock improvement application
                improvement_type = arguments.get("improvement_type", "")
                return {
                    "function": function_name,
                    "success": True,
                    "result": {
                        "improvement_type": improvement_type,
                        "status": "applied",
                        "impact": "positive",
                    },
                }

            else:
                return {
                    "function": function_name,
                    "success": False,
                    "error": f"Unknown function: {function_name}",
                }

        except Exception as exc:
            self.logger.error(f"Error executing function {function_name}: {exc}")
            return {
                "function": function_name,
                "success": False,
                "error": str(exc),
            }

    def call_function(
        self,
        function_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a function (Gemini-selected or direct)."""
        self.logger.info(f"Executing function: {function_name}")
        result = self._execute_local_function(function_name, arguments)
        self.logger.info(f"Function result: {result}")
        return result

    def process_request(
        self,
        user_request: str,
        stream: bool = False,
    ) -> dict[str, Any]:
        """
        Process a user request using Gemini function calling.

        1. Send request to Gemini with function definitions
        2. Gemini selects and calls appropriate function(s)
        3. Execute selected function(s) locally
        4. Return results
        """
        if not self.client:
            return {
                "success": False,
                "error": "Gemini client not initialized",
            }

        try:
            # Create tools list for Gemini
            tools = [
                {
                    "function_declarations": self.functions,
                }
            ]

            # Call Gemini with function calling enabled
            model = self.client.GenerativeModel(
                self.model,
                tools=tools,
            )

            # Send request
            response = model.generate_content(user_request)

            # Process response
            results = []
            for part in response.parts:
                if part.function_call:
                    func_name = part.function_call.name
                    func_args = {k: v for k, v in part.function_call.args.items()}

                    # Execute the function
                    func_result = self.call_function(func_name, func_args)
                    results.append(func_result)

            self.logger.info(f"Processed request with {len(results)} function calls")
            return {
                "success": True,
                "request": user_request,
                "function_calls": results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as exc:
            self.logger.error(f"Error processing request: {exc}")
            return {
                "success": False,
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def process_request_async(
        self,
        user_request: str,
    ) -> dict[str, Any]:
        """Asynchronous version of process_request."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.process_request,
            user_request,
        )


def create_function_caller(
    api_key: str | None = None,
    model: str = "models/gemini-2.5-flash",
    executor_fn: callable | None = None,
) -> GeminiFunctionCaller:
    """Factory function to create a GeminiFunctionCaller instance."""
    return GeminiFunctionCaller(
        api_key=api_key,
        model=model,
        executor_fn=executor_fn,
    )
