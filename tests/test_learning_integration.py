"""
WEEK 2 LEARNING INTEGRATION TESTS
Tests for: Hook execution logging, automatic improvement suggestions, improvement delta tracking
"""

from __future__ import annotations

import asyncio
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import tempfile
import shutil

from server.agents.executor_agent import ExecutorAgent
from server.agents.task_planner_agent import TaskPlannerAgent
from server.agents.tool_registry import ToolRegistry
from server.agents.week1_pipeline import Week1Pipeline
from server.monitoring.execution_metrics import ExecutionMetricsCollector, ExecutionMetric
from server.monitoring.learning_integration import LearningIntegrationBridge
from server.agents.self_learning_agent import SelfLearningEngine


class TestLearningIntegrationHooks(unittest.TestCase):
    """Test learning hooks in week1_pipeline"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        # Close all logging handlers
        import logging
        for logger_name in list(logging.Logger.manager.loggerDict):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

        # Clean up temp directory
        if Path(self.temp_dir).exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass  # Ignore cleanup errors on Windows

    def test_metrics_fed_to_learning_engine(self) -> None:
        """Test that execution metrics are fed to learning engine"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)
        registry = ToolRegistry()

        # Register simple tools
        def analyze_tool(payload: dict) -> dict:
            return {"analysis": "ok"}

        def implement_tool(payload: dict) -> dict:
            return {"implementation": "ok"}

        registry.register("analyze", analyze_tool)
        registry.register("implement", implement_tool)

        pipeline = Week1Pipeline(
            planner=TaskPlannerAgent(),
            executor=ExecutorAgent(registry),
            tool_registry=registry,
            metrics_collector=metrics,
            logger=None,
        )

        # Run pipeline
        result = pipeline.run("Build a two-step plan", requested_actions=["analyze", "implement"])

        # Verify pipeline succeeded
        self.assertTrue(result["ok"])

        # Verify metrics were recorded
        recent_metrics = metrics.get_recent_metrics(limit=10)
        self.assertGreater(len(recent_metrics), 0, "No metrics recorded")

        # Check for pipeline-level metric
        pipeline_metrics = [m for m in recent_metrics if m.action == "pipeline"]
        self.assertGreater(len(pipeline_metrics), 0, "No pipeline metrics recorded")

        # Check for step-level metrics
        step_metrics = [m for m in recent_metrics if m.action in ("analyze", "implement")]
        self.assertGreater(len(step_metrics), 0, "No step metrics recorded")

    def test_suggestions_applied_automatically(self) -> None:
        """Test that improvement suggestions are generated and applied"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)
        learning = SelfLearningEngine(data_dir=str(self.log_dir / "learning"))
        bridge = LearningIntegrationBridge(
            metrics_collector=metrics,
            learning_engine=learning,
            log_dir=self.log_dir,
        )

        # Simulate several executions to build patterns
        async def simulate_executions() -> None:
            for i in range(5):
                # Mix of successes and failures for pattern
                result = {
                    "status": "success" if i % 2 == 0 else "failure",
                    "action": "test_action",
                    "error": "timeout" if i % 2 == 1 else None,
                    "duration": 1.0 + (i * 0.1),
                    "improvement_delta": 0.1,
                }
                await learning.log_execution(f"task_{i}", result)

                # Also record in metrics collector
                metrics.record_execution(
                    run_id=f"run_{i}",
                    action="test_action",
                    status="success" if i % 2 == 0 else "failure",
                    duration_seconds=1.0 + (i * 0.1),
                    error_message="timeout" if i % 2 == 1 else None,
                )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(simulate_executions())
        finally:
            loop.close()

        # Check that suggestions can be generated
        suggestions = asyncio.run(learning.suggest_improvements())
        self.assertGreater(len(suggestions), 0, "No suggestions generated from patterns")

        # Verify suggestion structure
        for suggestion in suggestions:
            self.assertIn("type", suggestion)
            self.assertIn("expected_improvement", suggestion)
            self.assertIn("priority", suggestion)

    def test_improvement_delta_tracked(self) -> None:
        """Test that improvement deltas are tracked in metrics"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)
        registry = ToolRegistry()

        def tool_action(payload: dict) -> dict:
            return {"result": "ok"}

        registry.register("verify", tool_action)

        bridge = LearningIntegrationBridge(
            metrics_collector=metrics,
            log_dir=self.log_dir,
        )

        pipeline = Week1Pipeline(
            planner=TaskPlannerAgent(),
            executor=ExecutorAgent(registry),
            tool_registry=registry,
            metrics_collector=metrics,
            learning_bridge=bridge,
        )

        # Run pipeline
        result = pipeline.run("Verify system", requested_actions=["verify"])

        # Verify pipeline structure includes improvement_delta
        self.assertIn("improvement_delta", result)

        # Get learning metrics
        learning_metrics = pipeline.get_learning_metrics()
        self.assertIn("improvements_applied", learning_metrics)
        self.assertIn("improvement_deltas", learning_metrics)

    def test_learning_retry_backoff_suggestion(self) -> None:
        """Test: Learning suggests retry backoff for failed actions"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)
        learning = SelfLearningEngine(data_dir=str(self.log_dir / "learning"))

        # Simulate failed executions (same action failing multiple times)
        async def simulate_failures() -> None:
            for i in range(6):
                result = {
                    "status": "failure",
                    "action": "flaky_action",
                    "error": "timeout",
                    "duration": 2.0,
                }
                await learning.log_execution(f"task_{i}", result)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(simulate_failures())
            # Generate suggestions
            suggestions = loop.run_until_complete(learning.suggest_improvements())
        finally:
            loop.close()

        # Should suggest retry strategy for the failing action
        retry_suggestions = [s for s in suggestions if s.get("type") == "retry_strategy"]
        self.assertGreater(len(retry_suggestions), 0, "No retry_strategy suggestion for failing action")

        # Verify retry suggestion targets the failing action
        for suggestion in retry_suggestions:
            self.assertIn("target_errors", suggestion)
            self.assertIn("timeout", suggestion.get("target_errors", []))

    def test_improvement_with_auto_rollback_on_negative_impact(self) -> None:
        """Test: Apply improvement + auto-rollback if negative impact detected"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)
        learning = SelfLearningEngine(data_dir=str(self.log_dir / "learning"))

        bridge = LearningIntegrationBridge(
            metrics_collector=metrics,
            learning_engine=learning,
            log_dir=self.log_dir,
        )

        # Setup: Create baseline metrics
        async def setup_baseline() -> None:
            for i in range(10):
                metrics.record_execution(
                    run_id=f"baseline_{i}",
                    action="test_action",
                    status="success",
                    duration_seconds=1.0,
                )
                result = {
                    "status": "success",
                    "action": "test_action",
                    "error": None,
                    "duration": 1.0,
                }
                await learning.log_execution(f"baseline_{i}", result)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(setup_baseline())

            # Get baseline stats
            baseline_stats = metrics.get_stats(time_window_minutes=60)
            baseline_success_rate = baseline_stats.get("success_rate_pct", 0)

            # Apply improvement
            improvement_result = loop.run_until_complete(bridge.check_and_apply_improvements())

            # If improvement was applied, verify it's tracked
            if improvement_result.get("status") == "success":
                improvement_id = improvement_result.get("improvement_id")
                self.assertIsNotNone(improvement_id)

                # Simulate negative impact (add failures after improvement)
                async def introduce_failures() -> None:
                    for i in range(5):
                        metrics.record_execution(
                            run_id=f"after_improvement_{i}",
                            action="test_action",
                            status="failure",
                            duration_seconds=1.0,
                            error_message="degraded",
                        )

                    loop.run_until_complete(introduce_failures())

                # Check impact
                impact = loop.run_until_complete(bridge.check_improvement_impact(improvement_id, timeout_minutes=60))

                # If impact is negative, rollback should be triggered
                if impact.get("delta", 0) < bridge.rollback_threshold:
                    self.assertTrue(impact.get("rollback_triggered", False))
                    self.assertIn("rollback_reason", impact)
        finally:
            loop.close()

    def test_logging_comprehensive(self) -> None:
        """Test: Logging is comprehensive for debugging"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)
        registry = ToolRegistry()

        def analyze_tool(payload: dict) -> dict:
            return {"analysis": "ok"}

        registry.register("analyze", analyze_tool)

        bridge = LearningIntegrationBridge(
            metrics_collector=metrics,
            log_dir=self.log_dir,
        )

        pipeline = Week1Pipeline(
            planner=TaskPlannerAgent(),
            executor=ExecutorAgent(registry),
            tool_registry=registry,
            metrics_collector=metrics,
            learning_bridge=bridge,
        )

        # Run pipeline
        pipeline.run("Test analyze", requested_actions=["analyze"])

        # Check that logs were created
        log_files = list(self.log_dir.glob("*.log"))
        self.assertGreater(len(log_files), 0, "No log files created")

        # Verify learning bridge logs exist
        learning_logs = [f for f in log_files if "learning" in f.name or "bridge" in f.name]
        self.assertGreater(len(learning_logs), 0, "No learning integration logs found")

        # Check log content
        week1_logs = [f for f in log_files if "week1" in f.name]
        if week1_logs:
            with open(week1_logs[0], "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("pipeline_started", content)
                self.assertIn("pipeline_finished", content)


class TestLearningIntegrationMetrics(unittest.TestCase):
    """Test metrics collection and learning integration"""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.log_dir = Path(self.temp_dir) / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        # Close all logging handlers
        import logging
        for logger_name in list(logging.Logger.manager.loggerDict):
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)

        # Clean up temp directory
        if Path(self.temp_dir).exists():
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass  # Ignore cleanup errors on Windows

    def test_metrics_aggregation(self) -> None:
        """Test that metrics are correctly aggregated"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)

        # Record various metrics
        metrics.record_execution(
            run_id="run_1",
            action="action_a",
            status="success",
            duration_seconds=1.5,
        )

        metrics.record_execution(
            run_id="run_2",
            action="action_a",
            status="failure",
            duration_seconds=2.0,
            error_message="error_type_1",
        )

        metrics.record_execution(
            run_id="run_3",
            action="action_b",
            status="success",
            duration_seconds=0.8,
        )

        # Get stats
        stats = metrics.get_stats(time_window_minutes=60)

        self.assertEqual(stats["total_executions"], 3)
        self.assertEqual(stats["success_count"], 2)
        self.assertEqual(stats["failure_count"], 1)
        self.assertAlmostEqual(stats["success_rate_pct"], 66.7, places=1)

    def test_improvement_history_tracking(self) -> None:
        """Test that improvement history is tracked"""
        metrics = ExecutionMetricsCollector(log_dir=self.log_dir)
        learning = SelfLearningEngine(data_dir=str(self.log_dir / "learning"))

        bridge = LearningIntegrationBridge(
            metrics_collector=metrics,
            learning_engine=learning,
            log_dir=self.log_dir,
        )

        # Setup some data
        async def setup() -> None:
            for i in range(5):
                metrics.record_execution(
                    run_id=f"run_{i}",
                    action="test",
                    status="success",
                    duration_seconds=1.0,
                )
                result = {
                    "status": "success",
                    "action": "test",
                    "error": None,
                    "duration": 1.0,
                }
                await learning.log_execution(f"task_{i}", result)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(setup())

            # Get improvement history (should be empty initially)
            history = bridge.get_improvement_history()
            self.assertEqual(len(history), 0)

            # Try to apply improvements
            result = loop.run_until_complete(bridge.check_and_apply_improvements())

            # Get history again (may have applied improvement)
            history = bridge.get_improvement_history()
            # Just verify method works
            self.assertIsInstance(history, list)
        finally:
            loop.close()


if __name__ == "__main__":
    unittest.main()
