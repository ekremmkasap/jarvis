#!/usr/bin/env python3
"""
Tests for Telegram Intelligence System (Caleb-3)
Smart alerts and command processing
"""

from __future__ import annotations

import unittest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

from server.telegram.telegram_intelligence import (
    TelegramIntelligence,
    Alert,
    AlertLevel,
    RateLimiter
)


class RateLimiterTests(unittest.TestCase):
    """Test rate limiting functionality"""

    def test_initial_alert_allowed(self) -> None:
        """Test that first alert is allowed"""
        limiter = RateLimiter(max_alerts_per_minute=1)
        assert limiter.should_alert("test_rule") is True

    def test_rate_limiting_blocks_second_alert(self) -> None:
        """Test that second alert within 1 minute is blocked"""
        limiter = RateLimiter(max_alerts_per_minute=1)
        assert limiter.should_alert("test_rule") is True
        assert limiter.should_alert("test_rule") is False

    def test_different_rules_not_rate_limited(self) -> None:
        """Test that different rules have independent rate limits"""
        limiter = RateLimiter(max_alerts_per_minute=1)
        assert limiter.should_alert("rule_1") is True
        assert limiter.should_alert("rule_2") is True
        assert limiter.should_alert("rule_1") is False


class AlertRulesTests(unittest.TestCase):
    """Test alert rules"""

    def setUp(self) -> None:
        """Set up test fixture"""
        self.temp_dir = tempfile.mkdtemp()
        self.intel = TelegramIntelligence(log_dir=self.temp_dir)

    def tearDown(self) -> None:
        """Clean up test fixture"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_error_threshold_alert(self) -> None:
        """Test error threshold rule triggers alert"""
        alert = self.intel.check_error_threshold(
            error_rate=0.10,
            threshold=0.05
        )
        assert alert is not None
        assert alert.rule_name == "error_threshold"
        assert alert.level == AlertLevel.ERROR.value
        assert "Error rate" in alert.message

    def test_error_threshold_critical_level(self) -> None:
        """Test CRITICAL level for very high error rates"""
        alert = self.intel.check_error_threshold(
            error_rate=0.20,
            threshold=0.05
        )
        assert alert is not None
        assert alert.level == AlertLevel.CRITICAL.value

    def test_error_threshold_no_alert_below_threshold(self) -> None:
        """Test no alert when error rate is below threshold"""
        alert = self.intel.check_error_threshold(
            error_rate=0.02,
            threshold=0.05
        )
        assert alert is None

    def test_latency_spike_alert(self) -> None:
        """Test latency spike rule triggers alert"""
        alert = self.intel.check_latency_spike(
            current_latency=2.6,
            baseline_latency=1.0,
            spike_factor=2.5
        )
        assert alert is not None
        assert alert.rule_name == "latency_spike"
        assert alert.level == AlertLevel.WARNING.value
        assert "spike" in alert.message.lower()

    def test_latency_spike_critical_level(self) -> None:
        """Test CRITICAL level for extreme latency spikes"""
        alert = self.intel.check_latency_spike(
            current_latency=5.5,
            baseline_latency=1.0,
            spike_factor=2.5
        )
        assert alert is not None
        assert alert.level == AlertLevel.CRITICAL.value

    def test_latency_spike_no_alert_below_spike_factor(self) -> None:
        """Test no alert when latency is below spike factor"""
        alert = self.intel.check_latency_spike(
            current_latency=1.5,
            baseline_latency=1.0,
            spike_factor=2.5
        )
        assert alert is None

    def test_learning_event_alert(self) -> None:
        """Test learning event rule triggers alert"""
        alert = self.intel.check_learning_event(
            improvement_pct=0.05,
            min_improvement=0.01
        )
        assert alert is not None
        assert alert.rule_name == "learning_event"
        assert alert.level == AlertLevel.INFO.value
        assert "improvement" in alert.message.lower()

    def test_learning_event_no_alert_below_threshold(self) -> None:
        """Test no alert when improvement is below threshold"""
        alert = self.intel.check_learning_event(
            improvement_pct=0.005,
            min_improvement=0.01
        )
        assert alert is None


class CommandFormattingTests(unittest.TestCase):
    """Test message formatting for commands"""

    def setUp(self) -> None:
        """Set up test fixture"""
        self.temp_dir = tempfile.mkdtemp()
        self.intel = TelegramIntelligence(log_dir=self.temp_dir)

    def tearDown(self) -> None:
        """Clean up test fixture"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_format_health_message(self) -> None:
        """Test /health message formatting"""
        metrics = {
            "status": "healthy",
            "uptime_seconds": 3600,
            "error_count": 2,
            "total_requests": 100
        }
        msg = self.intel.format_health_message(metrics)
        assert "System Health Status" in msg
        assert "healthy" in msg
        assert "1.0h" in msg or "1 h" in msg

    def test_format_metrics_message(self) -> None:
        """Test /metrics message formatting"""
        metrics = {
            "avg_latency_ms": 45.5,
            "p95_latency_ms": 120.3,
            "cache_hit_rate": 0.85,
            "total_executions": 150
        }
        msg = self.intel.format_metrics_message(metrics)
        assert "Execution Metrics" in msg
        assert "45.50ms" in msg or "45.5" in msg
        assert "150" in msg

    def test_format_improvements_message_with_suggestions(self) -> None:
        """Test /improve message formatting with suggestions"""
        improvements = [
            {"title": "Cache optimization", "impact_score": 0.8},
            {"title": "Query reuse", "impact_score": 0.6}
        ]
        msg = self.intel.format_improvements_message(improvements)
        assert "Suggested Improvements" in msg
        assert "Cache optimization" in msg
        assert "Query reuse" in msg

    def test_format_improvements_message_empty(self) -> None:
        """Test /improve message formatting with no suggestions"""
        msg = self.intel.format_improvements_message([])
        assert "No improvement suggestions" in msg

    def test_format_rollback_message_success(self) -> None:
        """Test /rollback success message"""
        result = {
            "success": True,
            "revision": "abc123",
            "message": "Reverted changes"
        }
        msg = self.intel.format_rollback_message(result)
        assert "Rollback Successful" in msg
        assert "abc123" in msg

    def test_format_rollback_message_failure(self) -> None:
        """Test /rollback failure message"""
        result = {
            "success": False,
            "message": "No previous revision found"
        }
        msg = self.intel.format_rollback_message(result)
        assert "Rollback Failed" in msg
        assert "No previous revision" in msg

    def test_format_cache_message(self) -> None:
        """Test /cache message formatting"""
        cache_stats = {
            "hits": 450,
            "misses": 50,
            "size_mb": 125.5
        }
        msg = self.intel.format_cache_message(cache_stats)
        assert "Cache Statistics" in msg
        assert "450" in msg
        assert "90.0%" in msg or "90%" in msg


