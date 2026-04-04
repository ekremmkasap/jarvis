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
        """
        try:
            # Analyze patterns
            analysis = await self.learning.analyze_patterns()

            if not analysis or not analysis.get("patterns"):
                return {"status": "no_patterns", "message": "Not enough data for analysis"}

            # Get suggestions
            suggestions = await self.learning.suggest_improvements()

            if not suggestions:
                return {"status": "no_suggestions", "message": "No improvements suggested"}

            # Apply top suggestion
            top_suggestion = suggestions[0]
            result = await self.learning.apply_improvement(top_suggestion)

            self.logger.info(
                f"Applied improvement: {top_suggestion.get('type')} "
                f"with expected gain: {top_suggestion.get('expected_improvement')}"
            )

            return {
                "status": "success",
                "improvement_applied": top_suggestion.get("type"),
                "expected_gain": top_suggestion.get("expected_improvement"),
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

    def get_learning_status(self) -> dict[str, Any]:
        """Get current learning system status"""
        stats = self.metrics.get_stats()
        cache_stats = getattr(self, '_cache_stats', {})

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
                "last_analysis": None,
                "improvements_applied": 0,
            },
        }
