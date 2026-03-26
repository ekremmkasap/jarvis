from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.request import urlopen

from agents.runtime_base import RuntimeAgent

SYSTEM = """You are the Jarvis MissionControlAgent — top-level coordinator.
Monitor all agent activity, detect anomalies, maintain system health.
Responsibilities:
- Summarize active task states
- Detect stuck or failed agent loops
- Generate dashboard status reports (GREEN/YELLOW/RED)
- Proactively suggest next actions
- Coordinate cross-agent workflows"""


class MissionControlAgent(RuntimeAgent):
    name = "mission_control"
    description = "Monitors all agents, maintains system health, coordinates workflows"
    model_chain = "reasoning"

    def execute_task(self, task) -> str:
        self.log.info("Mission control: %s", task.goal[:80])
        status = self._collect_system_status()

        prompt = f"""Mission Control Status Report
Request: {task.goal}

Current System State:
{json.dumps(status, indent=2)}

Provide:
## Overall Health: GREEN / YELLOW / RED
**Reasoning:**

## Active Agents Summary
## Blocked or Failing Tasks
## Recommended Immediate Actions
## Proactive Suggestions

Format as markdown dashboard report."""

        return self.llm_call(prompt, system=SYSTEM, max_tokens=1500)

    def _collect_system_status(self) -> dict:
        orch_url = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:8091")
        try:
            with urlopen(f"{orch_url}/health", timeout=3) as resp:
                health = json.loads(resp.read())
        except Exception:
            health = {"status": "unreachable"}

        try:
            with urlopen(f"{orch_url}/tasks?limit=20", timeout=3) as resp:
                tasks_data = json.loads(resp.read())
                tasks = tasks_data.get("tasks", [])
        except Exception:
            tasks = []

        running = [t for t in tasks if t.get("status") == "running"]
        failed = [t for t in tasks if t.get("status") == "failed"]
        queued = [t for t in tasks if t.get("status") == "queued"]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "orchestrator": health,
            "tasks": {
                "running": len(running),
                "queued": len(queued),
                "failed": len(failed),
                "failed_details": [{"id": t["id"], "error": t.get("error", "")[:100]} for t in failed[:3]],
            },
        }
