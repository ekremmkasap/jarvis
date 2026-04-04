#!/usr/bin/env python3
"""
TELEGRAM INTELLIGENCE - Smart Alerts & Command Processing
Caleb-3: Alert rules, command handlers, metric reporting
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from enum import Enum


class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class Alert:
    """Alert definition"""
    timestamp: str
    rule_name: str
    level: str  # AlertLevel name
    message: str
    metric_name: str
    metric_value: float
    threshold: float
    context: Dict[str, Any] = None


class RateLimiter:
    """Simple rate limiter for alerts"""

    def __init__(self, max_alerts_per_minute: int = 1):
        self.max_per_minute = max_alerts_per_minute
        self.rule_timestamps: Dict[str, List[float]] = {}

    def should_alert(self, rule_name: str) -> bool:
        """Check if rule should trigger alert (rate limiting)"""
        now = time.time()
        if rule_name not in self.rule_timestamps:
            self.rule_timestamps[rule_name] = []

        # Remove timestamps older than 1 minute
        one_minute_ago = now - 60
        self.rule_timestamps[rule_name] = [
            ts for ts in self.rule_timestamps[rule_name]
            if ts > one_minute_ago
        ]

        # Check if we can alert
        if len(self.rule_timestamps[rule_name]) < self.max_per_minute:
            self.rule_timestamps[rule_name].append(now)
            return True
        return False


class TelegramIntelligence:
    """Telegram intelligence system with alerts and command processing"""

    def __init__(self, log_dir: Path | str = "server/logs/telegram"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = self._build_logger()
        self.rate_limiter = RateLimiter(max_alerts_per_minute=1)
        self.alerts_file = self.log_dir / "alerts.jsonl"
        self.commands_file = self.log_dir / "commands.jsonl"

    def _build_logger(self) -> logging.Logger:
        """Build logger for telegram intelligence"""
        logger = logging.getLogger("jarvis.telegram.intelligence")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        # Remove existing handlers
        logger.handlers = []

        # File handler
        fh = logging.FileHandler(
            self.log_dir / "intelligence.log",
            encoding="utf-8"
        )
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(fh)

        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(ch)

        return logger

    # ─────────────────────── ALERT RULES ──────────────────────────

    def check_error_threshold(
        self,
        error_rate: float,
        threshold: float = 0.05
    ) -> Optional[Alert]:
        """Check if error rate exceeds threshold (5% by default)"""
        rule_name = "error_threshold"

        if error_rate > threshold:
            if not self.rate_limiter.should_alert(rule_name):
                self.logger.debug(f"Rate limited: {rule_name}")
                return None

            level = AlertLevel.CRITICAL if error_rate > 0.15 else AlertLevel.ERROR
            alert = Alert(
                timestamp=datetime.now(timezone.utc).isoformat(),
                rule_name=rule_name,
                level=level.value,
                message=f"Error rate {error_rate*100:.1f}% exceeds threshold {threshold*100:.1f}%",
                metric_name="error_rate",
                metric_value=error_rate,
                threshold=threshold,
                context={"severity": "high"}
            )
            self._log_alert(alert)
            return alert
        return None

    def check_latency_spike(
        self,
        current_latency: float,
        baseline_latency: float,
        spike_factor: float = 2.5
    ) -> Optional[Alert]:
        """Check if latency spikes above baseline"""
        rule_name = "latency_spike"

        if current_latency > baseline_latency * spike_factor:
            if not self.rate_limiter.should_alert(rule_name):
                self.logger.debug(f"Rate limited: {rule_name}")
                return None

            level = (
                AlertLevel.CRITICAL if current_latency > baseline_latency * 5
                else AlertLevel.WARNING
            )
            alert = Alert(
                timestamp=datetime.now(timezone.utc).isoformat(),
                rule_name=rule_name,
                level=level.value,
                message=f"Latency spike: {current_latency:.2f}s (baseline: {baseline_latency:.2f}s)",
                metric_name="latency_ms",
                metric_value=current_latency * 1000,
                threshold=baseline_latency * spike_factor * 1000,
                context={
                    "current": current_latency,
                    "baseline": baseline_latency,
                    "spike_factor": spike_factor
                }
            )
            self._log_alert(alert)
            return alert
        return None

    def check_learning_event(
        self,
        improvement_pct: float,
        min_improvement: float = 0.01
    ) -> Optional[Alert]:
        """Check if learning event occurred (improvement > threshold)"""
        rule_name = "learning_event"

        if improvement_pct > min_improvement:
            if not self.rate_limiter.should_alert(rule_name):
                self.logger.debug(f"Rate limited: {rule_name}")
                return None

            alert = Alert(
                timestamp=datetime.now(timezone.utc).isoformat(),
                rule_name=rule_name,
                level=AlertLevel.INFO.value,
                message=f"Learning milestone: {improvement_pct*100:.2f}% improvement detected",
                metric_name="improvement_pct",
                metric_value=improvement_pct,
                threshold=min_improvement,
                context={"learning_event": True}
            )
            self._log_alert(alert)
            return alert
        return None

    def _log_alert(self, alert: Alert) -> None:
        """Log alert to file and logger"""
        try:
            with open(self.alerts_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(alert), ensure_ascii=False) + "\n")
            self.logger.info(
                f"ALERT [{alert.level}] {alert.rule_name}: {alert.message}"
            )
        except Exception as e:
            self.logger.error(f"Failed to log alert: {e}")

    # ─────────────────────── COMMAND HANDLERS ──────────────────────

    def format_health_message(self, metrics: Dict[str, Any]) -> str:
        """Format /health command response"""
        status = metrics.get("status", "unknown")
        uptime = metrics.get("uptime_seconds", 0)
        errors = metrics.get("error_count", 0)
        requests = metrics.get("total_requests", 0)

        uptime_hours = uptime / 3600
        error_rate = (errors / requests * 100) if requests > 0 else 0

        msg = f"""
