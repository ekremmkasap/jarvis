#!/usr/bin/env python3
"""
JARVIS LEARNING DASHBOARD
Real-time monitoring of autonomous improvements + metrics
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta


class LearningDashboard:
    """Monitor self-learning progress and improvements"""

    def __init__(self, log_dir: str = "server/logs/learning"):
        self.log_dir = Path(log_dir)

    def get_learning_stats(self) -> Dict[str, Any]:
        """Aggregate learning statistics"""
        try:
            successes = self._load_logs("successes.jsonl")
            failures = self._load_logs("failures.jsonl")
            improvements = self._load_logs("improvements.jsonl")

            if not successes and not failures:
                return {"status": "no_data"}

            total_executions = len(successes) + len(failures)
            success_rate = (len(successes) / total_executions * 100) if total_executions > 0 else 0

            # Calculate trends
            recent_5_successes = [s.get("improvement_delta", 0) for s in successes[-5:]]
            avg_improvement = sum(recent_5_successes) / len(recent_5_successes) if recent_5_successes else 0

            return {
                "status": "active",
                "total_executions": total_executions,
                "successes": len(successes),
                "failures": len(failures),
                "success_rate_pct": round(success_rate, 1),
                "avg_improvement_pct": round(avg_improvement, 2),
                "total_improvements_applied": len(improvements),
                "latest_improvement": improvements[-1] if improvements else None,
                "error_types": self._count_error_types(failures),
                "success_actions": self._count_success_actions(successes),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_improvement_timeline(self) -> list[Dict[str, Any]]:
        """Get timeline of applied improvements"""
        try:
            improvements = self._load_logs("improvements.jsonl")
            return sorted(
                improvements,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:20]  # Last 20
        except Exception as e:
            return []

    def get_failure_analysis(self) -> Dict[str, Any]:
        """Analyze failure patterns"""
        try:
            failures = self._load_logs("failures.jsonl")

            error_counts = {}
            action_failures = {}

            for f in failures:
                error = f.get("error", "unknown")
                action = f.get("action", "unknown")

                error_counts[error] = error_counts.get(error, 0) + 1
                action_failures[action] = action_failures.get(action, 0) + 1

            return {
                "total_failures": len(failures),
                "unique_errors": len(error_counts),
                "most_common_errors": sorted(
                    [{"error": e, "count": c} for e, c in error_counts.items()],
                    key=lambda x: x["count"],
                    reverse=True
                )[:5],
                "problematic_actions": sorted(
                    [{"action": a, "failures": c} for a, c in action_failures.items()],
                    key=lambda x: x["failures"],
                    reverse=True
                )[:5],
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_success_analysis(self) -> Dict[str, Any]:
        """Analyze success patterns"""
        try:
            successes = self._load_logs("successes.jsonl")

            action_counts = {}
            improvement_deltas = {}

            for s in successes:
                action = s.get("action", "unknown")
                delta = s.get("improvement_delta", 0)

                action_counts[action] = action_counts.get(action, 0) + 1
                if action not in improvement_deltas:
                    improvement_deltas[action] = []
                improvement_deltas[action].append(delta)

            # Calculate avg improvement per action
            action_improvements = {
                action: round(sum(deltas) / len(deltas), 2)
                for action, deltas in improvement_deltas.items()
            }

            return {
                "total_successes": len(successes),
                "most_successful_actions": sorted(
                    [{"action": a, "count": c} for a, c in action_counts.items()],
                    key=lambda x: x["count"],
                    reverse=True
                )[:5],
                "highest_improvement_actions": sorted(
                    [{"action": a, "avg_improvement": v} for a, v in action_improvements.items()],
                    key=lambda x: x["avg_improvement"],
                    reverse=True
                )[:5],
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get overall performance metrics"""
        try:
            successes = self._load_logs("successes.jsonl")
            improvements = self._load_logs("improvements.jsonl")

            if not successes:
                return {"status": "no_data"}

            # Aggregate metrics from improvements
            total_throughput_gain = 0
            total_latency_improvement = 0
            total_error_reduction = 0

            for imp in improvements:
                metrics = imp.get("metrics", {})
                # Parse delta strings like "+5.2%"
                for key, value in metrics.items():
                    if isinstance(value, str):
                        try:
                            num = float(value.replace("+", "").replace("%", "").replace("ms", ""))
                            if "throughput" in key:
                                total_throughput_gain += num
                            elif "latency" in key:
                                total_latency_improvement += num
                            elif "error" in key:
                                total_error_reduction += abs(num)
                        except:
                            pass

            return {
                "total_throughput_gain_pct": round(total_throughput_gain, 1),
                "total_latency_improvement_ms": round(total_latency_improvement, 0),
                "total_error_reduction_pct": round(total_error_reduction, 1),
                "improvements_applied": len(improvements),
                "avg_improvement_per_cycle": round(
                    total_throughput_gain / max(len(improvements), 1), 2
                ),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def export_dashboard_json(self, output_path: str = "server/logs/learning_dashboard.json"):
        """Export complete dashboard to JSON"""
        try:
            dashboard = {
                "timestamp": datetime.now().isoformat(),
                "learning_stats": self.get_learning_stats(),
                "failure_analysis": self.get_failure_analysis(),
                "success_analysis": self.get_success_analysis(),
                "performance_metrics": self.get_performance_metrics(),
                "recent_improvements": self.get_improvement_timeline(),
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dashboard, f, indent=2, ensure_ascii=False)

            return {"status": "saved", "path": output_path}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _load_logs(self, filename: str) -> list[Dict]:
        """Load JSON lines from log file"""
        log_file = self.log_dir / filename
        if not log_file.exists():
            return []

        logs = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    logs.append(json.loads(line))
                except:
                    pass

        return logs

    def _count_error_types(self, failures: list[Dict]) -> Dict[str, int]:
        """Count error types"""
        counts = {}
        for f in failures:
            error = f.get("error", "unknown")
            counts[error] = counts.get(error, 0) + 1
        return counts

    def _count_success_actions(self, successes: list[Dict]) -> Dict[str, int]:
        """Count successful actions"""
        counts = {}
        for s in successes:
            action = s.get("action", "unknown")
            counts[action] = counts.get(action, 0) + 1
        return counts


def main():
    """Test dashboard"""
    dashboard = LearningDashboard()

    stats = dashboard.get_learning_stats()
    print("Learning Stats:", json.dumps(stats, indent=2, ensure_ascii=False))

    failures = dashboard.get_failure_analysis()
    print("\nFailure Analysis:", json.dumps(failures, indent=2, ensure_ascii=False))

    successes = dashboard.get_success_analysis()
    print("\nSuccess Analysis:", json.dumps(successes, indent=2, ensure_ascii=False))

    metrics = dashboard.get_performance_metrics()
    print("\nPerformance Metrics:", json.dumps(metrics, indent=2, ensure_ascii=False))

    # Export
    result = dashboard.export_dashboard_json()
    print(f"\nDashboard exported: {result}")


if __name__ == "__main__":
    main()
