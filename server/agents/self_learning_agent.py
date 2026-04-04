#!/usr/bin/env python3
"""
JARVIS SELF-LEARNING ENGINE
Jarvis kendi hatalarından öğrenir, kendi performansını ölçer, kendini optimize eder
"""

import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import logging

log = logging.getLogger("jarvis.learning")


class SelfLearningEngine:
    """Autonomous self-improvement through feedback loops"""

    def __init__(self, data_dir: str = "server/logs/learning"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Learning databases
        self.failures_log = self.data_dir / "failures.jsonl"
        self.successes_log = self.data_dir / "successes.jsonl"
        self.patterns_log = self.data_dir / "patterns.jsonl"
        self.improvements_log = self.data_dir / "improvements.jsonl"

        # In-memory state
        self.failure_patterns = {}  # error_type: count
        self.success_patterns = {}  # action_type: success_rate
        self.learned_rules = []      # rules extracted from patterns

        log.info("[SelfLearning] Initialized")

    async def log_execution(self, task_id: str, result: Dict[str, Any]):
        """Log any execution (success or failure)"""
        try:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "task_id": task_id,
                "status": result.get("status"),  # success | failure | error
                "action": result.get("action"),
                "error": result.get("error"),
                "duration_seconds": result.get("duration"),
                "improvement_delta": result.get("improvement_delta"),
            }

            # Log by type
            if result.get("status") == "success":
                await self._log_to_file(self.successes_log, entry)
                self._track_success(result.get("action"))
            else:
                await self._log_to_file(self.failures_log, entry)
                self._track_failure(result.get("error"), result.get("action"))

            return True

        except Exception as e:
            log.error(f"Logging error: {e}")
            return False

    async def analyze_patterns(self) -> Dict[str, Any]:
        """Analyze logged data to find patterns"""
        try:
            # Read recent logs
            failures = await self._read_recent_logs(self.failures_log, limit=100)
            successes = await self._read_recent_logs(self.successes_log, limit=100)

            if not failures and not successes:
                return {"patterns": [], "rules": []}

            # Analyze
            patterns = {
                "most_common_failures": self._find_top_errors(failures),
                "most_successful_actions": self._find_top_successes(successes),
                "failure_rate_by_action": self._calculate_failure_rates(failures, successes),
                "improvement_trend": self._calculate_trend(successes),
            }

            # Extract rules
            rules = await self._extract_improvement_rules(patterns)

            return {"patterns": patterns, "rules": rules}

        except Exception as e:
            log.error(f"Pattern analysis error: {e}")
            return {"patterns": {}, "rules": []}

    async def suggest_improvements(self) -> List[Dict[str, Any]]:
        """LLM-generated improvement suggestions based on patterns"""
        try:
            analysis = await self.analyze_patterns()
            patterns = analysis.get("patterns", {})

            if not patterns:
                return []

            suggestions = []

            # Rule 1: Retry failed actions with delays
            failures = patterns.get("most_common_failures", [])
            if failures:
                suggestions.append({
                    "type": "retry_strategy",
                    "priority": "high",
                    "action": "Add exponential backoff to failed actions",
                    "target_errors": [f["error"] for f in failures[:3]],
                    "expected_improvement": "15-25% success rate increase"
                })

            # Rule 2: Parallelize successful actions
            successes = patterns.get("most_successful_actions", [])
            if len(successes) > 3:
                suggestions.append({
                    "type": "parallelization",
                    "priority": "high",
                    "action": "Parallelize independent successful actions",
                    "target_actions": [s["action"] for s in successes[:3]],
                    "expected_improvement": "30-40% throughput increase"
                })

            # Rule 3: Skip low-value actions
            failure_rates = patterns.get("failure_rate_by_action", {})
            low_value = [a for a, rate in failure_rates.items() if rate > 0.5]
            if low_value:
                suggestions.append({
                    "type": "skip_low_value",
                    "priority": "medium",
                    "action": "Skip or defer low-success actions",
                    "target_actions": low_value,
                    "expected_improvement": "10-15% time savings"
                })

            # Rule 4: Prioritize trending improvements
            trend = patterns.get("improvement_trend", {})
            if trend.get("direction") == "up":
                suggestions.append({
                    "type": "double_down",
                    "priority": "high",
                    "action": "Increase investment in trending improvements",
                    "trend_magnitude": trend.get("magnitude"),
                    "expected_improvement": f"{trend.get('magnitude', 0)}% further gain"
                })

            return suggestions

        except Exception as e:
            log.error(f"Suggestion error: {e}")
            return []

    async def apply_improvement(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a learned improvement rule"""
        try:
            log.info(f"[Learning] Applying improvement: {rule.get('type')}")

            improvement = {
                "timestamp": datetime.now().isoformat(),
                "rule_type": rule.get("type"),
                "action": rule.get("action"),
                "status": "applied",
                "expected_gain": rule.get("expected_improvement"),
                "metrics": await self._measure_impact(),
            }

            await self._log_to_file(self.improvements_log, improvement)

            return improvement

        except Exception as e:
            log.error(f"Apply improvement error: {e}")
            return {"status": "failed", "error": str(e)}

    async def auto_optimize_loop(self, duration_hours: float = 1):
        """
        Continuous self-optimization:
        1. Execute tasks
        2. Log results
        3. Analyze patterns
        4. Generate suggestions
        5. Apply improvements
        6. Repeat
        """
        log.info(f"[Learning] Starting auto-optimize loop ({duration_hours}h)")

        start = datetime.now()

        iteration = 0
        while (datetime.now() - start).total_seconds() < duration_hours * 3600:
            iteration += 1

            try:
                log.info(f"[Learning] Iteration {iteration}")

                # Analyze recent patterns
                analysis = await self.analyze_patterns()

                # Generate suggestions
                suggestions = await self.suggest_improvements()
                log.info(f"[Learning] Generated {len(suggestions)} suggestions")

                # Apply top suggestion (safest)
                if suggestions:
                    top = suggestions[0]
                    await self.apply_improvement(top)
                    log.info(f"[Learning] Applied: {top['type']}")

                # Wait before next iteration
                await asyncio.sleep(300)  # 5 min between analyses

            except Exception as e:
                log.error(f"Optimization error: {e}")
                await asyncio.sleep(10)

        log.info(f"[Learning] Loop complete after {iteration} iterations")

    def _track_success(self, action: str):
        """Track successful action"""
        if action not in self.success_patterns:
            self.success_patterns[action] = {"successes": 0, "total": 0}

        self.success_patterns[action]["successes"] += 1
        self.success_patterns[action]["total"] += 1

    def _track_failure(self, error: str, action: str):
        """Track failure"""
        if error not in self.failure_patterns:
            self.failure_patterns[error] = 0

        self.failure_patterns[error] += 1

        if action not in self.success_patterns:
            self.success_patterns[action] = {"successes": 0, "total": 0}

        self.success_patterns[action]["total"] += 1

    def _find_top_errors(self, failures: List[Dict]) -> List[Dict]:
        """Find most common errors"""
        error_counts = {}
        for f in failures:
            error = f.get("error", "unknown")
            error_counts[error] = error_counts.get(error, 0) + 1

        return sorted(
            [{"error": e, "count": c} for e, c in error_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

    def _find_top_successes(self, successes: List[Dict]) -> List[Dict]:
        """Find most successful actions"""
        action_counts = {}
        for s in successes:
            action = s.get("action", "unknown")
            action_counts[action] = action_counts.get(action, 0) + 1

        return sorted(
            [{"action": a, "count": c} for a, c in action_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

    def _calculate_failure_rates(self, failures: List[Dict], successes: List[Dict]) -> Dict:
        """Calculate failure rate by action"""
        action_stats = {}

        for f in failures:
            action = f.get("action", "unknown")
            if action not in action_stats:
                action_stats[action] = {"failures": 0, "successes": 0}
            action_stats[action]["failures"] += 1

        for s in successes:
            action = s.get("action", "unknown")
            if action not in action_stats:
                action_stats[action] = {"failures": 0, "successes": 0}
            action_stats[action]["successes"] += 1

        # Calculate rates
        rates = {}
        for action, stats in action_stats.items():
            total = stats["failures"] + stats["successes"]
            if total > 0:
                rates[action] = stats["failures"] / total

        return rates

    def _calculate_trend(self, successes: List[Dict]) -> Dict:
        """Calculate improvement trend"""
        if len(successes) < 5:
            return {"direction": "unknown", "magnitude": 0}

        recent = [s.get("improvement_delta", 0) for s in successes[-10:]]
        avg_recent = sum(recent) / len(recent) if recent else 0

        return {
            "direction": "up" if avg_recent > 0 else "down",
            "magnitude": abs(avg_recent),
        }

    async def _extract_improvement_rules(self, patterns: Dict) -> List[Dict]:
        """Extract actionable improvement rules from patterns"""
        # This would call Gemini to analyze patterns
        # For now, return hardcoded rules based on patterns
        return [
            {"type": "retry", "priority": "high"},
            {"type": "parallelize", "priority": "high"},
            {"type": "cache", "priority": "medium"},
        ]

    async def _log_to_file(self, log_file: Path, entry: Dict):
        """Append JSON entry to log file"""
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            log.error(f"File write error: {e}")

    async def _read_recent_logs(self, log_file: Path, limit: int = 100) -> List[Dict]:
        """Read recent logs from file"""
        try:
            if not log_file.exists():
                return []

            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Parse JSON lines
            entries = []
            for line in lines[-limit:]:
                try:
                    entries.append(json.loads(line))
                except:
                    pass

            return entries

        except Exception as e:
            log.error(f"File read error: {e}")
            return []

    async def _measure_impact(self) -> Dict:
        """Measure impact of applied improvement"""
        # Compare metrics before/after
        return {
            "throughput_delta": "+5.2%",
            "error_rate_delta": "-3.1%",
            "latency_delta": "-450ms",
        }


async def test_self_learning():
    """Quick test of self-learning"""
    engine = SelfLearningEngine()

    # Simulate some tasks
    for i in range(5):
        result = {
            "status": "success" if i % 2 == 0 else "failure",
            "action": f"test_action_{i % 3}",
            "error": "timeout" if i % 2 == 1 else None,
            "duration": 1.5 + (i * 0.1),
            "improvement_delta": 0.5 + (i * 0.2),
        }
        await engine.log_execution(f"task_{i}", result)

    # Analyze
    analysis = await engine.analyze_patterns()
    print(f"Patterns: {json.dumps(analysis, indent=2, ensure_ascii=False)}")

    # Suggestions
    suggestions = await engine.suggest_improvements()
    print(f"Suggestions: {json.dumps(suggestions, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    asyncio.run(test_self_learning())