*System Health Status*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: `{status}`
Uptime: `{uptime_hours:.1f}h`
Total Requests: `{requests}`
Errors: `{errors}` ({error_rate:.1f}%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return msg.strip()

    def format_metrics_message(self, metrics: Dict[str, Any]) -> str:
        """Format /metrics command response"""
        avg_latency = metrics.get("avg_latency_ms", 0)
        p95_latency = metrics.get("p95_latency_ms", 0)
        cache_hit_rate = metrics.get("cache_hit_rate", 0)
        total_executions = metrics.get("total_executions", 0)

        msg = f"""
*Execution Metrics (Last 1H)*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Executions: `{total_executions}`
Avg Latency: `{avg_latency:.2f}ms`
P95 Latency: `{p95_latency:.2f}ms`
Cache Hit Rate: `{cache_hit_rate*100:.1f}%`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return msg.strip()

    def format_improvements_message(self, improvements: List[Dict[str, Any]]) -> str:
        """Format /improve command response"""
        if not improvements:
            return "*No improvement suggestions at this time.*"

        msg = "*Suggested Improvements*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        for i, imp in enumerate(improvements[:5], 1):
            title = imp.get("title", "Unknown")
            impact = imp.get("impact_score", 0)
            msg += f"{i}. {title} (Impact: `{impact:.1f}`)\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        return msg

    def format_rollback_message(self, result: Dict[str, Any]) -> str:
        """Format /rollback command response"""
        success = result.get("success", False)
        revision = result.get("revision", "?")
        message = result.get("message", "Unknown")

        if success:
            return f"✅ *Rollback Successful*\nReverted to: `{revision}`\nMessage: _{message}_"
        else:
            return f"❌ *Rollback Failed*\nError: {message}"

    def format_cache_message(self, cache_stats: Dict[str, Any]) -> str:
        """Format /cache command response"""
        hits = cache_stats.get("hits", 0)
        misses = cache_stats.get("misses", 0)
        size_mb = cache_stats.get("size_mb", 0)
        total = hits + misses

        hit_rate = (hits / total * 100) if total > 0 else 0

        msg = f"""
*Cache Statistics*
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Hits: `{hits}`
Misses: `{misses}`
Hit Rate: `{hit_rate:.1f}%`
Size: `{size_mb:.2f} MB`
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return msg.strip()

    def log_command(
        self,
        command: str,
        chat_id: int,
        status: str,
        response_length: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log command execution"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "command": command,
            "chat_id": chat_id,
            "status": status,
            "response_length": response_length,
            "metadata": metadata or {}
        }
        try:
            with open(self.commands_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log command: {e}")

    def get_recent_alerts(self, limit: int = 10) -> List[Alert]:
        """Get recent alerts"""
        if not self.alerts_file.exists():
            return []

        alerts = []
        try:
            with open(self.alerts_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        alerts.append(Alert(**data))
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"Failed to read alerts: {e}")

        return alerts[-limit:]

    def get_alert_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get alert summary for given time window"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        alerts = self.get_recent_alerts(limit=1000)

        summary = {
            "total": 0,
            "by_level": {level.value: 0 for level in AlertLevel},
            "by_rule": {},
            "recent_alerts": []
        }

        for alert in alerts:
            alert_time = datetime.fromisoformat(alert.timestamp)
            if alert_time < cutoff:
                continue

            summary["total"] += 1
            summary["by_level"][alert.level] += 1
            summary["by_rule"][alert.rule_name] = summary["by_rule"].get(alert.rule_name, 0) + 1
            summary["recent_alerts"].append({
                "rule": alert.rule_name,
                "level": alert.level,
                "message": alert.message
            })

        return summary

    def get_command_summary(self, time_window_minutes: int = 60) -> Dict[str, Any]:
        """Get command execution summary"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
        commands = []

        if not self.commands_file.exists():
            return {"total": 0, "by_command": {}, "success_rate": 0.0}

        try:
            with open(self.commands_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        cmd_time = datetime.fromisoformat(data["timestamp"])
                        if cmd_time >= cutoff:
                            commands.append(data)
                    except Exception:
                        continue
        except Exception as e:
            self.logger.error(f"Failed to read commands: {e}")

        by_cmd = {}
        success_count = 0
        for cmd in commands:
            cmd_name = cmd.get("command", "unknown")
            by_cmd[cmd_name] = by_cmd.get(cmd_name, 0) + 1
            if cmd.get("status") == "success":
                success_count += 1

        total = len(commands)
        success_rate = (success_count / total) if total > 0 else 0

        return {
            "total": total,
            "by_command": by_cmd,
            "success_rate": success_rate
        }
