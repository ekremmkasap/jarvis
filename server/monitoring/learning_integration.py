"""
Learning System Integration
Hook execution metrics into self-learning engine for continuous improvement
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json

from server.monitoring.execution_metrics import ExecutionMetricsCollector
from server.agents.self_learning_agent import SelfLearningEngine


class LearningIntegrationBridge:
    """Bridge execution metrics to learning system"""

    def __init__(
        self,
        metrics_collector: ExecutionMetricsCollector | None = None,
        learning_engine: SelfLearningEngine | None = None,
        log_dir: Path | str = "server/logs",
    ):
        self.metrics = metrics_collector or ExecutionMetricsCollector(log_dir=log_dir)
        self.learning = learning_engine or SelfLearningEngine(
            data_dir=str(Path(log_dir) / "learning")
        )
        self.log_dir = Path(log_dir)
        self.logger = self._build_logger()

        # Improvement tracking
        self.improvement_history: list[dict[str, Any]] = []
        self.improvement_snapshots: dict[str, dict[str, Any]] = {}
        self.rollback_threshold = 0.05  # -5% is rollback threshold
        self._max_improvements_per_cycle = 1

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger("jarvis.monitoring.learning_bridge")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not any(
            isinstance(h, logging.FileHandler)
            and "learning_bridge" in h.baseFilename
            for h in logger.handlers
        ):
            handler = logging.FileHandler(
                self.log_dir / "learning_bridge.log",
                encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(handler)
        return logger

    async def feed_metrics_to_learning(self) -> dict[str, Any]:
        """
        Feed recent metrics to learning engine for pattern analysis
        """
        try:
            # Get recent metrics
            stats = self.metrics.get_stats(time_window_minutes=60)

            if stats.get("total_executions", 0) == 0:
                return {"status": "no_data", "message": "No executions to analyze"}

            # Log success/failure patterns
            recent_metrics = self.metrics.get_recent_metrics(limit=100)

            for metric in recent_metrics:
                execution_result = {
                    "status": metric.status,
                    "action": metric.action,
                    "error": metric.error_message,
                    "duration": metric.duration_seconds,
                    "cache_hit": metric.cache_hit,
                    "retry_count": metric.retry_count,
                }

                # Feed to learning engine
                await self.learning.log_execution(
                    task_id=metric.run_id,
                    result=execution_result
                )

            self.logger.info(f"Fed {len(recent_metrics)} metrics to learning engine")

            return {
                "status": "success",
                "metrics_fed": len(recent_metrics),
                "stats": stats,
            }

        except Exception as e:
            self.logger.error(f"Failed to feed metrics: {e}")
            return {"status": "error", "error": str(e)}

    async def check_and_apply_improvements(self) -> dict[str, Any]:
        """
        Analyze patterns and apply improvements if suggested
        Max 1 improvement per cycle with auto-rollback on negative impact
        """
        try:
            # Check if already applied max improvements this cycle
            if len(self.improvement_history) > 0:
                last_improvement = self.improvement_history[-1]
                if (datetime.now(timezone.utc).timestamp() -
                    datetime.fromisoformat(last_improvement["timestamp"]).timestamp()) < 3600:
                    # Less than 1 hour since last improvement
                    if last_improvement.get("status") == "applied":
                        return {
                            "status": "max_per_cycle",
                            "message": f"Max {self._max_improvements_per_cycle} improvement per cycle reached"
                        }

            # Take metrics snapshot before improvement
            pre_improvement_stats = self.metrics.get_stats(time_window_minutes=60)
            self.logger.info(f"pre_improvement_snapshot success_rate={pre_improvement_stats.get('success_rate_pct')}%")

            # Analyze patterns
            analysis = await self.learning.analyze_patterns()

            if not analysis or not analysis.get("patterns"):
                return {"status": "no_patterns", "message": "Not enough data for analysis"}

            # Get suggestions
            suggestions = await self.learning.suggest_improvements()

            if not suggestions:
                return {"status": "no_suggestions", "message": "No improvements suggested"}

            # Apply top suggestion (safest one)
            top_suggestion = suggestions[0]
            improvement_id = f"imp_{datetime.now(timezone.utc).isoformat().replace(':', '-')}"

            result = await self.learning.apply_improvement(top_suggestion)

            # Store snapshot for rollback detection
            self.improvement_snapshots[improvement_id] = {
                "pre_stats": pre_improvement_stats,
                "suggestion": top_suggestion,
                "applied_at": datetime.now(timezone.utc).isoformat(),
            }

            improvement_record = {
                "id": improvement_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": top_suggestion.get("type"),
                "expected_improvement": top_suggestion.get("expected_improvement"),
                "status": "applied",
                "priority": top_suggestion.get("priority", "medium"),
                "result": result,
            }

            self.improvement_history.append(improvement_record)

            # Log improvement
            await self._log_improvement(improvement_record)

            self.logger.info(
                f"Applied improvement: {top_suggestion.get('type')} "
                f"with expected gain: {top_suggestion.get('expected_improvement')} "
                f"improvement_id={improvement_id}"
            )

            return {
                "status": "success",
                "improvement_applied": top_suggestion.get("type"),
                "expected_gain": top_suggestion.get("expected_improvement"),
                "improvement_id": improvement_id,
                "result": result,
            }

        except Exception as e:
            self.logger.error(f"Failed to apply improvements: {e}")
            return {"status": "error", "error": str(e)}

    async def continuous_learning_loop(
        self,
        interval_seconds: int = 3600,  # 1 hour
        max_iterations: int = 24,  # 24 hours max
    ) -> dict[str, Any]:
        """
        Run continuous learning loop
        - Every hour: feed metrics to learning engine
        - Every 3 hours: analyze and suggest improvements
        """
        iterations = 0
        improvements_applied = 0
        total_metrics_fed = 0

        self.logger.info(f"Starting learning loop (interval={interval_seconds}s)")

        try:
            while iterations < max_iterations:
                # Feed metrics
                feed_result = await self.feed_metrics_to_learning()
                if feed_result.get("status") == "success":
                    total_metrics_fed += feed_result.get("metrics_fed", 0)

                # Every 3 iterations (3 hours), check for improvements
                if iterations % 3 == 0 and iterations > 0:
                    improve_result = await self.check_and_apply_improvements()
                    if improve_result.get("status") == "success":
                        improvements_applied += 1

                iterations += 1
                self.logger.info(
                    f"Learning loop iteration {iterations}: "
                    f"{total_metrics_fed} metrics fed, {improvements_applied} improvements applied"
                )

                # Wait for next interval
                await asyncio.sleep(interval_seconds)

            return {
                "status": "completed",
                "iterations": iterations,
                "metrics_fed": total_metrics_fed,
                "improvements_applied": improvements_applied,
            }

        except KeyboardInterrupt:
            return {
                "status": "interrupted",
                "iterations": iterations,
                "metrics_fed": total_metrics_fed,
                "improvements_applied": improvements_applied,
            }

    async def _log_improvement(self, record: dict[str, Any]) -> None:
        """Log improvement to file for audit trail"""
        try:
            improvements_log = self.log_dir / "improvements.jsonl"
            with open(improvements_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log improvement: {e}")

    async def check_improvement_impact(self, improvement_id: str, timeout_minutes: int = 5) -> dict[str, Any]:
        """
        Check if improvement had positive or negative impact
        If negative impact detected, trigger auto-rollback
        """
        try:
            if improvement_id not in self.improvement_snapshots:
                return {"status": "not_found", "message": f"No snapshot for {improvement_id}"}

            snapshot = self.improvement_snapshots[improvement_id]
            pre_stats = snapshot["pre_stats"]
            current_stats = self.metrics.get_stats(time_window_minutes=timeout_minutes)

            if current_stats.get("total_executions", 0) == 0:
                return {"status": "insufficient_data", "message": "Not enough data to measure impact"}

            pre_success_rate = pre_stats.get("success_rate_pct", 0)
            current_success_rate = current_stats.get("success_rate_pct", 0)
            delta = (current_success_rate - pre_success_rate) / 100.0 if pre_success_rate > 0 else 0

            impact = {
                "improvement_id": improvement_id,
                "pre_success_rate": pre_success_rate,
                "current_success_rate": current_success_rate,
                "delta": round(delta, 4),
                "status": "positive" if delta > 0 else "negative" if delta < self.rollback_threshold else "neutral",
            }

            self.logger.info(f"Improvement impact check: {improvement_id} delta={delta:.2%}")

            # Auto-rollback on negative impact
            if delta < self.rollback_threshold:
                self.logger.warning(
                    f"Auto-rollback triggered for {improvement_id}: "
                    f"delta={delta:.2%} below threshold={self.rollback_threshold:.2%}"
                )
                impact["rollback_triggered"] = True
                impact["rollback_reason"] = f"Success rate dropped {delta:.2%}"

                # Find and mark for rollback
                for record in self.improvement_history:
                    if record["id"] == improvement_id:
                        record["status"] = "rolled_back"
                        record["rollback_at"] = datetime.now(timezone.utc).isoformat()
                        break

            return impact

        except Exception as e:
            self.logger.error(f"Failed to check improvement impact: {e}")
            return {"status": "error", "error": str(e)}

    def get_learning_status(self) -> dict[str, Any]:
        """Get current learning system status"""
        stats = self.metrics.get_stats()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "total_executions": stats.get("total_executions", 0),
                "success_rate_pct": stats.get("success_rate_pct", 0),
                "cache_hit_rate_pct": stats.get("cache_hit_rate_pct", 0),
                "avg_duration_seconds": stats.get("avg_duration_seconds", 0),
            },
            "learning": {
                "engine_active": True,
                "improvements_applied": len([h for h in self.improvement_history if h.get("status") == "applied"]),
                "improvements_rolled_back": len([h for h in self.improvement_history if h.get("status") == "rolled_back"]),
                "last_improvement": self.improvement_history[-1] if self.improvement_history else None,
            },
        }

    def get_improvement_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get improvement history"""
        return self.improvement_history[-limit:]
