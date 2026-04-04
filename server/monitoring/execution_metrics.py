"""
Execution Metrics Collection & Analysis
Real-time system performance monitoring
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


@dataclass
class ExecutionMetric:
    """Single execution metric"""
    timestamp: str
    run_id: str
    action: str
    status: str  # success, failure, timeout, error
    duration_seconds: float
    result_size_bytes: int = 0
    error_message: str | None = None
    cache_hit: bool = False
    retry_count: int = 0


class ExecutionMetricsCollector:
    """Collect and aggregate execution metrics"""

    def __init__(self, log_dir: Path | str = "server/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_file = self.log_dir / "execution_metrics.jsonl"
        self.logger = self._build_logger()

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger("jarvis.monitoring.metrics")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not any(
            isinstance(h, logging.FileHandler)
            and Path(h.baseFilename) == self.log_dir / "execution_metrics.log"
            for h in logger.handlers
        ):
            handler = logging.FileHandler(
                self.log_dir / "execution_metrics.log",
                encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(handler)
        return logger

    def record(self, metric: ExecutionMetric) -> None:
        """Record a single execution metric"""
        try:
            with open(self.metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(metric), ensure_ascii=False) + "\n")
            self.logger.info(f"metric_recorded action={metric.action} status={metric.status}")
        except Exception as e:
            self.logger.error(f"Failed to record metric: {e}")

    def record_execution(
        self,
        run_id: str,
        action: str,
        status: str,
        duration_seconds: float,
        error_message: str | None = None,
        result_size_bytes: int = 0,
        cache_hit: bool = False,
        retry_count: int = 0,
    ) -> None:
        """Convenience method to record execution"""
        metric = ExecutionMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            action=action,
            status=status,
            duration_seconds=round(duration_seconds, 3),
            result_size_bytes=result_size_bytes,
            error_message=error_message,
            cache_hit=cache_hit,
            retry_count=retry_count,
        )
        self.record(metric)

    def get_recent_metrics(self, limit: int = 100) -> list[ExecutionMetric]:
        """Get most recent metrics"""
        if not self.metrics_file.exists():
            return []

        metrics = []
        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        metric = ExecutionMetric(**data)
                        metrics.append(metric)
                    except (json.JSONDecodeError, TypeError):
                        pass
        except Exception as e:
            self.logger.error(f"Failed to read metrics: {e}")

        return metrics[-limit:]

    def get_stats(self, time_window_minutes: int = 60) -> dict[str, Any]:
        """Get aggregated statistics for time window"""
        metrics = self.get_recent_metrics(limit=1000)

        # Filter by time window
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        recent = [
            m for m in metrics
            if datetime.fromisoformat(m.timestamp) > cutoff
        ]

        if not recent:
            return {
                "time_window_minutes": time_window_minutes,
                "total_executions": 0,
                "status": "no_data"
            }

        # Calculate statistics
        success = sum(1 for m in recent if m.status == "success")
        failures = sum(1 for m in recent if m.status in ("failure", "error", "timeout"))
        cache_hits = sum(1 for m in recent if m.cache_hit)
        total_duration = sum(m.duration_seconds for m in recent)
        avg_duration = total_duration / len(recent) if recent else 0

        success_rate = (success / len(recent) * 100) if recent else 0
        cache_hit_rate = (cache_hits / len(recent) * 100) if recent else 0

        # Error breakdown
        error_types = {}
        for m in recent:
            if m.error_message:
                error_type = m.error_message.split(":")[0] if ":" in m.error_message else m.error_message
                error_types[error_type] = error_types.get(error_type, 0) + 1

        # Top actions
        action_counts = {}
        for m in recent:
            action_counts[m.action] = action_counts.get(m.action, 0) + 1

        top_actions = sorted(action_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "time_window_minutes": time_window_minutes,
            "total_executions": len(recent),
            "success_count": success,
            "failure_count": failures,
            "success_rate_pct": round(success_rate, 1),
            "cache_hit_count": cache_hits,
            "cache_hit_rate_pct": round(cache_hit_rate, 1),
            "avg_duration_seconds": round(avg_duration, 2),
            "total_duration_seconds": round(total_duration, 1),
            "top_errors": sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:5],
            "top_actions": [{"action": a, "count": c} for a, c in top_actions],
            "throughput_per_minute": round(len(recent) / time_window_minutes, 2),
        }

    def get_action_stats(self, action: str, limit: int = 100) -> dict[str, Any]:
        """Get statistics for a specific action"""
        metrics = self.get_recent_metrics(limit=limit)
        action_metrics = [m for m in metrics if m.action == action]

        if not action_metrics:
            return {"action": action, "status": "no_data"}

        success = sum(1 for m in action_metrics if m.status == "success")
        failures = sum(1 for m in action_metrics if m.status != "success")
        durations = [m.duration_seconds for m in action_metrics]

        return {
            "action": action,
            "total_calls": len(action_metrics),
            "success_count": success,
            "failure_count": failures,
            "success_rate_pct": round(success / len(action_metrics) * 100, 1),
            "min_duration_seconds": round(min(durations), 3),
            "max_duration_seconds": round(max(durations), 3),
            "avg_duration_seconds": round(sum(durations) / len(durations), 3),
            "p50_duration_seconds": round(sorted(durations)[len(durations)//2], 3),
        }


def create_metrics_dashboard(metrics: ExecutionMetricsCollector, limit: int = 10) -> str:
    """Create ASCII dashboard of execution metrics"""
    stats = metrics.get_stats(time_window_minutes=60)
    recent = metrics.get_recent_metrics(limit=limit)

    if not recent:
        return "No execution metrics available"

    dashboard = []
    dashboard.append("=" * 70)
    dashboard.append("EXECUTION METRICS DASHBOARD")
    dashboard.append("=" * 70)
    dashboard.append("")

    # Summary stats
    dashboard.append("SUMMARY (Last 60 minutes)")
    dashboard.append("-" * 70)
    dashboard.append(f"Total Executions: {stats.get('total_executions', 0)}")
    dashboard.append(f"Success Rate: {stats.get('success_rate_pct', 0)}%")
    dashboard.append(f"Cache Hit Rate: {stats.get('cache_hit_rate_pct', 0)}%")
    dashboard.append(f"Avg Duration: {stats.get('avg_duration_seconds', 0)}s")
    dashboard.append(f"Throughput: {stats.get('throughput_per_minute', 0)} calls/min")
    dashboard.append("")

    # Recent executions
    dashboard.append("RECENT EXECUTIONS (Last 10)")
    dashboard.append("-" * 70)
    dashboard.append(f"{'Time':<20} {'Action':<20} {'Status':<10} {'Duration':<10}")
    dashboard.append("-" * 70)

    for metric in reversed(recent[-10:]):
        time_str = metric.timestamp.split("T")[1][:8]
        status_char = "+" if metric.status == "success" else "-"
        dashboard.append(
            f"{time_str:<20} {metric.action:<20} {status_char} {metric.status:<8} "
            f"{metric.duration_seconds:<10.2f}s"
        )

    dashboard.append("=" * 70)
    return "\n".join(dashboard)
