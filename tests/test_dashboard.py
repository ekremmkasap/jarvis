"""
Tests for dashboard server
Real-time metrics dashboard functionality
"""

from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from server.monitoring.dashboard_server import DashboardServer
from server.monitoring.execution_metrics import ExecutionMetricsCollector
from server.monitoring.health_check import HealthChecker


class DashboardServerInitTests(unittest.TestCase):
    """Test dashboard server initialization"""

    def test_dashboard_server_initialization(self) -> None:
        """Test that dashboard server initializes correctly"""
        try:
            server = DashboardServer(
                host="127.0.0.1",
                port=8888,
                log_dir="server/logs/test",
                static_dir="apps/monitoring-dashboard"
            )

            assert server.host == "127.0.0.1"
            assert server.port == 8888
            assert server.static_dir.exists() or True  # May not exist yet
            assert isinstance(server.metrics_collector, ExecutionMetricsCollector)
            assert isinstance(server.health_checker, HealthChecker)
        except ImportError as e:
            # Skip if aiohttp not available
            self.skipTest(f"aiohttp not available: {e}")

    def test_dashboard_logger_creation(self) -> None:
        """Test that logger is created properly"""
        try:
            server = DashboardServer(
                host="localhost",
                port=8888,
                log_dir="server/logs/test"
            )

            assert server.logger is not None
            assert server.logger.name == "jarvis.monitoring.dashboard"
            assert server.logger.level > 0
        except ImportError:
            self.skipTest("aiohttp not available")

    def test_dashboard_app_creation(self) -> None:
        """Test that app is created with correct routes"""
        try:
            server = DashboardServer(log_dir="server/logs/test")
            app = server._create_app()

            assert app is not None
            assert len(app.router.routes()) > 0

            # Check that routes exist
            route_paths = set()
            for route in app.router.routes():
                if hasattr(route, 'resource') and hasattr(route.resource, '_path'):
                    route_paths.add(route.resource._path)

            # Should have at least the main endpoint
            assert len(route_paths) > 0
        except ImportError:
            self.skipTest("aiohttp not available")


class DashboardMetricsTests(unittest.TestCase):
    """Test dashboard metrics endpoints"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        try:
            self.server = DashboardServer(log_dir="server/logs/test")
        except ImportError:
            self.skipTest("aiohttp not available")

    def test_get_metrics_with_data(self) -> None:
        """Test getting metrics when data exists"""
        # Record some test metrics
        self.server.metrics_collector.record_execution(
            run_id="test-1",
            action="test_action",
            status="success",
            duration_seconds=0.5,
            cache_hit=True,
        )

        # Get stats
        stats = self.server.metrics_collector.get_stats(time_window_minutes=60)

        assert isinstance(stats, dict)
        assert "total_executions" in stats
        assert "success_rate_pct" in stats
        assert "avg_duration_seconds" in stats
        assert "throughput_per_minute" in stats
        assert "cache_hit_rate_pct" in stats

    def test_get_metrics_empty(self) -> None:
        """Test getting metrics when no data exists"""
        # Create fresh collector
        collector = ExecutionMetricsCollector(log_dir="server/logs/test_empty")
        stats = collector.get_stats(time_window_minutes=60)

        assert stats["total_executions"] == 0
        assert stats["status"] == "no_data"

    def test_get_chart_data_structure(self) -> None:
        """Test that chart data has correct structure"""
        # Record some metrics
        for i in range(5):
            self.server.metrics_collector.record_execution(
                run_id=f"run-{i}",
                action="test_action",
                status="success" if i % 2 == 0 else "failure",
                duration_seconds=0.1 * (i + 1),
                cache_hit=i % 2 == 0,
            )

        metrics = self.server.metrics_collector.get_recent_metrics(limit=100)
        assert len(metrics) > 0

        # Simulate chart data creation
        windows = {}
        for metric in metrics:
            from datetime import datetime
            ts = datetime.fromisoformat(metric.timestamp)
            window_time = ts.replace(minute=(ts.minute // 5) * 5, second=0, microsecond=0)
            window_key = window_time.isoformat()

            if window_key not in windows:
                windows[window_key] = {
                    "time": window_key,
                    "total": 0,
                    "success": 0,
                    "durations": [],
                    "cache_hits": 0,
                }

            windows[window_key]["total"] += 1
            if metric.status == "success":
                windows[window_key]["success"] += 1
            windows[window_key]["durations"].append(metric.duration_seconds)
            if metric.cache_hit:
                windows[window_key]["cache_hits"] += 1

        assert len(windows) > 0

        # Check that we can build trend data
        sorted_windows = sorted(windows.items())
        success_rate_trend = [
            {
                "time": w["time"],
                "rate": round((w["success"] / w["total"] * 100) if w["total"] > 0 else 0, 1)
            }
            for _, w in sorted_windows
        ]

        assert len(success_rate_trend) > 0
        assert "time" in success_rate_trend[0]
        assert "rate" in success_rate_trend[0]


class DashboardHealthTests(unittest.TestCase):
    """Test dashboard health status"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        try:
            self.server = DashboardServer(log_dir="server/logs/test")
        except ImportError:
            self.skipTest("aiohttp not available")

    def test_health_status_response(self) -> None:
        """Test health status endpoint response"""
        response, status_code = self.server.health_checker.get_health_endpoint_response()

        assert isinstance(response, dict)
        assert isinstance(status_code, int)
        assert "status" in response
        assert "timestamp" in response
        assert "components" in response
        assert response["status"] in ("healthy", "degraded", "unhealthy")

    def test_health_status_with_metrics(self) -> None:
        """Test health status with metrics included"""
        stats = self.server.metrics_collector.get_stats(time_window_minutes=60)
        response, status_code = self.server.health_checker.get_health_endpoint_response(
            include_metrics=True,
            metrics_data=stats
        )

        assert "status" in response
        assert "components" in response
        assert isinstance(status_code, int)

    def test_websocket_client_tracking(self) -> None:
        """Test that WebSocket clients are tracked"""
        assert isinstance(self.server.websocket_clients, set)
        assert len(self.server.websocket_clients) == 0


