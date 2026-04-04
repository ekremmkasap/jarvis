"""
Tests for monitoring modules
"""

from __future__ import annotations

import unittest
from pathlib import Path
from server.monitoring.execution_metrics import ExecutionMetricsCollector, ExecutionMetric
from server.monitoring.health_check import HealthChecker


class ExecutionMetricsTests(unittest.TestCase):
    def test_record_and_retrieve_metrics(self) -> None:
        """Test recording and retrieving metrics"""
        collector = ExecutionMetricsCollector(log_dir="server/logs/test")

        # Record a metric
        collector.record_execution(
            run_id="test-run-1",
            action="test_action",
            status="success",
            duration_seconds=0.5,
            cache_hit=False,
            retry_count=0,
        )

        # Retrieve metrics
        metrics = collector.get_recent_metrics(limit=10)
        assert len(metrics) > 0
        assert metrics[-1].action == "test_action"
        assert metrics[-1].status == "success"

    def test_get_stats(self) -> None:
        """Test stat aggregation"""
        collector = ExecutionMetricsCollector(log_dir="server/logs/test")

        # Record several metrics
        for i in range(3):
            collector.record_execution(
                run_id=f"run-{i}",
                action="test",
                status="success",
                duration_seconds=0.1 * (i + 1),
            )

        stats = collector.get_stats(time_window_minutes=60)
        assert stats["total_executions"] >= 3
        assert stats["success_rate_pct"] > 0


class HealthCheckerTests(unittest.TestCase):
    def test_health_check(self) -> None:
        """Test health check"""
        checker = HealthChecker(log_dir="server/logs/test")

        # Get components status
        components = checker.check_components()
        assert isinstance(components, dict)
        assert "logs_writable" in components

    def test_get_status(self) -> None:
        """Test overall status determination"""
        checker = HealthChecker(log_dir="server/logs/test")
        status = checker.get_status()

        assert status.status in ("healthy", "degraded", "unhealthy")
        assert isinstance(status.components, dict)

    def test_health_endpoint_response(self) -> None:
        """Test health endpoint response"""
        checker = HealthChecker(log_dir="server/logs/test")
        response, status_code = checker.get_health_endpoint_response()

        assert isinstance(response, dict)
        assert status_code in (200, 503)
        assert "status" in response
        assert "timestamp" in response


if __name__ == "__main__":
    unittest.main()
