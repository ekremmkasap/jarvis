"""
WEEK 3 ADVANCED LEARNING RULES TESTS - CALEB-5
Tests for context-aware improvement rules and pattern analysis
"""

import unittest
from datetime import datetime, timezone
from typing import Any

from server.agents.advanced_learning_rules import (
    AdvancedLearningRules,
    ImprovementContext,
)
from server.monitoring.pattern_analyzer import PatternAnalyzer


class TestAdvancedLearningRules(unittest.TestCase):
    """Test advanced learning rules implementation"""

    def setUp(self) -> None:
        self.rules = AdvancedLearningRules()
        self.analyzer = PatternAnalyzer()

    def test_context_detection_peak_hours(self) -> None:
        """Test context detection during peak hours"""
        metrics = {
            "success_rate": 0.95,
            "avg_duration_ms": 450,
            "cache_hit_rate": 0.75,
        }

        # 2 PM = peak hours
        context = self.rules.get_context(
            current_hour=14,
            active_requests=150,
            error_type=None,
            metrics=metrics,
        )

        self.assertEqual(context.time_of_day, "peak")
        self.assertEqual(context.current_load, "high")
        self.assertIsNone(context.error_cluster)
        self.assertEqual(context.success_rate, 0.95)

    def test_context_detection_off_peak(self) -> None:
        """Test context detection during off-peak hours"""
        metrics = {
            "success_rate": 0.93,
            "avg_duration_ms": 300,
            "cache_hit_rate": 0.8,
        }

        # 8 PM = off-peak hours
        context = self.rules.get_context(
            current_hour=20,
            active_requests=50,
            error_type=None,
            metrics=metrics,
        )

        self.assertEqual(context.time_of_day, "off_peak")
        self.assertEqual(context.current_load, "medium")

    def test_context_detection_night(self) -> None:
        """Test context detection during night hours"""
        metrics = {
            "success_rate": 0.98,
            "avg_duration_ms": 200,
            "cache_hit_rate": 0.85,
        }

        # 2 AM = night hours
        context = self.rules.get_context(
            current_hour=2,
            active_requests=10,
            error_type=None,
            metrics=metrics,
        )

        self.assertEqual(context.time_of_day, "night")
        self.assertEqual(context.current_load, "low")

    def test_context_detection_with_error(self) -> None:
        """Test context detection with error cluster"""
        metrics = {
            "success_rate": 0.85,
            "avg_duration_ms": 800,
            "cache_hit_rate": 0.5,
        }

        context = self.rules.get_context(
            current_hour=14,
            active_requests=120,
            error_type="timeout",
            metrics=metrics,
        )

        self.assertEqual(context.error_cluster, "timeout")

    def test_rule_selection_peak_high_load(self) -> None:
        """Test batch_execution rule selected during peak high-load"""
        context = ImprovementContext(
            time_of_day="peak",
            current_load="high",
            error_cluster=None,
            success_rate=0.92,
            avg_duration_ms=600,
            cache_hit_rate=0.7,
            active_requests=150,
            user_feedback_sentiment="positive",
        )

        applicable = self.rules.select_applicable_rules(context)
        self.assertIn("batch_execution", applicable)

    def test_rule_selection_low_cache_hit_rate(self) -> None:
        """Test smart_caching rule selected when cache hit rate is low"""
        context = ImprovementContext(
            time_of_day="peak",
            current_load="medium",
            error_cluster=None,
            success_rate=0.96,
            avg_duration_ms=500,
            cache_hit_rate=0.65,  # Low cache hit
            active_requests=80,
            user_feedback_sentiment="neutral",
        )

        applicable = self.rules.select_applicable_rules(context)
        self.assertIn("smart_caching", applicable)

    def test_rule_selection_high_load_positive_feedback(self) -> None:
        """Test resource_allocation rule selected with high load and positive feedback"""
        context = ImprovementContext(
            time_of_day="peak",
            current_load="high",
            error_cluster=None,
            success_rate=0.94,
            avg_duration_ms=500,
            cache_hit_rate=0.75,
            active_requests=120,
            user_feedback_sentiment="positive",
        )

        applicable = self.rules.select_applicable_rules(context)
        self.assertIn("resource_allocation", applicable)

    def test_batch_execution_rule(self) -> None:
        """Test batch_execution rule groups requests by action"""
        pending_requests = [
            {"action": "query", "id": "1"},
            {"action": "query", "id": "2"},
            {"action": "write", "id": "3"},
            {"action": "query", "id": "4"},
            {"action": "write", "id": "5"},
        ]

        context = ImprovementContext(
            time_of_day="peak",
            current_load="high",
            error_cluster=None,
            success_rate=0.95,
            avg_duration_ms=500,
            cache_hit_rate=0.75,
            active_requests=100,
            user_feedback_sentiment="neutral",
        )

        result = self.rules.batch_execution(pending_requests, context)

        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["batches_created"], 2)  # "query" and "write"
        self.assertEqual(result["total_requests"], 5)
        self.assertIn("batch_details", result)
        self.assertIn("batch_execution", self.rules.applied_rules)

    def test_smart_caching_rule(self) -> None:
        """Test smart_caching rule identifies cacheable patterns"""
        request_patterns = {
            "get_user_profile": 30,  # Frequent
            "search_index": 25,      # Frequent
            "get_config": 8,          # Somewhat frequent
            "delete_temp": 2,         # Not frequent enough
        }

        context = ImprovementContext(
            time_of_day="peak",
            current_load="high",
            error_cluster=None,
            success_rate=0.95,
            avg_duration_ms=500,
            cache_hit_rate=0.65,
            active_requests=100,
            user_feedback_sentiment="neutral",
        )

        result = self.rules.smart_caching(request_patterns, context)

        self.assertEqual(result["status"], "applied")
        self.assertGreater(result["cache_policies_created"], 0)
        self.assertIn("get_user_profile", result["cacheable_patterns"])
        self.assertIn("search_index", result["cacheable_patterns"])
        self.assertIn("smart_caching", self.rules.applied_rules)

    def test_resource_allocation_rule(self) -> None:
        """Test resource_allocation rule prioritizes top performers"""
        top_performers = [
            {"name": "query_agent", "performance_score": 0.95},
            {"name": "cache_agent", "performance_score": 0.88},
            {"name": "error_handler", "performance_score": 0.92},
        ]

        context = ImprovementContext(
            time_of_day="peak",
            current_load="high",
            error_cluster=None,
            success_rate=0.95,
            avg_duration_ms=500,
            cache_hit_rate=0.75,
            active_requests=120,
            user_feedback_sentiment="positive",
        )

        result = self.rules.resource_allocation(top_performers, context)

        self.assertEqual(result["status"], "applied")
        self.assertEqual(result["allocations"], 3)
        self.assertGreater(len(result["allocation_details"]), 0)
        self.assertIn("resource_allocation", self.rules.applied_rules)

    def test_user_feedback_positive(self) -> None:
        """Test user feedback tracking for accepted suggestions"""
        self.rules.add_user_feedback({
            "suggestion_id": "sugg_001",
            "accepted": True,
            "comment": "Works great",
        })
        self.rules.add_user_feedback({
            "suggestion_id": "sugg_002",
            "accepted": True,
            "comment": "Improved performance",
        })

        sentiment = self.rules._analyze_feedback_sentiment()
        self.assertEqual(sentiment, "positive")

    def test_user_feedback_negative(self) -> None:
        """Test user feedback sentiment when suggestions rejected"""
        for i in range(8):
            self.rules.add_user_feedback({
                "suggestion_id": f"sugg_{i:03d}",
                "accepted": False,
                "sentiment": "negative",
            })

        sentiment = self.rules._analyze_feedback_sentiment()
        self.assertEqual(sentiment, "negative")

    def test_user_feedback_neutral(self) -> None:
        """Test neutral feedback sentiment"""
        self.rules.add_user_feedback({
            "suggestion_id": "sugg_001",
            "accepted": True,
        })
        self.rules.add_user_feedback({
            "suggestion_id": "sugg_002",
            "accepted": False,
        })
        self.rules.add_user_feedback({
            "suggestion_id": "sugg_003",
            "accepted": True,
        })

        sentiment = self.rules._analyze_feedback_sentiment()
        self.assertEqual(sentiment, "neutral")

    def test_predict_before_issue_declining_success(self) -> None:
        """Test prediction detects declining success rate"""
        metrics_history = [
            {"success_rate": 0.95, "avg_duration_ms": 450},
            {"success_rate": 0.92, "avg_duration_ms": 480},
            {"success_rate": 0.88, "avg_duration_ms": 520},
        ]

        result = self.rules.predict_before_issue(metrics_history)

        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["predictions"]), 0)

        # Check for declining success rate prediction
        has_success_decline = any(
            p["issue_type"] == "declining_success_rate"
            for p in result["predictions"]
        )
        self.assertTrue(has_success_decline)

    def test_predict_before_issue_increasing_latency(self) -> None:
        """Test prediction detects increasing latency"""
        metrics_history = [
            {"success_rate": 0.96, "avg_duration_ms": 300},
            {"success_rate": 0.95, "avg_duration_ms": 400},
            {"success_rate": 0.94, "avg_duration_ms": 500},
        ]

        result = self.rules.predict_before_issue(metrics_history)

        self.assertEqual(result["status"], "success")
        has_latency_prediction = any(
            p["issue_type"] == "increasing_latency"
            for p in result["predictions"]
        )
        self.assertTrue(has_latency_prediction)

    def test_feedback_summary(self) -> None:
        """Test feedback summary generation"""
        for i in range(5):
            self.rules.add_user_feedback({
                "suggestion_id": f"sugg_{i:03d}",
                "accepted": i % 2 == 0,
            })

        summary = self.rules.get_feedback_summary()

        self.assertEqual(summary["total_feedback"], 5)
        self.assertIn("acceptance_rate", summary)
        self.assertIn("sentiment", summary)


