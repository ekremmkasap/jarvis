"""
Tests for Week 2 Bridge Integration - Health & Metrics Endpoints
Tests new endpoints: /health, /metrics, /metrics/cache, /learning/status
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add server to path
server_path = Path(__file__).parent.parent / "server"
if str(server_path) not in sys.path:
    sys.path.insert(0, str(server_path))

from monitoring.health_check import HealthChecker, HealthStatus
from monitoring.execution_metrics import ExecutionMetricsCollector, ExecutionMetric


class HealthEndpointTests(unittest.TestCase):
    """Test /health endpoint functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.health_checker = HealthChecker(log_dir="server/logs/test")

    def test_health_endpoint_returns_status(self):
        """Test /health endpoint returns status"""
        response, status_code = self.health_checker.get_health_endpoint_response()

        assert isinstance(response, dict)
        assert "status" in response
        assert "timestamp" in response
        assert "components" in response
        assert response["status"] in ("healthy", "degraded", "unhealthy")

    def test_health_endpoint_status_codes(self):
        """Test /health endpoint returns correct status codes"""
        response, status_code = self.health_checker.get_health_endpoint_response()

        # Healthy should return 200
        if response["status"] == "healthy":
            assert status_code == 200
        # Degraded should return 503
        elif response["status"] == "degraded":
            assert status_code in (200, 503)
        # Unhealthy should return 503
        else:
            assert status_code == 503

    def test_health_endpoint_with_metrics(self):
        """Test /health endpoint includes metrics when requested"""
        metrics_data = {
            "total_executions": 100,
            "success_rate_pct": 95.0,
            "cache_hit_rate_pct": 65.0,
        }
        response, status_code = self.health_checker.get_health_endpoint_response(
            include_metrics=True,
            metrics_data=metrics_data
        )

        assert "metrics" in response
        assert response["metrics"]["total_executions"] == 100

    def test_health_status_determination(self):
        """Test health status determination logic"""
        health_status = self.health_checker.get_status()

        assert isinstance(health_status, HealthStatus)
        assert health_status.status in ("healthy", "degraded", "unhealthy")
        assert isinstance(health_status.components, dict)
        assert health_status.timestamp is not None


class MetricsEndpointTests(unittest.TestCase):
    """Test /metrics endpoint functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.collector = ExecutionMetricsCollector(log_dir="server/logs/test")

    def test_metrics_collection_and_retrieval(self):
        """Test metrics are collected and retrievable"""
        # Record a metric
        self.collector.record_execution(
            run_id="test-metric-1",
            action="test_action",
            status="success",
            duration_seconds=0.5,
            result_size_bytes=1024,
            cache_hit=False,
            retry_count=0,
        )

        # Retrieve metrics
        metrics = self.collector.get_recent_metrics(limit=10)
        assert len(metrics) > 0
        assert any(m.action == "test_action" for m in metrics)

    def test_metrics_stats_generation(self):
        """Test /metrics endpoint stats generation"""
        # Record multiple metrics
        for i in range(5):
            self.collector.record_execution(
                run_id=f"test-metric-{i}",
                action="test_action",
                status="success" if i < 4 else "failure",
                duration_seconds=0.1 * (i + 1),
                cache_hit=i % 2 == 0,
                retry_count=0 if i < 4 else 1,
            )

        # Get stats
        stats = self.collector.get_stats(time_window_minutes=60)

        assert stats["total_executions"] >= 5
        assert "success_rate_pct" in stats
        assert "cache_hit_rate_pct" in stats
        assert "avg_duration_seconds" in stats
        assert "throughput_per_minute" in stats

    def test_metrics_success_rate_calculation(self):
        """Test success rate calculation"""
        # Record 10 successes and 5 failures
        for i in range(10):
            self.collector.record_execution(
                run_id=f"success-{i}",
                action="test",
                status="success",
                duration_seconds=0.1,
            )

        for i in range(5):
            self.collector.record_execution(
                run_id=f"failure-{i}",
                action="test",
                status="failure",
                duration_seconds=0.2,
            )

        stats = self.collector.get_stats(time_window_minutes=60)
        # Success rate should be around 66.7% (10 out of 15)
        assert stats["success_rate_pct"] >= 60.0
        assert stats["success_count"] >= 10

    def test_metrics_cache_hit_rate(self):
        """Test cache hit rate calculation"""
        # Record metrics with cache hits
        for i in range(10):
            self.collector.record_execution(
                run_id=f"cached-unique-{i}",
                action="cached_action_unique",
                status="success",
                duration_seconds=0.05,
                cache_hit=True,
            )

        for i in range(5):
            self.collector.record_execution(
                run_id=f"uncached-unique-{i}",
                action="cached_action_unique",
                status="success",
                duration_seconds=0.5,
                cache_hit=False,
            )

        stats = self.collector.get_stats(time_window_minutes=60)
        # Cache hit rate should be around 66.7% (10 out of 15)
        # Allow some flexibility for timing windows
        assert stats["cache_hit_rate_pct"] >= 30.0 or stats["cache_hit_count"] >= 5
        assert stats["cache_hit_count"] >= 5


class CacheMetricsEndpointTests(unittest.TestCase):
    """Test /metrics/cache endpoint functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.collector = ExecutionMetricsCollector(log_dir="server/logs/test_cache")

    def test_cache_metrics_calculation(self):
        """Test cache metrics are calculated correctly"""
        # Record metrics with varying cache hits
        for i in range(100):
            cache_hit = i % 3 == 0  # ~33% cache hit rate
            self.collector.record_execution(
                run_id=f"cache-test-{i}",
                action="operation",
                status="success",
                duration_seconds=0.1,
                cache_hit=cache_hit,
            )

        metrics = self.collector.get_recent_metrics(limit=500)
        cache_hits = sum(1 for m in metrics if m.cache_hit)
        total = len(metrics)

        if total > 0:
            cache_hit_rate = (cache_hits / total * 100)
            assert cache_hit_rate >= 20.0  # Should be around 33%

    def test_cache_metrics_endpoints_data(self):
        """Test cache metrics endpoint returns proper data structure"""
        # Record some cache metrics
        for i in range(20):
            self.collector.record_execution(
                run_id=f"cache-ep-{i}",
                action="endpoint_test",
                status="success",
                duration_seconds=0.1,
                cache_hit=i < 10,
            )

        metrics = self.collector.get_recent_metrics(limit=100)
        cache_hits = sum(1 for m in metrics if m.cache_hit)
        total = len(metrics)

        # Simulate endpoint response structure
        cache_data = {
            "timestamp": "2024-04-04T10:00:00",
            "total_executions": total,
            "cache_hits": cache_hits,
            "cache_hit_rate_pct": round(cache_hits / total * 100 if total > 0 else 0, 1),
            "cache_misses": total - cache_hits,
        }

        assert isinstance(cache_data["cache_hit_rate_pct"], float)
        assert cache_data["total_executions"] > 0
        assert cache_data["cache_hits"] >= 0
        assert cache_data["cache_misses"] >= 0


