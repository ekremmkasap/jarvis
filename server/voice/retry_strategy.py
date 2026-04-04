#!/usr/bin/env python3
"""Retry strategy with exponential backoff for API resilience."""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 0.5  # seconds
    max_delay: float = 10.0  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True
    log_path: Optional[Path] = None


class RetryStrategy(Generic[T]):
    """Retry with exponential backoff and jitter."""

    def __init__(self, config: RetryConfig, logger: Optional[logging.Logger] = None) -> None:
        self.config = config
        self.logger = logger or self._build_logger()
        self.attempt_count = 0

    def execute(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute function with retry strategy."""
        self.attempt_count = 0
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_attempts):
            self.attempt_count = attempt + 1
            try:
                self.logger.debug(f"Attempt {self.attempt_count}/{self.config.max_attempts}")
                return func(*args, **kwargs)
            except Exception as exc:
                last_exception = exc
                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    self.logger.warning(f"Attempt {self.attempt_count} failed: {exc}. Retrying in {delay:.2f}s")
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.config.max_attempts} attempts failed")

        raise last_exception or RuntimeError("Retry strategy failed")

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = self.config.initial_delay * (self.config.backoff_multiplier ** attempt)
        delay = min(delay, self.config.max_delay)

        if self.config.jitter:
            delay = delay * (0.5 + random.random())

        return delay

    def _build_logger(self) -> logging.Logger:
        """Build dedicated logger for retry strategy."""
        log_dir = self.config.log_path or Path("server") / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "retry_strategy.log"

        logger_name = f"jarvis.retry_strategy.{id(self)}"
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        for handler in logger.handlers:
            if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path.resolve():
                return logger

        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
        return logger
