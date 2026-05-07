"""
WEEK 3 PATTERN ANALYZER - Context Detection & Prediction
Analyzes execution patterns, detects context, and provides predictive insights
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
from collections import defaultdict, Counter


class PatternAnalyzer:
    """Context detection and predictive analysis for system patterns"""

    def __init__(self, lookback_minutes: int = 120):
        self.logger = logging.getLogger("jarvis.pattern_analyzer")
        self.lookback_minutes = lookback_minutes
        self.pattern_history: list[dict[str, Any]] = []
        self.error_clusters: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.request_patterns: dict[str, int] = Counter()

    def detect_time_of_day_pattern(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Analyze metrics by time-of-day to detect patterns

        Args:
            metrics: List of metrics with timestamps

        Returns:
            Dictionary with peak hours, off-peak hours, patterns
        """
        if not metrics:
            return {"status": "no_data"}

        # Group by hour
        hourly_stats: dict[int, dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "success_count": 0,
            "total_duration": 0,
            "errors": []
        })

        for metric in metrics:
            try:
                timestamp = metric.get("timestamp", "")
                status = metric.get("status", "")
                duration = metric.get("duration_seconds", 0)

                # Parse hour from ISO timestamp
                if "T" in timestamp:
                    hour = int(timestamp.split("T")[1].split(":")[0])
                    hourly_stats[hour]["count"] += 1
                    if status == "success":
                        hourly_stats[hour]["success_count"] += 1
                    hourly_stats[hour]["total_duration"] += duration
                    if status in ["error", "failure"]:
                        hourly_stats[hour]["errors"].append(metric.get("error_message", "unknown"))
            except (IndexError, ValueError):
                continue

        # Analyze patterns
        peak_hours = []
        off_peak_hours = []
        avg_request_count = sum(s["count"] for s in hourly_stats.values()) / len(hourly_stats) if hourly_stats else 0

        for hour, stats in sorted(hourly_stats.items()):
            if stats["count"] > avg_request_count * 1.3:
                peak_hours.append(hour)
            elif stats["count"] < avg_request_count * 0.7:
                off_peak_hours.append(hour)

        result = {
            "status": "success",
            "peak_hours": peak_hours,
            "off_peak_hours": off_peak_hours,
            "hourly_breakdown": {
                str(h): {
                    "requests": stats["count"],
                    "success_rate": f"{stats['success_count']/stats['count']:.1%}" if stats["count"] > 0 else "N/A",
                    "avg_duration_ms": f"{(stats['total_duration']/stats['count']*1000):.0f}" if stats["count"] > 0 else "N/A",
                }
                for h, stats in hourly_stats.items()
            }
        }

        self.logger.info(f"Time-of-day pattern: peak_hours={peak_hours}")
        return result

    def detect_load_patterns(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Detect system load patterns from metrics

        Args:
            metrics: List of metrics

        Returns:
            Load pattern analysis
        """
        if not metrics:
            return {"status": "no_data"}

        durations = [m.get("duration_seconds", 0) for m in metrics]
        request_counts = []

        # Group by minute and count requests
        minute_requests: dict[str, int] = defaultdict(int)
        for metric in metrics:
            try:
                timestamp = metric.get("timestamp", "")
                if "T" in timestamp:
                    minute_key = timestamp[:16]  # YYYY-MM-DDTHH:MM
                    minute_requests[minute_key] += 1
            except (IndexError, ValueError):
                continue

        request_counts = list(minute_requests.values())

        if not request_counts:
            return {"status": "no_data"}

        avg_requests_per_minute = sum(request_counts) / len(request_counts)
        max_requests = max(request_counts)
        min_requests = min(request_counts)

        # Classify load
        high_threshold = avg_requests_per_minute * 1.5
        low_threshold = avg_requests_per_minute * 0.5

        high_load_minutes = sum(1 for c in request_counts if c > high_threshold)
        low_load_minutes = sum(1 for c in request_counts if c < low_threshold)

        result = {
            "status": "success",
            "avg_requests_per_minute": f"{avg_requests_per_minute:.1f}",
            "max_requests_per_minute": max_requests,
            "min_requests_per_minute": min_requests,
            "high_load_period_pct": f"{high_load_minutes/len(request_counts)*100:.1f}%" if request_counts else "N/A",
            "low_load_period_pct": f"{low_load_minutes/len(request_counts)*100:.1f}%" if request_counts else "N/A",
            "load_variability": f"{(max_requests - min_requests) / avg_requests_per_minute:.2f}x" if avg_requests_per_minute > 0 else "N/A",
        }

        self.logger.info(f"Load patterns detected: avg={avg_requests_per_minute:.1f} req/min")
        return result

    def detect_error_clusters(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Detect clusters of similar errors

        Args:
            metrics: List of metrics

        Returns:
            Error clustering analysis
        """
        if not metrics:
            return {"status": "no_data", "clusters": []}

        # Group errors
        error_types: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for metric in metrics:
            status = metric.get("status", "")
            if status in ["error", "failure"]:
                error_msg = metric.get("error_message") or "unknown_error"
                # Simplify error message to get error type
                error_type = error_msg.split(":")[0] if ":" in error_msg else error_msg[:30]
                error_types[error_type].append(metric)

        if not error_types:
            return {"status": "no_errors", "clusters": []}

        # Analyze clusters
        clusters = []
        for error_type, errors in error_types.items():
            if len(errors) >= 2:  # Only report clusters of 2+
                time_windows = []
                sorted_errors = sorted(errors, key=lambda e: e.get("timestamp", ""))

                # Check for temporal clustering
                for i in range(len(sorted_errors) - 1):
                    try:
                        curr_ts = datetime.fromisoformat(sorted_errors[i].get("timestamp", ""))
                        next_ts = datetime.fromisoformat(sorted_errors[i + 1].get("timestamp", ""))
                        delta_seconds = (next_ts - curr_ts).total_seconds()
                        if delta_seconds < 300:  # Within 5 minutes
                            time_windows.append(delta_seconds)
                    except (ValueError, TypeError):
                        continue

                is_temporal_cluster = len(time_windows) > len(errors) * 0.5

                clusters.append({
                    "error_type": error_type,
                    "count": len(errors),
                    "is_temporal_cluster": is_temporal_cluster,
                    "first_occurrence": errors[0].get("timestamp", "unknown"),
                    "last_occurrence": errors[-1].get("timestamp", "unknown"),
                    "avg_time_between_errors_sec": f"{sum(time_windows)/len(time_windows):.1f}" if time_windows else "N/A",
                })

                self.error_clusters[error_type] = errors

        result = {
            "status": "success" if clusters else "no_clusters",
            "clusters": clusters,
            "total_error_types": len(error_types),
            "critical_clusters": [c for c in clusters if c.get("count", 0) >= 5],
        }

        self.logger.info(f"Error clusters detected: {len(clusters)} clusters")
        return result

    def detect_request_patterns(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Detect frequently occurring request patterns

        Args:
            metrics: List of metrics

        Returns:
            Request pattern analysis
        """
        if not metrics:
            return {"status": "no_data", "patterns": []}

        # Count action types
        action_counter = Counter()
        action_details: dict[str, dict[str, Any]] = {}

        for metric in metrics:
            action = metric.get("action", "unknown")
            action_counter[action] += 1

            if action not in action_details:
                action_details[action] = {
                    "total_duration": 0,
                    "success_count": 0,
                    "count": 0,
                }
            action_details[action]["total_duration"] += metric.get("duration_seconds", 0)
            action_details[action]["count"] += 1
            if metric.get("status") == "success":
                action_details[action]["success_count"] += 1

        # Find top patterns (frequency > 5)
        patterns = []
        for action, count in action_counter.most_common():
            if count >= 5:
                details = action_details[action]
                patterns.append({
                    "action": action,
                    "frequency": count,
                    "success_rate": f"{details['success_count']/details['count']:.1%}" if details["count"] > 0 else "N/A",
                    "avg_duration_ms": f"{(details['total_duration']/details['count']*1000):.0f}" if details["count"] > 0 else "N/A",
                })
                # Store in request_patterns for caching rule
                self.request_patterns[action] = count

        result = {
            "status": "success" if patterns else "no_patterns",
            "patterns": patterns,
            "total_actions": len(action_counter),
            "top_pattern": patterns[0]["action"] if patterns else None,
        }

        self.logger.info(f"Request patterns detected: {len(patterns)} patterns")
        return result

    def predict_issues(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Predict potential issues before they occur

        Args:
            metrics: List of recent metrics

        Returns:
            Predictions with severity and suggested actions
        """
        if len(metrics) < 5:
            return {"status": "insufficient_data", "predictions": []}

        predictions = []

        # 1. Success rate declining?
        recent_metrics = metrics[-5:]
        success_rates = [m.get("status") == "success" for m in recent_metrics]
        success_rate = sum(success_rates) / len(success_rates)

        if success_rate < 0.85:
            predictions.append({
                "type": "declining_success",
                "severity": "high" if success_rate < 0.75 else "medium",
                "current_rate": f"{success_rate:.1%}",
                "suggested_action": "Increase resilience rules and error handling",
                "priority_rules": ["resource_allocation", "smart_caching"],
            })

        # 2. Latency increasing?
        durations = [m.get("duration_seconds", 0) for m in recent_metrics]
        if len(durations) >= 2:
            avg_recent = sum(durations[-3:]) / 3 if len(durations) >= 3 else durations[-1]
            avg_older = sum(durations[:-3]) / (len(durations) - 3) if len(durations) > 3 else durations[0]

            if avg_recent > avg_older * 1.2:
                predictions.append({
                    "type": "increasing_latency",
                    "severity": "medium",
                    "current_avg_ms": f"{avg_recent*1000:.0f}",
                    "previous_avg_ms": f"{avg_older*1000:.0f}",
                    "suggested_action": "Apply batch execution and optimize caching",
                    "priority_rules": ["batch_execution", "resource_allocation"],
                })

        # 3. Error clustering?
        error_clusters = self.detect_error_clusters(metrics)
        if error_clusters.get("critical_clusters"):
            for cluster in error_clusters["critical_clusters"]:
                predictions.append({
                    "type": f"error_cluster_{cluster['error_type']}",
                    "severity": "high",
                    "error_count": cluster["count"],
                    "suggested_action": "Investigate root cause and apply targeted fixes",
                    "priority_rules": ["resource_allocation"],
                })

        result = {
            "status": "success" if predictions else "healthy",
            "predictions": predictions,
            "total_alerts": len(predictions),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info(f"Predictions made: {len(predictions)} potential issues")
        return result

    def analyze_comprehensive(self, metrics: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Run comprehensive pattern analysis

        Args:
            metrics: List of all recent metrics

        Returns:
            Complete analysis with all patterns and predictions
        """
        if not metrics:
            return {"status": "no_data"}

        result = {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics_analyzed": len(metrics),
            "time_patterns": self.detect_time_of_day_pattern(metrics),
            "load_patterns": self.detect_load_patterns(metrics),
            "error_clusters": self.detect_error_clusters(metrics),
            "request_patterns": self.detect_request_patterns(metrics),
            "predictions": self.predict_issues(metrics),
        }

        self.logger.info("Comprehensive analysis completed")
        return result

    def get_pattern_summary(self) -> dict[str, Any]:
        """Get current pattern summary for display"""
        return {
            "error_clusters": len(self.error_clusters),
            "request_patterns": len(self.request_patterns),
            "pattern_history_size": len(self.pattern_history),
        }
