#!/usr/bin/env python3
"""Circuit breaker pattern implementation for API resilience."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker state transitions."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""

    failure_threshold: int = 3
    recovery_timeout: int = 300  # 5 minutes
    half_open_attempts: int = 1
    log_path: Optional[Path] = None


class CircuitBreaker(Generic[T]):
    """
    Circuit breaker for API calls with automatic reset.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests blocked with fallback
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(self, config: CircuitBreakerConfig, logger: Optional[logging.Logger] = None) -> None:
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.logger = logger or self._build_logger()

    def call(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                self.logger.warning("Circuit breaker OPEN - request blocked")
                raise CircuitBreakerOpenError("Circuit breaker is OPEN - service temporarily unavailable")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful request."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.half_open_attempts:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.logger.info("Circuit breaker CLOSED - service recovered")
        else:
            self.failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        self.logger.warning(f"API failure {self.failure_count}/{self.config.failure_threshold}")

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.error("Circuit breaker OPEN - too many failures")

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return False
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.logger.info("Circuit breaker manually RESET")

    def _build_logger(self) -> logging.Logger:
        """Build dedicated logger for circuit breaker."""
        log_dir = self.config.log_path or Path("server") / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "circuit_breaker.log"

        logger_name = f"jarvis.circuit_breaker.{id(self)}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)
        logger.propagate = False

        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path.resolve():
                return logger

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
        return logger


class CircuitBreakerOpenError(RuntimeError):
    """Raised when circuit breaker is open."""

    pass
