from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from server.agents.error_handler_agent import ErrorHandlerAgent, RecoveryResult
from server.agents.executor_agent import ExecutorAgent
from server.agents.task_planner_agent import PlanResult, TaskPlannerAgent
from server.agents.tool_registry import ToolRegistry
from server.monitoring.execution_metrics import ExecutionMetricsCollector
from server.monitoring.learning_integration import LearningIntegrationBridge


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "week1_pipeline.log"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger("jarvis.week1.pipeline")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == LOG_FILE for handler in logger.handlers):
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(file_handler)
    return logger


def _route_task_handler(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from server.services.tool_router import route_task
    except Exception:
        description = str(payload.get("description") or payload.get("goal") or "")
        return {"tool": "jarvis", "label": "Jarvis", "reason": description[:160]}
    description = str(payload.get("description") or payload.get("goal") or "")
    return route_task(description)


def _report_handler(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from server.services.tool_executor import build_tool_execution_report
    except Exception:
        description = str(payload.get("description") or payload.get("goal") or "")
        return {"report": f"fallback-report:{description[:120]}"}
    description = str(payload.get("description") or payload.get("goal") or "")
    report = build_tool_execution_report(description, task_type=str(payload.get("action") or "summary"))
    return {"report": report}


def _safe_summary_handler(payload: dict[str, Any]) -> dict[str, Any]:
    description = str(payload.get("description") or payload.get("goal") or "").strip()
    return {"summary": description[:200] or "No-op summary."}


def build_week1_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("analyze", _route_task_handler)
    registry.register("design", _report_handler)
    registry.register("implement", _report_handler)
    registry.register("test", _report_handler)
    registry.register("review", _safe_summary_handler)
    registry.register("document", _safe_summary_handler)
    registry.register("verify", _safe_summary_handler)
    return registry


class Week1Pipeline:
    def __init__(
        self,
        *,
        planner: TaskPlannerAgent | None = None,
        executor: ExecutorAgent | None = None,
        error_handler: ErrorHandlerAgent | None = None,
        tool_registry: ToolRegistry | None = None,
        logger: logging.Logger | None = None,
        metrics_collector: ExecutionMetricsCollector | None = None,
        learning_bridge: LearningIntegrationBridge | None = None,
    ) -> None:
        self.tool_registry = tool_registry or build_week1_tool_registry()
        self.planner = planner or TaskPlannerAgent()
        self.executor = executor or ExecutorAgent(self.tool_registry)
        self.error_handler = error_handler or ErrorHandlerAgent(max_retries=1, max_replan_attempts=2)
        self.logger = logger or _build_logger()
        self.metrics_collector = metrics_collector or ExecutionMetricsCollector(log_dir=LOG_DIR)
        self.learning_bridge = learning_bridge or LearningIntegrationBridge(
            metrics_collector=self.metrics_collector,
            log_dir=LOG_DIR,
        )
        self._improvements_applied = 0
        self._improvement_delta_tracking: dict[str, dict[str, Any]] = {}

    def run(
        self,
        goal: str,
        *,
        requested_actions: list[str] | None = None,
        replan_step: Callable[[dict[str, Any], Exception | str, int], dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        self.logger.info("pipeline_started run_id=%s goal=%s", run_id, goal[:100])

        # Hook: Feed metrics to learning engine
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.learning_bridge.feed_metrics_to_learning())
            finally:
                loop.close()
        except Exception as e:
            self.logger.warning("learning_metrics_feed_failed error=%s", str(e))

        plan_result: PlanResult = self.planner.plan(goal, requested_actions=requested_actions)
        if not plan_result.ok:
            self.logger.error("pipeline_plan_failed run_id=%s error=%s", run_id, plan_result.error)
            return {
                "ok": False,
                "status": "plan_failed",
                "run_id": run_id,
                "goal": goal,
                "steps": [],
                "results": [],
                "recoveries": [],
                "summary": str(plan_result.error or "Planning failed."),
                "improvement_delta": None,
            }

        results: list[dict[str, Any]] = []
        recoveries: list[RecoveryResult] = []
        step_payloads = [
            {
                "name": f"step_{index}",
                "action": step.action,
                "params": {
                    "action": step.action,
                    "description": step.description,
                    "goal": goal,
                    "step_index": index,
                },
            }
            for index, step in enumerate(plan_result.steps, start=1)
        ]

        for step in step_payloads:
            outcome = self._execute_checked(step, run_id)
            if outcome["ok"]:
                results.append(outcome)
                continue

            recovery = self.error_handler.execute_with_recovery(
                step=step,
                error=RuntimeError(outcome["error"]["message"]),
                execute_step=lambda current_step: self._execute_or_raise(current_step, run_id),
                replan_step=replan_step or self._default_replan_step,
            )
            recoveries.append(recovery)
            if recovery.ok:
                results.append(recovery.output)
            else:
                results.append(
                    {
                        "ok": False,
                        "run_id": run_id,
                        "action": step["action"],
                        "result": None,
                        "error": {
                            "type": "RecoverySkipped",
                            "message": recovery.error or "Recovery skipped.",
                        },
                    }
                )

        ok = all(item.get("ok") for item in results)
        status = "completed" if ok else "completed_with_recovery"
        summary = self._build_summary(goal, results, recoveries)

        # Record metrics
        success_count = sum(1 for r in results if r.get("ok"))
        error_msg = None if ok else "completed_with_recovery"
        duration = len(step_payloads) * 0.1  # Estimate
        self.metrics_collector.record_execution(
            run_id=run_id,
            action="pipeline",
            status="success" if ok else "partial",
            duration_seconds=duration,
            error_message=error_msg,
            retry_count=len(recoveries),
        )

        # Hook: Check and apply improvements (max 1 per cycle)
        improvement_delta = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                improvement_result = loop.run_until_complete(self.learning_bridge.check_and_apply_improvements())
                if improvement_result.get("status") == "success":
                    self._improvements_applied += 1
                    improvement_delta = {
                        "applied_type": improvement_result.get("improvement_applied"),
                        "expected_gain": improvement_result.get("expected_gain"),
                        "sequence": self._improvements_applied,
                    }
                    self.logger.info(
                        "improvement_applied run_id=%s type=%s expected_gain=%s",
                        run_id,
                        improvement_delta["applied_type"],
                        improvement_delta["expected_gain"],
                    )
                    self._improvement_delta_tracking[run_id] = improvement_delta
            finally:
                loop.close()
        except Exception as e:
            self.logger.warning("learning_improvement_failed error=%s", str(e))

        self.logger.info("pipeline_finished run_id=%s status=%s recovered=%s improvements=%s",
                        run_id, status, len(recoveries), self._improvements_applied)

        return {
            "ok": ok,
            "status": status,
            "run_id": run_id,
            "goal": goal,
            "steps": step_payloads,
            "results": results,
            "recoveries": [self._serialize_recovery(item) for item in recoveries],
            "summary": summary,
            "improvement_delta": improvement_delta,
        }

    def _execute_checked(self, step: dict[str, Any], run_id: str) -> dict[str, Any]:
        start_time = datetime.now(timezone.utc)
        result = self.executor.execute_step(step, run_id=run_id)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Log execution for learning
        status = "success" if result.get("ok") else "failure"
        error_msg = result.get("error", {}).get("message") if not result.get("ok") else None
        self.metrics_collector.record_execution(
            run_id=run_id,
            action=step.get("action", "unknown"),
            status=status,
            duration_seconds=duration,
            error_message=error_msg,
        )

        return result

    def _execute_or_raise(self, step: dict[str, Any], run_id: str) -> dict[str, Any]:
        output = self._execute_checked(step, run_id)
        if not output["ok"]:
            raise RuntimeError(output["error"]["message"])
        return output

    def _default_replan_step(
        self,
        step: dict[str, Any],
        error: Exception | str,
        attempt: int,
    ) -> dict[str, Any]:
        params = dict(step.get("params") or {})
        params["replanned_from"] = step.get("action")
        params["replan_attempt"] = attempt
        params["replan_reason"] = str(error)
        return {
            "name": f"{step.get('name', 'step')}_replan_{attempt}",
            "action": "verify",
            "params": params,
        }

    def _build_summary(
        self,
        goal: str,
        results: list[dict[str, Any]],
        recoveries: list[RecoveryResult],
    ) -> str:
        successful = sum(1 for item in results if item.get("ok"))
        failed = len(results) - successful
        recovered = sum(1 for item in recoveries if item.ok)
        return (
            f"Goal '{goal[:80]}' processed across {len(results)} steps. "
            f"Successful steps: {successful}. Failed steps: {failed}. "
            f"Recoveries attempted: {len(recoveries)}. Recoveries succeeded: {recovered}."
        )

    @staticmethod
    def _serialize_recovery(recovery: RecoveryResult) -> dict[str, Any]:
        return {
            "ok": recovery.ok,
            "decision": recovery.decision.value,
            "step": dict(recovery.step),
            "output": recovery.output,
            "error": recovery.error,
            "retry_attempts": recovery.retry_attempts,
            "replan_attempts": recovery.replan_attempts,
            "recovery_path": list(recovery.recovery_path),
        }

    def get_learning_metrics(self) -> dict[str, Any]:
        """Get current learning metrics and improvement tracking"""
        return {
            "improvements_applied": self._improvements_applied,
            "improvement_deltas": self._improvement_delta_tracking,
            "learning_engine_status": self.learning_bridge.get_learning_status(),
        }
