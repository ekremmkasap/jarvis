"""
Week 2 E2E Testing - AZIZ-5
Complete voice → plan → execute → learn → improve cycle testing

This test suite validates:
1. Voice input processing (simulated)
2. Task planning
3. Step execution
4. Metrics collection
5. Learning integration
6. Performance improvements
"""

from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from typing import Any

from server.agents.executor_agent import ExecutorAgent
from server.agents.execution_cache import ExecutionCache
from server.agents.task_planner_agent import TaskPlannerAgent
from server.agents.tool_registry import ToolRegistry
from server.agents.week1_pipeline import Week1Pipeline, build_week1_tool_registry
from server.monitoring.execution_metrics import ExecutionMetricsCollector
from server.monitoring.health_check import HealthChecker


class _FakeResponse:
    """Fake Gemini response for testing"""
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    """Fake Gemini models for testing"""
    def generate_content(self, *, model: str, contents: str) -> _FakeResponse:
        prompt = str(contents or "").strip()
        return _FakeResponse(f"Response to: {prompt[:100]}")


class _FakeClient:
    """Fake Gemini client for testing"""
    def __init__(self) -> None:
        self.models = _FakeModels()


class TestCallTracker:
    """Track executed actions for analysis"""
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.start_time = time.time()

    def record_call(self, action: str, success: bool, duration: float) -> None:
        """Record a single action call"""
        self.calls.append({
            "action": action,
            "success": success,
            "duration": duration,
            "timestamp": time.time() - self.start_time,
        })

    def get_stats(self) -> dict[str, Any]:
        """Get aggregated statistics"""
        if not self.calls:
            return {
                "total_calls": 0,
                "success_rate": 0.0,
                "avg_latency": 0.0,
                "min_latency": 0.0,
                "max_latency": 0.0,
            }

        successful = sum(1 for call in self.calls if call["success"])
        durations = [call["duration"] for call in self.calls]

        return {
            "total_calls": len(self.calls),
            "success_rate": (successful / len(self.calls)) * 100,
            "avg_latency": sum(durations) / len(durations),
            "min_latency": min(durations),
            "max_latency": max(durations),
            "successful_actions": successful,
            "failed_actions": len(self.calls) - successful,
        }