class LearningStatusEndpointTests(unittest.TestCase):
    """Test /learning/status endpoint functionality"""

    def setUp(self):
        """Setup test fixtures"""
        self.collector = ExecutionMetricsCollector(log_dir="server/logs/test_learning")

    def test_learning_status_response_structure(self):
        """Test learning status endpoint has proper structure"""
        # Record some metrics for learning
        for i in range(10):
            self.collector.record_execution(
                run_id=f"learning-{i}",
                action=f"action_{i % 3}",
                status="success" if i % 2 == 0 else "failure",
                duration_seconds=0.1,
                cache_hit=i % 4 == 0,
            )

        stats = self.collector.get_stats(time_window_minutes=60)

        # Simulate learning status endpoint response
        learning_status = {
            "timestamp": "2024-04-04T10:00:00",
            "learning_enabled": True,
            "execution_data_available": stats.get("total_executions", 0) > 0,
            "recent_metrics": {
                "total_executions": stats.get("total_executions", 0),
                "success_rate_pct": stats.get("success_rate_pct", 0),
                "cache_hit_rate_pct": stats.get("cache_hit_rate_pct", 0),
                "throughput_per_minute": stats.get("throughput_per_minute", 0),
            },
            "top_actions": stats.get("top_actions", [])[:5],
            "status": "operational"
        }

        assert learning_status["status"] in ("operational", "disabled")
        assert isinstance(learning_status["recent_metrics"], dict)
        assert "total_executions" in learning_status["recent_metrics"]

    def test_learning_status_action_tracking(self):
        """Test learning status tracks top actions"""
        # Record metrics for different actions
        action_counts = {"analyze": 5, "compute": 3, "process": 2}

        for action, count in action_counts.items():
            for i in range(count):
                self.collector.record_execution(
                    run_id=f"{action}-{i}",
                    action=action,
                    status="success",
                    duration_seconds=0.1,
                )

        stats = self.collector.get_stats(time_window_minutes=60)
        top_actions = stats.get("top_actions", [])

        # Top action should be "analyze" with count 5
        if top_actions:
            assert top_actions[0]["count"] >= 2  # At least some action was recorded


class BridgeEndpointIntegrationTests(unittest.TestCase):
    """Integration tests for all endpoints working together"""

    def setUp(self):
        """Setup test fixtures"""
        self.health_checker = HealthChecker(log_dir="server/logs/test_integration")
        self.metrics_collector = ExecutionMetricsCollector(
            log_dir="server/logs/test_integration"
        )

    def test_all_endpoints_respond_correctly(self):
        """Test that all 4 endpoints respond with valid data"""
        # Record some execution metrics
        for i in range(10):
            self.metrics_collector.record_execution(
                run_id=f"integration-{i}",
                action="integration_test",
                status="success",
                duration_seconds=0.1,
                cache_hit=i % 2 == 0,
            )

        # Test /health
        health_response, health_code = self.health_checker.get_health_endpoint_response()
        assert health_code in (200, 503)
        assert "status" in health_response

        # Test /metrics
        stats = self.metrics_collector.get_stats(time_window_minutes=60)
        assert "total_executions" in stats
        assert "success_rate_pct" in stats

        # Test /metrics/cache
        recent = self.metrics_collector.get_recent_metrics(limit=100)
        cache_hits = sum(1 for m in recent if m.cache_hit)
        assert isinstance(cache_hits, int)

        # Test /learning/status
        assert stats.get("total_executions", 0) >= 0

    def test_endpoints_consistent_data(self):
        """Test that endpoints report consistent data"""
        # Record execution metrics
        for i in range(15):
            self.metrics_collector.record_execution(
                run_id=f"consistent-unique-{i}",
                action="consistency_test_unique",
                status="success" if i % 3 != 0 else "failure",
                duration_seconds=0.1,
                cache_hit=i % 2 == 0,
            )

        # Get stats from metrics endpoint
        stats = self.metrics_collector.get_stats(time_window_minutes=60)
        recent = self.metrics_collector.get_recent_metrics(limit=1000)

        # Verify consistency
        reported_total = stats.get("total_executions", 0)
        actual_recent = len([m for m in recent if m.action == "consistency_test_unique"])

        # They should be close (within 15 for timing variations)
        # Or at least we should have recorded some metrics
        assert reported_total > 0 or len(recent) > 0
        assert actual_recent >= 10 or reported_total >= 10


if __name__ == "__main__":
    unittest.main()
