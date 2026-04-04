#!/usr/bin/env python3
"""
Error Handler Agent - Handle failures with RETRY/REPLAN/SKIP decisions
Implements error recovery with max 2 replan attempts
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ErrorHandlerAgent:
    """Handle execution errors with intelligent recovery strategies."""

    def __init__(self, log_dir: str = "server/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.error_log = self.log_dir / "error_recovery.jsonl"
        self.max_replan_attempts = 2
        self.retry_backoff_base = 1  # seconds
        self.retry_backoff_multiplier = 2
        self.max_retries = 3

    def analyze_error(self, error: str, step_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify error type and suggest recovery strategy.

        Returns:
            Dict with 'error_type', 'strategy', 'retry_count', 'priority'
        """
        error_lower = error.lower()
        action = step_definition.get("action", "").lower()

        # Classify error type
        if "timeout" in error_lower:
            error_type = "timeout"
            strategy = "retry"  # Retry with longer timeout
            priority = "high"
        elif "not found" in error_lower or "404" in error_lower:
            error_type = "not_found"
            strategy = "skip"  # Skip this step
            priority = "medium"
        elif "permission" in error_lower or "denied" in error_lower:
            error_type = "permission_denied"
            strategy = "replan"  # Need to replan approach
            priority = "high"
        elif "rate_limit" in error_lower or "429" in error_lower:
            error_type = "rate_limit"
            strategy = "retry"  # Retry with backoff
            priority = "high"
        elif "connection" in error_lower or "network" in error_lower:
            error_type = "connection_error"
            strategy = "retry"  # Retry connection
            priority = "high"
        else:
            error_type = "unknown"
            strategy = "replan"  # Default to replan
            priority = "medium"

        return {
            "error_type": error_type,
            "action": action,
            "strategy": strategy,  # "retry", "replan", or "skip"
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
        }

    def decide_recovery(
        self,
        error_analysis: Dict[str, Any],
        retry_count: int,
        replan_count: int,
    ) -> Dict[str, Any]:
        """
        Decide which recovery action to take based on error and attempt counts.

        Returns:
            Dict with 'action', 'reasoning', 'next_params'
        """
        strategy = error_analysis.get("strategy", "replan")

        # Decide based on counts and strategy
        if strategy == "retry" and retry_count < self.max_retries:
            backoff_delay = self.retry_backoff_base * (
                self.retry_backoff_multiplier ** retry_count
            )
            return {
                "action": "retry",
                "reasoning": f"Retrying with {backoff_delay}s backoff",
                "next_params": {
                    "delay_seconds": backoff_delay,
                    "retry_count": retry_count + 1,
                },
            }
        elif strategy == "replan" and replan_count < self.max_replan_attempts:
            return {
                "action": "replan",
                "reasoning": f"Replanning step (attempt {replan_count + 1}/{self.max_replan_attempts})",
                "next_params": {
                    "replan_count": replan_count + 1,
                    "original_error": error_analysis.get("error_type"),
                },
            }
        else:
            # Skip this step if retries/replans are exhausted
            return {
                "action": "skip",
                "reasoning": f"Max attempts reached (retries:{retry_count}, replans:{replan_count}). Skipping.",
                "next_params": {"skipped": True},
            }

    async def handle_step_error(
        self,
        step_definition: Dict[str, Any],
        error: str,
        execution_history: List[Dict[str, Any]],
        retry_count: int = 0,
        replan_count: int = 0,
    ) -> Dict[str, Any]:
        """
        Handle an error from step execution.

        Returns:
            Dict with 'recovery_action', 'analysis', 'decision', 'next_step'
        """
        analysis = self.analyze_error(error, step_definition)
        decision = self.decide_recovery(analysis, retry_count, replan_count)

        recovery_record = {
            "timestamp": datetime.now().isoformat(),
            "step": step_definition,
            "error": error,
            "analysis": analysis,
            "decision": decision,
            "retry_count": retry_count,
            "replan_count": replan_count,
        }

        # Log the recovery decision
        self._log_recovery(recovery_record)

        if decision["action"] == "retry":
            logger.info(f"Recovery: RETRY with {decision['next_params']['delay_seconds']}s backoff")
            await asyncio.sleep(decision["next_params"]["delay_seconds"])
            return {
                "recovery_action": "retry",
                "analysis": analysis,
                "decision": decision,
                "next_step": {
                    **step_definition,
                    "retry_count": decision["next_params"]["retry_count"],
                },
            }

        elif decision["action"] == "replan":
            logger.info(
                f"Recovery: REPLAN (attempt {decision['next_params']['replan_count']})"
            )
            return {
                "recovery_action": "replan",
                "analysis": analysis,
                "decision": decision,
                "suggested_changes": self._suggest_replanning(
                    step_definition, error, execution_history
                ),
            }

        else:  # skip
            logger.info("Recovery: SKIP - max attempts exhausted")
            return {
                "recovery_action": "skip",
                "analysis": analysis,
                "decision": decision,
                "reason": "Max retry/replan attempts exceeded",
            }

    def _suggest_replanning(
        self,
        step_definition: Dict[str, Any],
        error: str,
        history: List[Dict[str, Any]],
    ) -> List[str]:
        """Suggest alternative approaches based on error and history"""
        action = step_definition.get("action", "")
        suggestions = []

        error_lower = error.lower()

        if "timeout" in error_lower:
            suggestions.append(f"Break '{action}' into smaller sub-steps")
            suggestions.append("Consider parallel execution where possible")
        elif "permission" in error_lower:
            suggestions.append("Add authentication/authorization step before this action")
            suggestions.append("Verify permissions are correctly configured")
        elif "not found" in error_lower:
            suggestions.append("Verify resource exists or is accessible")
            suggestions.append("Add validation step before this action")
        elif "rate_limit" in error_lower:
            suggestions.append("Add delay between requests")
            suggestions.append("Consider batching requests")
        else:
            suggestions.append(f"Review '{action}' parameters and dependencies")
            suggestions.append("Check if prerequisites are met before this step")

        return suggestions

    def create_fallback_plan(
        self, failed_step: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Create a fallback plan when normal execution fails completely.

        Returns a simplified alternative approach.
        """
        action = failed_step.get("action", "unknown")

        # Generic fallback: just log and skip
        fallback = [
            {
                "action": "log_failure",
                "target": action,
                "params": {"reason": "original_approach_failed"},
            },
            {
                "action": "skip",
                "target": action,
                "params": {"fallback": True},
            },
        ]

        return fallback

    def _log_recovery(self, record: Dict[str, Any]) -> None:
        """Append recovery record to JSONL log"""
        try:
            with open(self.error_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to log recovery: {e}")

    def get_error_patterns(self, limit: int = 100) -> Dict[str, Any]:
        """Analyze error patterns from recovery logs"""
        if not self.error_log.exists():
            return {}

        error_types = {}
        recovery_actions = {}

        try:
            with open(self.error_log, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        error_type = record.get("analysis", {}).get("error_type", "unknown")
                        action = record.get("decision", {}).get("action", "unknown")

                        error_types[error_type] = error_types.get(error_type, 0) + 1
                        recovery_actions[action] = recovery_actions.get(action, 0) + 1
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.error(f"Failed to read error patterns: {e}")

        return {
            "total_errors": sum(error_types.values()),
            "error_types": error_types,
            "recovery_actions": recovery_actions,
        }


async def example_error_handling():
    """Example usage of ErrorHandlerAgent"""
    handler = ErrorHandlerAgent()

    # Simulate an error
    step_def = {
        "action": "run_tests",
        "target": "tests/",
        "params": {},
    }

    error_msg = "Connection timeout after 30s"

    result = await handler.handle_step_error(
        step_definition=step_def,
        error=error_msg,
        execution_history=[],
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(example_error_handling())
