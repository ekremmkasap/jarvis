#!/usr/bin/env python3
"""
Week 1 Integration Tests
Tests voice layer, planner, executor, and error handler integration
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

from agents.executor_agent import ExecutorAgent
from agents.error_handler_agent import ErrorHandlerAgent


class Week1IntegrationTests:
    """Test suite for Week 1 buildout"""

    def __init__(self):
        self.executor = ExecutorAgent()
        self.error_handler = ErrorHandlerAgent()
        self.test_results = []

    async def test_executor_single_step(self) -> bool:
        """Test: Execute a single step successfully"""
        test_name = "Executor: Single Step"
        try:
            step = {
                "action": "compile_code",
                "target": "src/main.py",
                "params": {},
            }
            result = await self.executor.execute_step(step, step_index=0)
            passed = result["status"] == "success"
            self._record_result(test_name, passed, result)
            return passed
        except Exception as e:
            self._record_result(test_name, False, {"error": str(e)})
            return False

    async def test_executor_three_steps(self) -> bool:
        """Test: Execute 3-step plan successfully"""
        test_name = "Executor: Three Steps"
        try:
            plan = [
                {"action": "compile_code", "target": "src/main.py", "params": {}},
                {"action": "run_tests", "target": "tests/", "params": {}},
                {
                    "action": "git_commit",
                    "target": None,
                    "params": {"message": "test commit"},
                },
            ]
            result = await self.executor.execute_plan(plan)
            passed = result["status"] == "success"
            self._record_result(test_name, passed, result)
            return passed
        except Exception as e:
            self._record_result(test_name, False, {"error": str(e)})
            return False

    async def test_error_handler_retry_decision(self) -> bool:
        """Test: Error handler suggests RETRY for timeout"""
        test_name = "ErrorHandler: Retry Decision"
        try:
            error = "Connection timeout after 30s"
            step = {"action": "run_tests", "target": "tests/"}

            analysis = self.error_handler.analyze_error(error, step)
            decision = self.error_handler.decide_recovery(analysis, retry_count=0, replan_count=0)

            passed = decision["action"] == "retry"
            self._record_result(test_name, passed, {"analysis": analysis, "decision": decision})
            return passed
        except Exception as e:
            self._record_result(test_name, False, {"error": str(e)})
            return False

    async def test_error_handler_replan_decision(self) -> bool:
        """Test: Error handler suggests REPLAN for permission denied"""
        test_name = "ErrorHandler: Replan Decision"
        try:
            error = "Permission denied: unable to write file"
            step = {"action": "write_file", "target": "/restricted/file.txt"}

            analysis = self.error_handler.analyze_error(error, step)
            decision = self.error_handler.decide_recovery(analysis, retry_count=0, replan_count=0)

            passed = decision["action"] == "replan"
            self._record_result(test_name, passed, {"analysis": analysis, "decision": decision})
            return passed
        except Exception as e:
            self._record_result(test_name, False, {"error": str(e)})
            return False

    async def test_error_handler_skip_after_max_attempts(self) -> bool:
        """Test: Error handler suggests SKIP after max attempts exhausted"""
        test_name = "ErrorHandler: Skip After Max Attempts"
        try:
            error = "Unknown error occurred"
            step = {"action": "some_action", "target": "target"}

            analysis = self.error_handler.analyze_error(error, step)
            # Max out both retry and replan counts
            decision = self.error_handler.decide_recovery(
                analysis,
                retry_count=self.error_handler.max_retries,
                replan_count=self.error_handler.max_replan_attempts,
            )

            passed = decision["action"] == "skip"
            self._record_result(test_name, passed, {"analysis": analysis, "decision": decision})
            return passed
        except Exception as e:
            self._record_result(test_name, False, {"error": str(e)})
            return False

    async def test_executor_with_timeout(self) -> bool:
        """Test: Executor handles timeout correctly"""
        test_name = "Executor: Timeout Handling"
        try:
            # Create a step with very short timeout
            step = {
                "action": "run_tests",
                "target": "tests/",
                "params": {},
            }
            # Manually set timeout to 0.01s to trigger timeout
            self.executor.timeout_seconds = 0.01
            result = await self.executor.execute_step(step, step_index=0)
            self.executor.timeout_seconds = 30  # Reset

            passed = result["status"] == "timeout"
            self._record_result(test_name, passed, result)
            return passed
        except Exception as e:
            self._record_result(test_name, False, {"error": str(e)})
            return False

    async def run_all_tests(self) -> Dict:
        """Run all Week 1 integration tests"""
        print("\n" + "=" * 60)
        print("WEEK 1 INTEGRATION TEST SUITE")
        print("=" * 60 + "\n")

        tests = [
            ("Executor Single Step", self.test_executor_single_step),
            ("Executor Three Steps", self.test_executor_three_steps),
            ("Error Handler Retry", self.test_error_handler_retry_decision),
            ("Error Handler Replan", self.test_error_handler_replan_decision),
            ("Error Handler Skip", self.test_error_handler_skip_after_max_attempts),
            ("Executor Timeout", self.test_executor_with_timeout),
        ]

        passed_count = 0
        failed_count = 0

        for test_name, test_func in tests:
            try:
                result = await test_func()
                if result:
                    passed_count += 1
                    print(f"[OK] {test_name}: PASS")
                else:
                    failed_count += 1
                    print(f"[FAIL] {test_name}: FAIL")
            except Exception as e:
                failed_count += 1
                print(f"[ERR] {test_name}: ERROR - {e}")

        print("\n" + "=" * 60)
        print(f"RESULTS: {passed_count} passed, {failed_count} failed")
        print("=" * 60 + "\n")

        return {
            "total": len(tests),
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": round(100 * passed_count / len(tests), 1),
            "test_results": self.test_results,
        }

    def _record_result(self, test_name: str, passed: bool, details: dict) -> None:
        """Record test result"""
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "details": details,
        })


async def main():
    """Run test suite"""
    tests = Week1IntegrationTests()
    results = await tests.run_all_tests()

    # Save results
    output_file = Path("server/logs/week1_test_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Test results saved to: {output_file}")
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