class AlertLoggingTests(unittest.TestCase):
    """Test alert logging and retrieval"""

    def setUp(self) -> None:
        """Set up test fixture"""
        self.temp_dir = tempfile.mkdtemp()
        self.intel = TelegramIntelligence(log_dir=self.temp_dir)

    def tearDown(self) -> None:
        """Clean up test fixture"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_alert_is_logged_to_file(self) -> None:
        """Test that alerts are logged to file"""
        alert = self.intel.check_error_threshold(
            error_rate=0.10,
            threshold=0.05
        )
        assert alert is not None
        assert self.intel.alerts_file.exists()
        with open(self.intel.alerts_file) as f:
            content = f.read()
            assert "error_threshold" in content

    def test_get_recent_alerts(self) -> None:
        """Test retrieving recent alerts"""
        # Generate some alerts
        for i in range(3):
            self.intel.check_error_threshold(
                error_rate=0.10 + i * 0.05,
                threshold=0.05
            )

        alerts = self.intel.get_recent_alerts(limit=10)
        assert len(alerts) >= 1

    def test_get_alert_summary(self) -> None:
        """Test alert summary generation"""
        # Generate alerts
        self.intel.check_error_threshold(error_rate=0.10, threshold=0.05)
        self.intel.check_latency_spike(current_latency=2.6, baseline_latency=1.0)

        summary = self.intel.get_alert_summary(time_window_minutes=60)
        assert summary["total"] >= 1
        assert "by_level" in summary
        assert "by_rule" in summary


class CommandLoggingTests(unittest.TestCase):
    """Test command logging and reporting"""

    def setUp(self) -> None:
        """Set up test fixture"""
        self.temp_dir = tempfile.mkdtemp()
        self.intel = TelegramIntelligence(log_dir=self.temp_dir)

    def tearDown(self) -> None:
        """Clean up test fixture"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_command(self) -> None:
        """Test logging command execution"""
        self.intel.log_command(
            command="/health",
            chat_id=12345,
            status="success",
            response_length=150
        )
        assert self.intel.commands_file.exists()

    def test_command_is_logged_to_file(self) -> None:
        """Test that command data is written to file"""
        self.intel.log_command(
            command="/metrics",
            chat_id=12345,
            status="success",
            response_length=200
        )
        with open(self.intel.commands_file) as f:
            content = f.read()
            assert "/metrics" in content
            assert "12345" in content

    def test_get_command_summary(self) -> None:
        """Test command summary generation"""
        self.intel.log_command("/health", 12345, "success", 150)
        self.intel.log_command("/metrics", 12345, "success", 200)
        self.intel.log_command("/health", 12345, "error", 50)

        summary = self.intel.get_command_summary(time_window_minutes=60)
        assert summary["total"] >= 2
        assert summary["success_rate"] > 0


if __name__ == "__main__":
    unittest.main()