class TestPatternAnalyzer(unittest.TestCase):
    """Test pattern analyzer for context detection"""

    def setUp(self) -> None:
        self.analyzer = PatternAnalyzer()
        self.base_timestamp = datetime.now(timezone.utc).isoformat()

    def _create_metric(
        self,
        action: str,
        status: str,
        duration_seconds: float = 0.5,
        error_message: str | None = None,
        timestamp_offset_minutes: int = 0,
    ) -> dict[str, Any]:
        """Helper to create test metrics"""
        ts = datetime.fromisoformat(self.base_timestamp)
        if timestamp_offset_minutes != 0:
            from datetime import timedelta
            ts = ts + timedelta(minutes=timestamp_offset_minutes)

        return {
            "timestamp": ts.isoformat(),
            "run_id": f"run_{action}_{status}",
            "action": action,
            "status": status,
            "duration_seconds": duration_seconds,
            "error_message": error_message,
        }

    def test_time_of_day_pattern_detection(self) -> None:
        """Test detection of peak/off-peak hours"""
        metrics = []
        # Create metrics for different hours
        for hour in range(24):
            count = 30 if 9 <= hour <= 17 else 10  # More requests during 9-17
            for _ in range(count):
                ts = datetime.now(timezone.utc).replace(hour=hour, minute=0, second=0)
                metrics.append({
                    "timestamp": ts.isoformat(),
                    "status": "success",
                    "duration_seconds": 0.5,
                })

        result = self.analyzer.detect_time_of_day_pattern(metrics)

        self.assertEqual(result["status"], "success")
        self.assertIn("peak_hours", result)
        self.assertIn("hourly_breakdown", result)

    def test_load_pattern_detection(self) -> None:
        """Test detection of system load patterns"""
        metrics = []
        # High load first, then low load
        for minute in range(30):
            count = 25 if minute < 15 else 5
            for _ in range(count):
                offset = minute
                metrics.append(self._create_metric(
                    "query",
                    "success",
                    timestamp_offset_minutes=offset
                ))

        result = self.analyzer.detect_load_patterns(metrics)

        self.assertEqual(result["status"], "success")
        self.assertIn("avg_requests_per_minute", result)
        self.assertIn("high_load_period_pct", result)

    def test_error_clustering_detection(self) -> None:
        """Test detection of error clusters"""
        metrics = []
        # Create cluster of timeout errors
        for i in range(5):
            metrics.append(self._create_metric(
                "query",
                "error",
                error_message="TimeoutError: Connection timeout",
                timestamp_offset_minutes=i
            ))

        # Some normal errors
        for i in range(2):
            metrics.append(self._create_metric(
                "write",
                "error",
                error_message="ValidationError: Invalid input",
                timestamp_offset_minutes=i + 10
            ))

        result = self.analyzer.detect_error_clusters(metrics)

        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["clusters"]), 0)
        # Should identify timeout as a cluster
        has_timeout_cluster = any(
            "Timeout" in c["error_type"] for c in result["clusters"]
        )
        self.assertTrue(has_timeout_cluster)

    def test_request_pattern_detection(self) -> None:
        """Test detection of frequent request patterns"""
        metrics = []
        # Frequent query actions
        for _ in range(20):
            metrics.append(self._create_metric("query", "success"))

        # Moderate write actions
        for _ in range(8):
            metrics.append(self._create_metric("write", "success"))

        # Rare delete actions
        for _ in range(2):
            metrics.append(self._create_metric("delete", "success"))

        result = self.analyzer.detect_request_patterns(metrics)

        self.assertEqual(result["status"], "success")
        self.assertGreater(len(result["patterns"]), 0)
        # Query should be top pattern
        if result["patterns"]:
            self.assertEqual(result["patterns"][0]["action"], "query")

    def test_issue_prediction_declining_success(self) -> None:
        """Test prediction of declining success rate"""
        metrics = [
            self._create_metric("query", "success"),
            self._create_metric("query", "success"),
            self._create_metric("query", "success"),
            self._create_metric("query", "success"),
            self._create_metric("query", "error"),  # Declining
        ]

        result = self.analyzer.predict_issues(metrics)

        # With low success rate, should predict issues
        self.assertIn("predictions", result)

    def test_issue_prediction_increasing_latency(self) -> None:
        """Test prediction of increasing latency"""
        metrics = [
            self._create_metric("query", "success", duration_seconds=0.2),
            self._create_metric("query", "success", duration_seconds=0.25),
            self._create_metric("query", "success", duration_seconds=0.3),
            self._create_metric("query", "success", duration_seconds=0.5),
            self._create_metric("query", "success", duration_seconds=0.6),
        ]

        result = self.analyzer.predict_issues(metrics)

        # With increasing duration, should predict latency issue
        self.assertIn("predictions", result)

    def test_comprehensive_analysis(self) -> None:
        """Test comprehensive pattern analysis"""
        metrics = []
        # Create diverse metrics
        for i in range(50):
            hour = (i // 5) % 24
            action = ["query", "write", "delete"][i % 3]
            status = "success" if i % 10 < 8 else "error"

            ts = datetime.now(timezone.utc).replace(hour=hour % 24, minute=i % 60)
            metrics.append({
                "timestamp": ts.isoformat(),
                "action": action,
                "status": status,
                "duration_seconds": 0.3 + (i % 5) * 0.1,
                "error_message": "TestError" if status == "error" else None,
            })

        result = self.analyzer.analyze_comprehensive(metrics)

        self.assertEqual(result["status"], "success" if metrics else "no_data")
        self.assertIn("time_patterns", result)
        self.assertIn("load_patterns", result)
        self.assertIn("error_clusters", result)
        self.assertIn("request_patterns", result)
        self.assertIn("predictions", result)

    def test_pattern_summary(self) -> None:
        """Test pattern summary generation"""
        summary = self.analyzer.get_pattern_summary()

        self.assertIn("error_clusters", summary)
        self.assertIn("request_patterns", summary)
        self.assertIn("pattern_history_size", summary)


if __name__ == "__main__":
    unittest.main()
