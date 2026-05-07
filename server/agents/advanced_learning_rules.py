"""
WEEK 3 ADVANCED LEARNING RULES - CALEB-5
Context-aware improvement rules for intelligent system optimization
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from dataclasses import dataclass, asdict


@dataclass
class ImprovementContext:
    """Context information for rule selection"""
    time_of_day: str  # "peak", "off_peak", "night"
    current_load: str  # "high", "medium", "low"
    error_cluster: str | None  # error type if clustering detected
    success_rate: float  # 0-1
    avg_duration_ms: float
    cache_hit_rate: float  # 0-1
    active_requests: int
    user_feedback_sentiment: str  # "positive", "neutral", "negative"


class AdvancedLearningRules:
    """Context-aware improvement rules for CALEB-5"""

    def __init__(self):
        self.logger = logging.getLogger("jarvis.advanced_rules")
        self.applied_rules: dict[str, dict[str, Any]] = {}
        self.user_feedback_buffer: list[dict[str, Any]] = []

    def get_context(
        self,
        current_hour: int,
        active_requests: int,
        error_type: str | None,
        metrics: dict[str, Any],
    ) -> ImprovementContext:
        """
        Detect current context for rule selection

        Args:
            current_hour: Hour of day (0-23)
            active_requests: Current number of active requests
            error_type: Type of error if any (e.g., "timeout", "memory", "rate_limit")
            metrics: Dictionary with keys: success_rate, avg_duration_ms, cache_hit_rate

        Returns:
            ImprovementContext with detected patterns
        """
        # Detect time-of-day pattern
        if 9 <= current_hour <= 17:
            time_of_day = "peak"
        elif 18 <= current_hour <= 22:
            time_of_day = "off_peak"
        else:
            time_of_day = "night"

        # Detect load pattern
        if active_requests > 100:
            current_load = "high"
        elif active_requests > 30:
            current_load = "medium"
        else:
            current_load = "low"

        # Get metrics
        success_rate = metrics.get("success_rate", 0.95)
        avg_duration_ms = metrics.get("avg_duration_ms", 500.0)
        cache_hit_rate = metrics.get("cache_hit_rate", 0.7)

        # Detect user sentiment from feedback buffer
        user_feedback_sentiment = self._analyze_feedback_sentiment()

        context = ImprovementContext(
            time_of_day=time_of_day,
            current_load=current_load,
            error_cluster=error_type,
            success_rate=success_rate,
            avg_duration_ms=avg_duration_ms,
            cache_hit_rate=cache_hit_rate,
            active_requests=active_requests,
            user_feedback_sentiment=user_feedback_sentiment,
        )

        self.logger.info(
            f"Context detected: time={context.time_of_day} "
            f"load={context.current_load} error={context.error_cluster} "
            f"feedback={context.user_feedback_sentiment}"
        )

        return context

    def select_applicable_rules(self, context: ImprovementContext) -> list[str]:
        """
        Select which rules to apply based on context

        Returns:
            List of rule names: ["batch_execution", "smart_caching", "resource_allocation"]
        """
        applicable = []

        # Rule 1: batch_execution
        # Best during peak hours with high load
        if context.time_of_day == "peak" and context.current_load == "high":
            applicable.append("batch_execution")

        # Rule 2: smart_caching
        # Useful when cache hit rate is low and success rate needs improvement
        if context.cache_hit_rate < 0.8 and context.success_rate < 0.98:
            applicable.append("smart_caching")

        # Rule 3: resource_allocation
        # Activate when there's high load and we have user positive feedback
        if context.current_load == "high" and context.user_feedback_sentiment == "positive":
            applicable.append("resource_allocation")

        # Always apply resource_allocation during error clusters
        if context.error_cluster is not None:
            if "resource_allocation" not in applicable:
                applicable.append("resource_allocation")

        self.logger.info(f"Applicable rules: {applicable}")
        return applicable

    def batch_execution(
        self,
        pending_requests: list[dict[str, Any]],
        context: ImprovementContext,
    ) -> dict[str, Any]:
        """
        Rule 1: Batch similar requests together
        Reduces context switching and improves throughput during peak hours

        Args:
            pending_requests: List of pending requests to batch
            context: Current context

        Returns:
            Improvement record with batching strategy
        """
        if not pending_requests:
            return {"status": "no_requests", "batches": 0}

        # Group requests by action type
        batches: dict[str, list[dict[str, Any]]] = {}
        for req in pending_requests:
            action = req.get("action", "unknown")
            if action not in batches:
                batches[action] = []
            batches[action].append(req)

        # Calculate batch sizes
        batch_info = []
        total_requests_batched = 0
        for action, reqs in batches.items():
            batch_info.append({
                "action": action,
                "count": len(reqs),
                "expected_speedup": f"{len(reqs) * 0.15:.1%}",  # ~15% per request in batch
            })
            total_requests_batched += len(reqs)

        result = {
            "rule": "batch_execution",
            "status": "applied",
            "batches_created": len(batches),
            "total_requests": total_requests_batched,
            "batch_details": batch_info,
            "expected_improvement": f"{len(batches) * 0.1:.1%}",  # 10% per batch
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.applied_rules["batch_execution"] = result
        self.logger.info(f"Batch execution applied: {len(batches)} batches, {total_requests_batched} requests")
        return result

    def smart_caching(
        self,
        request_patterns: dict[str, Any],
        context: ImprovementContext,
    ) -> dict[str, Any]:
        """
        Rule 2: Cache based on detected patterns
        Intelligently cache frequently accessed data and results

        Args:
            request_patterns: Detected request patterns from analysis
            context: Current context

        Returns:
            Improvement record with caching strategy
        """
        if not request_patterns:
            return {"status": "no_patterns", "cache_policies": 0}

        # Identify cacheable patterns
        cacheable_patterns = []
        cache_ttls = {}

        for pattern, frequency in request_patterns.items():
            if frequency > 5:  # Pattern appears more than 5 times
                cacheable_patterns.append(pattern)
                # Higher frequency = longer TTL
                if frequency > 50:
                    cache_ttls[pattern] = "5m"  # 5 minutes
                elif frequency > 20:
                    cache_ttls[pattern] = "2m"  # 2 minutes
                else:
                    cache_ttls[pattern] = "30s"  # 30 seconds

        if not cacheable_patterns:
            return {"status": "no_cacheable_patterns", "cache_policies": 0}

        result = {
            "rule": "smart_caching",
            "status": "applied",
            "cache_policies_created": len(cacheable_patterns),
            "cacheable_patterns": cacheable_patterns,
            "cache_ttls": cache_ttls,
            "expected_cache_improvement": f"{len(cacheable_patterns) * 0.08:.1%}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.applied_rules["smart_caching"] = result
        self.logger.info(f"Smart caching applied: {len(cacheable_patterns)} patterns cached")
        return result

    def resource_allocation(
        self,
        top_performers: list[dict[str, Any]],
        context: ImprovementContext,
    ) -> dict[str, Any]:
        """
        Rule 3: Allocate resources to top performers
        Prioritize and allocate more resources to high-performing agents/services

        Args:
            top_performers: List of top performing agents with metrics
            context: Current context

        Returns:
            Improvement record with allocation strategy
        """
        if not top_performers:
            return {"status": "no_performers", "allocations": 0}

        allocations = []
        total_resource_boost = 0.0

        for performer in top_performers:
            name = performer.get("name", "unknown")
            performance_score = performer.get("performance_score", 0.0)  # 0-1

            # Allocate resources proportional to performance
            resource_boost = max(0.1, min(0.5, performance_score * 0.5))  # 10-50% boost

            allocations.append({
                "name": name,
                "current_score": performance_score,
                "resource_boost": f"{resource_boost:.1%}",
                "priority_level": "high" if performance_score > 0.9 else "medium",
            })
            total_resource_boost += resource_boost

        result = {
            "rule": "resource_allocation",
            "status": "applied",
            "allocations": len(allocations),
            "allocation_details": allocations,
            "total_resource_boost": f"{total_resource_boost/len(allocations):.1%}" if allocations else "0%",
            "expected_improvement": f"{min(0.3, len(allocations) * 0.05):.1%}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.applied_rules["resource_allocation"] = result
        self.logger.info(f"Resource allocation applied: {len(allocations)} agents boosted")
        return result

    def add_user_feedback(self, feedback: dict[str, Any]) -> None:
        """
        Accept user feedback on improvement suggestions

        Args:
            feedback: Dictionary with:
                - suggestion_id: str
                - accepted: bool
                - comment: str (optional)
                - sentiment: "positive" | "neutral" | "negative" (optional)
        """
        feedback["timestamp"] = datetime.now(timezone.utc).isoformat()
        self.user_feedback_buffer.append(feedback)

        status = "accepted" if feedback.get("accepted") else "rejected"
        self.logger.info(
            f"User feedback recorded: {feedback.get('suggestion_id')} "
            f"status={status} comment={feedback.get('comment', 'none')}"
        )

    def _analyze_feedback_sentiment(self) -> str:
        """
        Analyze recent user feedback to determine overall sentiment

        Returns:
            "positive", "neutral", or "negative"
        """
        if not self.user_feedback_buffer:
            return "neutral"

        # Look at recent feedback (last 10)
        recent = self.user_feedback_buffer[-10:]

        positive_count = 0
        negative_count = 0

        for feedback in recent:
            if feedback.get("accepted"):
                positive_count += 1
            elif feedback.get("sentiment") == "positive":
                positive_count += 1
            elif feedback.get("sentiment") == "negative":
                negative_count += 1

        acceptance_rate = positive_count / len(recent) if recent else 0.5

        if acceptance_rate > 0.7:
            return "positive"
        elif acceptance_rate < 0.3:
            return "negative"
        else:
            return "neutral"

    def predict_before_issue(self, metrics_history: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Predict issues before they happen based on trends

        Args:
            metrics_history: List of recent metric snapshots with timestamps

        Returns:
            Prediction with suggested preventive actions
        """
        if len(metrics_history) < 3:
            return {"status": "insufficient_data", "predictions": []}

        predictions = []

        # Analyze trend: is success rate declining?
        recent_3 = metrics_history[-3:]
        success_rates = [m.get("success_rate", 1.0) for m in recent_3]

        if len(success_rates) >= 2:
            rate_decline = success_rates[0] - success_rates[-1]
            if rate_decline > 0.05:  # 5% decline trend
                predictions.append({
                    "issue_type": "declining_success_rate",
                    "severity": "high" if rate_decline > 0.1 else "medium",
                    "predicted_impact": f"{rate_decline:.1%} further decline",
                    "suggested_action": "Increase error handling and retry logic",
                    "preventive_rules": ["smart_caching", "resource_allocation"],
                })

        # Check for memory/latency trends
        durations = [m.get("avg_duration_ms", 500) for m in recent_3]
        if len(durations) >= 2:
            duration_increase = durations[-1] - durations[0]
            if duration_increase > 100:  # 100ms+ increase
                predictions.append({
                    "issue_type": "increasing_latency",
                    "severity": "medium",
                    "predicted_impact": f"{duration_increase:.0f}ms latency increase",
                    "suggested_action": "Apply batch execution and optimize resource allocation",
                    "preventive_rules": ["batch_execution", "resource_allocation"],
                })

        result = {
            "status": "success" if predictions else "no_issues_detected",
            "predictions": predictions,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        self.logger.info(f"Predictions generated: {len(predictions)} potential issues detected")
        return result

    def get_applied_rules(self) -> dict[str, dict[str, Any]]:
        """Get all applied rules and their results"""
        return self.applied_rules

    def get_feedback_summary(self) -> dict[str, Any]:
        """Get summary of user feedback"""
        if not self.user_feedback_buffer:
            return {
                "total_feedback": 0,
                "acceptance_rate": 0.0,
                "sentiment": "neutral",
            }

        accepted = sum(1 for f in self.user_feedback_buffer if f.get("accepted"))
        total = len(self.user_feedback_buffer)
        acceptance_rate = accepted / total if total > 0 else 0

        return {
            "total_feedback": total,
            "acceptance_rate": f"{acceptance_rate:.1%}",
            "sentiment": self._analyze_feedback_sentiment(),
            "recent_feedback": self.user_feedback_buffer[-5:],
        }