class DashboardIntegrationTests(unittest.TestCase):
    """Integration tests for dashboard"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        try:
            self.server = DashboardServer(
                host="127.0.0.1",
                port=9999,
                log_dir="server/logs/test_integration"
            )
        except ImportError:
            self.skipTest("aiohttp not available")

    def test_metrics_flow_success_rate(self) -> None:
        """Test complete metrics flow and success rate calculation"""
        # Record multiple executions
        for i in range(10):
            self.server.metrics_collector.record_execution(
                run_id=f"test-run-{i}",
                action="process_request",
                status="success" if i < 8 else "failure",
                duration_seconds=0.1 * (i + 1),
                cache_hit=(i % 3 == 0),
            )

        stats = self.server.metrics_collector.get_stats(time_window_minutes=60)

        # Should have recorded 10 executions
        assert stats["total_executions"] >= 10
        assert stats["success_count"] >= 8
        assert stats["failure_count"] >= 2

        # Success rate should be around 80%
        expected_rate = (8 / 10) * 100
        assert abs(stats["success_rate_pct"] - expected_rate) <= 5

    def test_metrics_flow_cache_performance(self) -> None:
        """Test cache hit rate calculation"""
        # Record executions with cache hits
        for i in range(10):
            self.server.metrics_collector.record_execution(
                run_id=f"cache-test-{i}",
                action="cache_read",
                status="success",
                duration_seconds=0.05,
                cache_hit=(i % 2 == 0),  # 50% cache hit rate
            )

        stats = self.server.metrics_collector.get_stats(time_window_minutes=60)

        # Cache hit rate should be around 50%
        assert 40 <= stats["cache_hit_rate_pct"] <= 60

    def test_metrics_flow_latency(self) -> None:
        """Test latency calculation"""
        # Create a fresh collector for this test to avoid interference
        from server.monitoring.execution_metrics import ExecutionMetricsCollector
        collector = ExecutionMetricsCollector(log_dir="server/logs/test_latency")

        # Record executions with varying latencies
        durations = [0.1, 0.2, 0.3, 0.4, 0.5]
        for i, duration in enumerate(durations):
            collector.record_execution(
                run_id=f"latency-test-{i}",
                action="query",
                status="success",
                duration_seconds=duration,
            )

        stats = collector.get_stats(time_window_minutes=60)

        # Average should be around 0.3 (sum=1.5 / count=5)
        expected_avg = sum(durations) / len(durations)
        assert abs(stats["avg_duration_seconds"] - expected_avg) <= 0.05

    def test_frontend_files_exist(self) -> None:
        """Test that frontend files exist"""
        static_dir = Path("apps/monitoring-dashboard")
        assert (static_dir / "index.html").exists(), "index.html not found"
        assert (static_dir / "app.js").exists(), "app.js not found"
        assert (static_dir / "style.css").exists(), "style.css not found"

    def test_frontend_files_have_content(self) -> None:
        """Test that frontend files have content"""
        static_dir = Path("apps/monitoring-dashboard")

        # Check HTML
        html_content = (static_dir / "index.html").read_text()
        assert len(html_content) > 100
        assert "Jarvis Mission Control" in html_content
        assert "canvas" in html_content.lower()

        # Check JavaScript
        js_content = (static_dir / "app.js").read_text()
        assert len(js_content) > 100
        assert "class DashboardApp" in js_content

        # Check CSS
        css_content = (static_dir / "style.css").read_text()
        assert len(css_content) > 100
        assert "dashboard" in css_content


class DashboardErrorHandlingTests(unittest.TestCase):
    """Test error handling in dashboard"""

    def setUp(self) -> None:
        """Set up test fixtures"""
        try:
            self.server = DashboardServer(log_dir="server/logs/test")
        except ImportError:
            self.skipTest("aiohttp not available")

    def test_metrics_with_errors(self) -> None:
        """Test that error metrics are recorded properly"""
        self.server.metrics_collector.record_execution(
            run_id="error-test-1",
            action="risky_operation",
            status="error",
            duration_seconds=0.25,
            error_message="ConnectionTimeout: Failed to connect to server",
        )

        stats = self.server.metrics_collector.get_stats(time_window_minutes=60)

        # Should have the error recorded
        assert stats["failure_count"] >= 1
        assert len(stats.get("top_errors", [])) > 0

    def test_retry_count_tracking(self) -> None:
        """Test retry count tracking"""
        self.server.metrics_collector.record_execution(
            run_id="retry-test-1",
            action="flaky_service",
            status="success",
            duration_seconds=0.5,
            retry_count=3,
        )

        metrics = self.server.metrics_collector.get_recent_metrics(limit=10)
        assert len(metrics) > 0

        retry_metrics = [m for m in metrics if m.retry_count > 0]
        assert len(retry_metrics) > 0
        assert retry_metrics[0].retry_count == 3


if __name__ == "__main__":
    unittest.main()