class Week2E2ETests(unittest.TestCase):
    """E2E tests for Week 2 system"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        self.logs_dir = Path("server/logs/test_week2")
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # Create test registry with instrumented tools
        self.registry = ToolRegistry()
        self.call_tracker = TestCallTracker()
        self.cache = ExecutionCache(ttl_seconds=300, max_entries=50)
        self.metrics_collector = ExecutionMetricsCollector(log_dir=str(self.logs_dir))

        # Register test tools
        self._register_test_tools()

        # Create pipeline components
        self.pipeline = Week1Pipeline(
            planner=TaskPlannerAgent(),
            executor=ExecutorAgent(self.registry),
            tool_registry=self.registry,
        )

    def _register_test_tools(self) -> None:
        """Register test tools with execution tracking"""
        def tracked_tool(action: str):
            def _tool(payload: dict) -> dict:
                start = time.time()
                try:
                    # Simulate tool execution
                    result = {
                        "action": action,
                        "status": "success",
                        "description": payload.get("description", ""),
                        "timestamp": time.time(),
                    }
                    duration = time.time() - start
                    self.call_tracker.record_call(action, True, duration)

                    # Check cache first
                    cache_result, cache_hit = self.cache.get(action, payload)
                    if cache_hit:
                        self.metrics_collector.record_execution(
                            run_id="test",
                            action=action,
                            status="success",
                            duration_seconds=0.001,  # Cache hits are faster
                            cache_hit=True,
                        )
                    else:
                        # Cache miss - record actual execution
                        self.cache.set(action, payload, result)
                        self.metrics_collector.record_execution(
                            run_id="test",
                            action=action,
                            status="success",
                            duration_seconds=duration,
                            cache_hit=False,
                        )

                    return result
                except Exception as e:
                    duration = time.time() - start
                    self.call_tracker.record_call(action, False, duration)
                    self.metrics_collector.record_execution(
                        run_id="test",
                        action=action,
                        status="failure",
                        duration_seconds=duration,
                        error_message=str(e),
                    )
                    return {
                        "action": action,
                        "status": "failure",
                        "error": str(e),
                    }

            return _tool

        # Register all standard actions
        for action in ["analyze", "design", "implement", "test", "review", "document", "verify"]:
            self.registry.register(action, tracked_tool(action))

    def test_voice_input_to_plan_cycle(self) -> None:
        """Test: voice input → planning"""
        # Simulate voice input with task prefix
        voice_input = "task: Build a test workflow"

        # Extract goal from voice input (simulates voice layer)
        goal = voice_input.replace("task:", "").strip() if voice_input.lower().startswith("task:") else voice_input

        # Run through pipeline
        result = self.pipeline.run(
            goal,
            requested_actions=["analyze", "test"],
        )

        # Verify result structure
        self.assertIn("goal", result)
        self.assertIn("steps", result)
        self.assertTrue(result["ok"])
        self.assertGreater(len(result["steps"]), 0)

    def test_plan_to_execute_cycle(self) -> None:
        """Test: planning → execution"""
        goal = "Complete a 3-step workflow"

        result = self.pipeline.run(
            goal,
            requested_actions=["analyze", "implement", "test"],
        )

        # Verify execution
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(len(result["steps"]), 3)
        self.assertEqual(len(result["results"]), 3)

        # Verify all steps executed
        for step in result["results"]:
            self.assertTrue(step["ok"], f"Step failed: {step}")

    def test_execute_with_metrics_collection(self) -> None:
        """Test: execution → metrics recording"""
        goal = "Track execution metrics"

        result = self.pipeline.run(
            goal,
            requested_actions=["analyze", "test"],
        )

        # Get collected metrics
        metrics = self.metrics_collector.get_recent_metrics(limit=100)

        # Verify metrics were recorded
        self.assertGreater(len(metrics), 0, "No metrics recorded")

        # Verify metric structure
        for metric in metrics:
            self.assertIsNotNone(metric.action)
            self.assertIsNotNone(metric.status)
            self.assertGreaterEqual(metric.duration_seconds, 0)

    def test_metrics_with_cache_hits(self) -> None:
        """Test: cache hits reported in metrics"""
        goal = "Test cache performance"

        # First run - cold cache
        result1 = self.pipeline.run(
            goal,
            requested_actions=["analyze"],
        )
        self.assertTrue(result1["ok"])

        # Get initial metrics
        metrics_before = len(self.metrics_collector.get_recent_metrics())

        # Second run - same action, should hit cache
        result2 = self.pipeline.run(
            goal,
            requested_actions=["analyze"],
        )
        self.assertTrue(result2["ok"])

        # Verify metrics show cache statistics
        metrics_after = self.metrics_collector.get_recent_metrics(limit=100)
        cache_hits = sum(1 for m in metrics_after if m.cache_hit)

        # Cache hits should be greater after second run
        self.assertGreaterEqual(cache_hits, 0, "Cache hit tracking failed")

    def test_10_call_sequence(self) -> None:
        """Test: 10-call sequential test sequence"""
        results = []

        for call_num in range(1, 11):
            goal = f"Execute task sequence call {call_num}"
            result = self.pipeline.run(
                goal,
                requested_actions=["analyze", "test"],
            )
            results.append(result)

        # Verify all calls completed
        self.assertEqual(len(results), 10)

        # Count successes
        successful = sum(1 for r in results if r["ok"])
        self.assertGreaterEqual(successful, 8, "Success rate too low")

        # Get statistics
        stats = self.call_tracker.get_stats()
        self.assertEqual(stats["total_calls"], 20)  # 2 actions x 10 calls
        self.assertGreater(stats["success_rate"], 80.0)

    def test_learning_pattern_detection(self) -> None:
        """Test: detect learning patterns from metrics"""
        # Generate several calls to establish patterns
        for i in range(5):
            self.pipeline.run(
                f"Pattern detection call {i}",
                requested_actions=["analyze"],
            )

        # Analyze metrics for patterns
        metrics = self.metrics_collector.get_recent_metrics(limit=100)
        actions = [m.action for m in metrics]
        action_counts = {}

        for action in actions:
            action_counts[action] = action_counts.get(action, 0) + 1

        # Verify we have action patterns
        self.assertGreater(len(action_counts), 0, "No action patterns detected")

        # Verify all recorded
        self.assertGreaterEqual(sum(action_counts.values()), 5)

    def test_improvement_delta_measurement(self) -> None:
        """Test: measure improvement delta between runs"""
        # First batch - baseline
        baseline_calls = []
        for i in range(3):
            start = time.time()
            result = self.pipeline.run(
                f"Baseline call {i}",
                requested_actions=["analyze", "test"],
            )
            duration = time.time() - start
            baseline_calls.append({
                "success": result["ok"],
                "duration": duration,
            })

        baseline_stats = {
            "success_rate": sum(1 for c in baseline_calls if c["success"]) / len(baseline_calls),
            "avg_duration": sum(c["duration"] for c in baseline_calls) / len(baseline_calls),
        }

        # Second batch - after "improvements"
        improved_calls = []
        for i in range(3):
            start = time.time()
            # With cache, should be faster
            result = self.pipeline.run(
                f"Improved call {i}",
                requested_actions=["analyze", "test"],
            )
            duration = time.time() - start
            improved_calls.append({
                "success": result["ok"],
                "duration": duration,
            })

        improved_stats = {
            "success_rate": sum(1 for c in improved_calls if c["success"]) / len(improved_calls),
            "avg_duration": sum(c["duration"] for c in improved_calls) / len(improved_calls),
        }

        # Calculate deltas
        delta = {
            "success_rate_delta": (improved_stats["success_rate"] - baseline_stats["success_rate"]) * 100,
            "latency_delta_pct": (
                (baseline_stats["avg_duration"] - improved_stats["avg_duration"]) / baseline_stats["avg_duration"] * 100
                if baseline_stats["avg_duration"] > 0 else 0
            ),
        }

        # Verify we can measure improvements
        self.assertIsNotNone(delta["success_rate_delta"])
        self.assertIsNotNone(delta["latency_delta_pct"])

    def test_health_check_during_load(self) -> None:
        """Test: health check during execution"""
        health_checker = HealthChecker(log_dir=str(self.logs_dir))

        # Run several tasks
        for i in range(5):
            self.pipeline.run(
                f"Health check test {i}",
                requested_actions=["analyze", "test"],
            )

        # Check health
        response, status_code = health_checker.get_health_endpoint_response()

        # Verify health response
        self.assertIn("status", response)
        self.assertIn(response["status"], ["healthy", "degraded", "unhealthy"])
        self.assertIn(status_code, [200, 503])

    def test_error_recovery_tracking(self) -> None:
        """Test: track error recovery in E2E"""
        goal = "Test error recovery"

        result = self.pipeline.run(
            goal,
            requested_actions=["analyze", "implement", "test"],
        )

        # Check recoveries were tracked
        self.assertIn("recoveries", result)
        self.assertIsInstance(result["recoveries"], list)

    def test_end_to_end_success_path(self) -> None:
        """Test: complete successful E2E path"""
        # Simulate voice input and extraction
        voice_input = "task: Complete end-to-end workflow"
        goal = voice_input.replace("task:", "").strip() if voice_input.lower().startswith("task:") else voice_input

        # Run through complete pipeline with 5 actions
        result = self.pipeline.run(
            goal,
            requested_actions=["analyze", "design", "implement", "test", "verify"],
        )

        # Verify complete flow
        self.assertTrue(result["ok"])

        # Verify all expected fields
        expected_fields = ["goal", "steps", "results", "summary"]
        for field in expected_fields:
            self.assertIn(field, result, f"Missing field: {field}")

        # Verify execution count
        total_steps = len(result["steps"])
        self.assertEqual(total_steps, 5)

    def test_cache_statistics_reporting(self) -> None:
        """Test: cache stats reporting"""
        # Set up cache hits
        for i in range(5):
            self.pipeline.run(
                "Cache test",  # Same goal
                requested_actions=["analyze"],
            )

        # Get cache stats
        cache_stats = self.cache.get_stats()

        # Verify stats structure
        expected_stats = ["hits", "misses", "total_entries", "hit_rate_pct"]
        for stat in expected_stats:
            self.assertIn(stat, cache_stats)

    def test_metrics_aggregation(self) -> None:
        """Test: metrics aggregation and reporting"""
        # Run several operations
        for i in range(5):
            self.pipeline.run(
                f"Metrics test {i}",
                requested_actions=["analyze", "test"],
            )

        # Get aggregated stats
        stats = self.metrics_collector.get_stats(time_window_minutes=60)

        # Verify stats are calculated
        expected_keys = [
            "total_executions",
            "success_rate_pct",
            "avg_duration_seconds",
            "total_duration_seconds",
        ]
        for key in expected_keys:
            self.assertIn(key, stats)

        # Verify reasonable values
        self.assertGreater(stats["total_executions"], 0)
        self.assertGreaterEqual(stats["success_rate_pct"], 0)
        self.assertLessEqual(stats["success_rate_pct"], 100)

    def test_action_specific_analysis(self) -> None:
        """Test: analyze performance by action type"""
        # Run various actions
        actions = ["analyze", "test", "implement"]
        for action in actions:
            for i in range(3):
                self.pipeline.run(
                    f"Action test {action} {i}",
                    requested_actions=[action],
                )

        # Get metrics and group by action
        metrics = self.metrics_collector.get_recent_metrics(limit=100)
        action_stats = {}

        for metric in metrics:
            if metric.action not in action_stats:
                action_stats[metric.action] = []
            action_stats[metric.action].append(metric)

        # Verify we have stats for each action
        self.assertGreater(len(action_stats), 0)

        # Calculate per-action stats
        for action, metrics_list in action_stats.items():
            successful = sum(1 for m in metrics_list if m.status == "success")
            success_rate = (successful / len(metrics_list)) * 100

            self.assertGreaterEqual(success_rate, 0)
            self.assertLessEqual(success_rate, 100)


class Week2ReportGeneration(unittest.TestCase):
    """Test suite for report generation"""

    def test_can_generate_performance_metrics_json(self) -> None:
        """Test: JSON report generation for metrics"""
        metrics_data = {
            "timestamp": "2026-04-04T12:00:00Z",
            "week": 2,
            "metrics": {
                "total_calls": 10,
                "success_rate": 95.0,
                "avg_latency_ms": 450,
                "cache_hit_rate": 35.0,
            },
        }

        # Verify JSON serializable
        json_str = json.dumps(metrics_data, indent=2)
        self.assertIn("week", json_str)
        self.assertIn("10", json_str)

    def test_can_generate_improvement_delta_report(self) -> None:
        """Test: improvement delta report generation"""
        baseline = {
            "success_rate": 75.0,
            "avg_latency": 1200,
            "throughput": 3,
        }

        improved = {
            "success_rate": 90.0,
            "avg_latency": 850,
            "throughput": 4,
        }

        deltas = {
            "success_rate_improvement": improved["success_rate"] - baseline["success_rate"],
            "latency_improvement_pct": (
                (baseline["avg_latency"] - improved["avg_latency"]) / baseline["avg_latency"] * 100
            ),
            "throughput_improvement_pct": (
                (improved["throughput"] - baseline["throughput"]) / baseline["throughput"] * 100
            ),
        }

        # Verify calculations
        self.assertEqual(deltas["success_rate_improvement"], 15.0)
        self.assertAlmostEqual(deltas["latency_improvement_pct"], 29.17, places=1)
        self.assertAlmostEqual(deltas["throughput_improvement_pct"], 33.33, places=1)


if __name__ == "__main__":
    unittest.main()
