#!/usr/bin/env python3
"""
Executor Agent - Execute individual steps from a plan
Handles tool invocation, error collection, timeout management
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, List

logger = logging.getLogger(__name__)


class ExecutorAgent:
    """Execute individual steps with tool integration and error handling."""

    def __init__(self, log_dir: str = "server/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.execution_log = self.log_dir / "execution_steps.jsonl"
        self.skill_registry = self._load_skill_registry()
        self.max_retries = 1
        self.timeout_seconds = 30

    def _load_skill_registry(self) -> Dict[str, Any]:
        """Load available skills from skill registry"""
        registry_path = Path("server/config/skill_registry.json")
        if registry_path.exists():
            try:
                with open(registry_path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load skill registry: {e}")
        return self._fallback_registry()

    def _fallback_registry(self) -> Dict[str, Any]:
        """Fallback skill registry if file doesn't exist"""
        return {
            "skills": {
                "run_tests": {"type": "function", "timeout": 60},
                "compile_code": {"type": "function", "timeout": 30},
                "read_file": {"type": "function", "timeout": 5},
                "write_file": {"type": "function", "timeout": 5},
                "run_command": {"type": "function", "timeout": 30},
                "git_commit": {"type": "function", "timeout": 10},
            }
        }

    async def execute_step(
        self,
        step_definition: Dict[str, Any],
        step_index: int = 0,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute a single step from the plan.

        Args:
            step_definition: Dict with 'action', 'target', 'params'
            step_index: Position in plan (for logging)
            context: Contextual information from previous steps

        Returns:
            Dict with 'status', 'output', 'error', 'duration', 'meta'
        """
        context = context or {}
        start_time = datetime.now()

        execution_record = {
            "timestamp": start_time.isoformat(),
            "step_index": step_index,
            "step_definition": step_definition,
            "status": None,
            "output": None,
            "error": None,
            "duration_seconds": 0,
        }

        try:
            action = step_definition.get("action", "").lower()
            target = step_definition.get("target")
            params = step_definition.get("params", {})

            if not action:
                raise ValueError("Step definition missing 'action' field")

            logger.info(f"[STEP {step_index}] Executing: {action} on {target}")

            # Check if skill exists
            skill_config = self.skill_registry.get("skills", {}).get(action)
            if not skill_config:
                raise ValueError(f"Unknown skill: {action}")

            # Execute with timeout
            timeout = skill_config.get("timeout", self.timeout_seconds)
            result = await asyncio.wait_for(
                self._invoke_skill(action, target, params, context),
                timeout=timeout,
            )

            execution_record["status"] = "success"
            execution_record["output"] = result
            logger.info(f"[STEP {step_index}] Success: {action}")

        except asyncio.TimeoutError:
            execution_record["status"] = "timeout"
            execution_record["error"] = f"Step {step_index} timed out after {timeout}s"
            logger.error(f"[STEP {step_index}] Timeout: {execution_record['error']}")

        except Exception as e:
            execution_record["status"] = "error"
            execution_record["error"] = str(e)
            logger.error(f"[STEP {step_index}] Error: {e}")

        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            execution_record["duration_seconds"] = round(elapsed, 2)
            self._log_execution(execution_record)

        return execution_record

    async def execute_plan(
        self,
        plan: List[Dict[str, Any]],
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Execute all steps in a plan sequentially.

        Returns dict with:
        - total_steps: int
        - completed_steps: int
        - failed_at: int or None
        - steps: list of execution records
        - status: "success", "partial", or "failed"
        """
        context = context or {}
        results = {
            "total_steps": len(plan),
            "completed_steps": 0,
            "failed_at": None,
            "steps": [],
            "status": "success",
        }

        for step_idx, step_def in enumerate(plan):
            result = await self.execute_step(step_def, step_idx, context)
            results["steps"].append(result)

            if result["status"] in ["error", "timeout"]:
                results["failed_at"] = step_idx
                results["status"] = "partial" if step_idx > 0 else "failed"
                logger.warning(f"Plan execution stopped at step {step_idx}")
                break
            else:
                results["completed_steps"] += 1

            # Update context for next step
            if result["status"] == "success" and result["output"]:
                context[f"step_{step_idx}_output"] = result["output"]

        return results

    async def _invoke_skill(
        self,
        action: str,
        target: Optional[str],
        params: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        """
        Invoke a skill with parameters.
        This is a stub that would integrate with actual skill implementations.
        """
        # Simulate skill invocation
        await asyncio.sleep(0.1)

        if action == "run_tests":
            return {"passed": 10, "failed": 0, "coverage": 95}
        elif action == "compile_code":
            return {"status": "compiled", "target": target}
        elif action == "read_file":
            return {"content": f"Content of {target}"}
        elif action == "write_file":
            return {"written": target, "bytes": len(params.get("content", ""))}
        elif action == "git_commit":
            return {"hash": "abc1234", "message": params.get("message")}
        elif action == "run_command":
            return {"returncode": 0, "stdout": "Command executed"}
        else:
            return {"result": f"{action} executed on {target}"}

    def _log_execution(self, record: Dict[str, Any]) -> None:
        """Append execution record to JSONL log"""
        try:
            with open(self.execution_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent execution history"""
        if not self.execution_log.exists():
            return []

        records = []
        try:
            with open(self.execution_log, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            logger.error(f"Failed to read execution history: {e}")

        return records[-limit:]


async def example_execution():
    """Example usage of ExecutorAgent"""
    executor = ExecutorAgent()

    # Example plan with steps
    plan = [
        {"action": "compile_code", "target": "src/main.py", "params": {}},
        {"action": "run_tests", "target": "tests/", "params": {}},
        {
            "action": "git_commit",
            "target": None,
            "params": {"message": "feat: Week 1 implementation"},
        },
    ]

    results = await executor.execute_plan(plan)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(example_execution())
