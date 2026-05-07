"""
Health Check Module
System status monitoring and diagnostics
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HealthStatus:
    """System health status"""
    timestamp: str
    status: str  # healthy, degraded, unhealthy
    components: dict[str, bool]
    error_message: str | None = None
    metrics: dict[str, Any] | None = None


class HealthChecker:
    """Monitor system health"""

    def __init__(self, log_dir: Path | str = "server/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = self._build_logger()

    def _build_logger(self) -> logging.Logger:
        logger = logging.getLogger("jarvis.monitoring.health")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        if not any(
            isinstance(h, logging.FileHandler)
            and Path(h.baseFilename) == self.log_dir / "health_check.log"
            for h in logger.handlers
        ):
            handler = logging.FileHandler(
                self.log_dir / "health_check.log",
                encoding="utf-8"
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            )
            logger.addHandler(handler)
        return logger

    def check_components(self) -> dict[str, bool]:
        """Check all system components"""
        components = {}

        # Check log directory
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            components["logs_writable"] = True
        except Exception as e:
            self.logger.error(f"Log directory check failed: {e}")
            components["logs_writable"] = False

        # Check Gemini availability (optional)
        try:
            import google.genai
            components["gemini_available"] = True
        except Exception:
            components["gemini_available"] = False

        # Check required files
        required_files = [
            Path("server/agents/week1_pipeline.py"),
            Path("server/voice/voice_layer.py"),
            Path("server/bridge.py"),
        ]

        components["required_files"] = all(f.exists() for f in required_files)

        # Check metrics file
        try:
            metrics_file = self.log_dir / "execution_metrics.jsonl"
            components["metrics_file_exists"] = metrics_file.exists()
        except Exception:
            components["metrics_file_exists"] = False

        return components

    def get_status(self, metrics_data: dict[str, Any] | None = None) -> HealthStatus:
        """Get overall system health status"""
        components = self.check_components()
        error_message = None

        # Determine overall status
        if all(components.values()):
            status = "healthy"
        elif sum(1 for v in components.values() if v) >= len(components) * 0.8:
            status = "degraded"
        else:
            status = "unhealthy"
            error_message = "Multiple components failing"

        health_status = HealthStatus(
            timestamp=datetime.now(timezone.utc).isoformat(),
            status=status,
            components=components,
            error_message=error_message,
            metrics=metrics_data,
        )

        if status != "healthy":
            self.logger.warning(f"Health check: {status} - {components}")
        else:
            self.logger.info("Health check: healthy")

        return health_status

    def to_json(self, health_status: HealthStatus) -> str:
        """Convert health status to JSON"""
        return json.dumps(asdict(health_status), ensure_ascii=False, indent=2)

    def get_health_endpoint_response(
        self,
        include_metrics: bool = False,
        metrics_data: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], int]:
        """
        Get response for /health endpoint

        Returns:
            (response_body, http_status_code)
        """
        health_status = self.get_status(metrics_data if include_metrics else None)

        response = {
            "status": health_status.status,
            "timestamp": health_status.timestamp,
            "components": health_status.components,
        }

        if include_metrics and health_status.metrics:
            response["metrics"] = health_status.metrics

        # HTTP status code
        if health_status.status == "healthy":
            status_code = 200
        elif health_status.status == "degraded":
            status_code = 503  # Service Unavailable
        else:
            status_code = 503

        return response, status_code


def format_health_report(health_status: HealthStatus) -> str:
    """Format health status as human-readable report"""
    lines = []
    lines.append("=" * 60)
    lines.append("SYSTEM HEALTH REPORT")
    lines.append("=" * 60)
    lines.append(f"Status: {health_status.status.upper()}")
    lines.append(f"Timestamp: {health_status.timestamp}")
    lines.append("")
    lines.append("COMPONENTS:")
    lines.append("-" * 60)

    for component, is_healthy in health_status.components.items():
        status_char = "[OK]" if is_healthy else "[ERR]"
        lines.append(f"{status_char} {component}")

    if health_status.error_message:
        lines.append("")
        lines.append("ERROR:")
        lines.append(f"  {health_status.error_message}")

    if health_status.metrics:
        lines.append("")
        lines.append("METRICS:")
        lines.append("-" * 60)
        for key, value in health_status.metrics.items():
            lines.append(f"  {key}: {value}")

    lines.append("=" * 60)
    return "\n".join(lines)
