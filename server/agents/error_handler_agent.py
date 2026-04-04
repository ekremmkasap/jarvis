from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class RecoveryDecision(str, Enum):
    RETRY = "RETRY"
    REPLAN = "REPLAN"
    SKIP = "SKIP"


@dataclass
class RecoveryResult:
    ok: bool
    decision: RecoveryDecision
    step: dict[str, Any]
    output: Any = None
    error: str | None = None
    retry_attempts: int = 0
    replan_attempts: int = 0
    recovery_path: list[str] = field(default_factory=list)


@dataclass
class RecoveryStats:
    total_failures: int = 0
    recovered: int = 0
    skipped: int = 0


class ErrorHandlerAgent:
    """Handles execution failures with deterministic RETRY/REPLAN/SKIP logic."""

    _TRANSIENT_KEYWORDS = ("timeout", "tempor", "network", "rate limit", "connection reset")
    _REPLAN_KEYWORDS = ("invalid", "unknown action", "unsupported", "not found", "missing")

    def __init__(
        self,
        *,
        max_retries: int = 1,
        max_replan_attempts: int = 2,
        log_dir: Path | None = None,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.max_retries = max(0, int(max_retries))
        self.max_replan_attempts = max(0, int(max_replan_attempts))
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.stats = RecoveryStats()
        self.logger = self._build_logger(log_dir=log_dir)

    def decide_action(
        self,
        error: Exception | str,
        *,
        retry_attempts: int,
        replan_attempts: int,
    ) -> RecoveryDecision:
        text = str(error).lower()
        if retry_attempts < self.max_retries and any(token in text for token in self._TRANSIENT_KEYWORDS):
            return RecoveryDecision.RETRY
        if replan_attempts < self.max_replan_attempts and any(token in text for token in self._REPLAN_KEYWORDS):
            return RecoveryDecision.REPLAN
        if retry_attempts < self.max_retries:
            return RecoveryDecision.RETRY
        if replan_attempts < self.max_replan_attempts:
            return RecoveryDecision.REPLAN
        return RecoveryDecision.SKIP

    def execute_with_recovery(
        self,
        *,
        step: dict[str, Any],
        error: Exception | str,
        execute_step: Callable[[dict[str, Any]], Any],
        replan_step: Callable[[dict[str, Any], Exception | str, int], dict[str, Any]] | None = None,
    ) -> RecoveryResult:
        self.stats.total_failures += 1
        retry_attempts = 0
        replan_attempts = 0
        recovery_path: list[str] = []
        active_step = dict(step)
        active_error: Exception | str = error

        self._log_event("failure_received", active_step, str(active_error))

        while True:
            decision = self.decide_action(
                active_error,
                retry_attempts=retry_attempts,
                replan_attempts=replan_attempts,
            )
            recovery_path.append(decision.value)
            self._log_event("decision", active_step, str(active_error), decision.value)

            if decision is RecoveryDecision.RETRY:
                retry_attempts += 1
                try:
                    output = execute_step(active_step)
                    self.stats.recovered += 1
                    self._log_event("recovered", active_step, "retry success", decision.value)
                    return RecoveryResult(
                        ok=True,
                        decision=decision,
                        step=active_step,
                        output=output,
                        retry_attempts=retry_attempts,
                        replan_attempts=replan_attempts,
                        recovery_path=recovery_path,
                    )
                except Exception as exc:
                    active_error = exc
                    self._log_event("retry_failed", active_step, str(exc), decision.value)
                    continue

            if decision is RecoveryDecision.REPLAN:
                if replan_step is None:
                    self.stats.skipped += 1
                    self._log_event("skip_no_replanner", active_step, str(active_error), decision.value)
                    return RecoveryResult(
                        ok=False,
                        decision=RecoveryDecision.SKIP,
                        step=active_step,
                        error="replan_step is required for REPLAN decision",
                        retry_attempts=retry_attempts,
                        replan_attempts=replan_attempts,
                        recovery_path=recovery_path,
                    )
                replan_attempts += 1
                active_step = replan_step(active_step, active_error, replan_attempts)
                self._log_event("replanned", active_step, str(active_error), decision.value)
                try:
                    output = execute_step(active_step)
                    self.stats.recovered += 1
                    self._log_event("recovered", active_step, "replan success", decision.value)
                    return RecoveryResult(
                        ok=True,
                        decision=decision,
                        step=active_step,
                        output=output,
                        retry_attempts=retry_attempts,
                        replan_attempts=replan_attempts,
                        recovery_path=recovery_path,
                    )
                except Exception as exc:
                    active_error = exc
                    self._log_event("replan_failed", active_step, str(exc), decision.value)
                    continue

            self.stats.skipped += 1
            self._log_event("skipped", active_step, str(active_error), decision.value)
            return RecoveryResult(
                ok=False,
                decision=RecoveryDecision.SKIP,
                step=active_step,
                error=str(active_error),
                retry_attempts=retry_attempts,
                replan_attempts=replan_attempts,
                recovery_path=recovery_path,
            )

    def _build_logger(self, *, log_dir: Path | None) -> logging.Logger:
        resolved_dir = log_dir or (Path(__file__).resolve().parents[1] / "logs")
        resolved_dir.mkdir(parents=True, exist_ok=True)
        log_path = resolved_dir / "error_handler_agent.log"
        logger = logging.getLogger(f"jarvis.error_handler.{id(self)}")
        logger.setLevel(logging.INFO)
        logger.propagate = False
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    def close(self) -> None:
        handlers = list(self.logger.handlers)
        for handler in handlers:
            handler.flush()
            handler.close()
            self.logger.removeHandler(handler)

    def _log_event(
        self,
        event: str,
        step: dict[str, Any],
        error: str,
        decision: str | None = None,
    ) -> None:
        self.logger.info(
            "ts=%s event=%s decision=%s step=%s error=%s",
            self.now_fn().isoformat(),
            event,
            decision or "-",
            step.get("name", "unknown"),
            error,
        )
