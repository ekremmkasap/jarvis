import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CORE_DIR = BASE_DIR / "core"
AGENTS_DIR = BASE_DIR / "agents"

for path in (CORE_DIR, AGENTS_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from agent import Task, TaskStatus  # noqa: E402
from builder_agent import BuilderAgent  # noqa: E402
from guard_agent import GuardAgent  # noqa: E402
from planner_agent import PlannerAgent  # noqa: E402
from research_agent import ResearchAgent  # noqa: E402
from synthesizer_agent import SynthesizerAgent  # noqa: E402

log = logging.getLogger("team.orchestrator")


class TeamOrchestrator:
    def __init__(self, llm_call, config_path: Path | None = None):
        self.llm_call = llm_call
        self.config_path = config_path or (BASE_DIR / "config" / "team_config.json")
        self.config = self._load_config()
        self.llm_timeout_seconds = int(self.config.get("llm_timeout_seconds", 25))
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.audit_path = BASE_DIR / "logs" / "team_audit.jsonl"
        self.memory_path = BASE_DIR / "memory" / "working_memory" / "team_tasks.jsonl"
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

        agent_cfg = self.config["agents"]
        self.planner = PlannerAgent(self._safe_llm_call, agent_cfg["planner"])
        self.builder = BuilderAgent(self._safe_llm_call, agent_cfg["builder"])
        self.guard = GuardAgent(self._safe_llm_call, agent_cfg["guard"])
        self.research = ResearchAgent(self._safe_llm_call, agent_cfg["research"])
        self.synthesizer = SynthesizerAgent(self._safe_llm_call, agent_cfg["synthesizer"])

    def run(self, goal: str, chat_id: str = "0", constraints: list | None = None, inputs: dict | None = None) -> dict:
        task = Task(goal=goal, constraints=constraints or [], inputs=inputs or {})
        task_type = self._classify_goal(goal)
        inputs = inputs or {}
        context_packet = inputs.get("context_packet", "")
        departments = inputs.get("departments", [])
        events = []
        attempts = 0
        review_feedback = ""
        research_result = None

        def record(phase: str, detail: str, data: dict | None = None):
            event = {
                "time": datetime.utcnow().isoformat(),
                "task_id": task.id,
                "phase": phase,
                "detail": detail,
            }
            if data:
                event["data"] = data
            events.append(event)
            self._append_jsonl(self.audit_path, event)

        record("queued", "team workflow accepted", {"task_type": task_type, "chat_id": str(chat_id)})
        task.transition(TaskStatus.PLANNING, "team planning started")

        plan_result = self.planner.run(
            task,
            {
                "goal": goal,
                "task_type": task_type,
                "context_packet": context_packet,
                "departments": departments,
            },
        )
        if plan_result.get("error"):
            task.transition(TaskStatus.FAILED, "planner failed")
            return self._finalize_failure(task, events, "planner_failed", plan_result)

        plan_payload = plan_result["output"]
        task.plan = plan_payload.get("plan", [])
        acceptance = plan_payload.get("acceptance", [])
        risks = plan_payload.get("risks", [])
        record("planning", "plan created", {"steps": len(task.plan), "acceptance": len(acceptance)})

        if self._should_run_research(goal, task_type):
            research_result = self.research.run(task, {"task_type": task_type})
            record("research", "research completed", {"enabled": True})
        else:
            record("research", "research skipped", {"enabled": False})

        builder_result = None
        guard_result = None
        max_review_loops = int(self.config.get("max_review_loops", 2))

        while attempts < max_review_loops:
            attempts += 1
            task.transition(TaskStatus.RUNNING, f"builder pass {attempts}")
            builder_result = self.builder.run(
                task,
                {
                    "plan": task.plan,
                    "acceptance": acceptance,
                    "review_feedback": review_feedback,
                    "task_type": task_type,
                    "context_packet": context_packet,
                    "departments": departments,
                },
            )
            if builder_result.get("error"):
                task.transition(TaskStatus.BLOCKED, "builder failed")
                return self._finalize_failure(task, events, "builder_failed", builder_result)

            record("builder", "builder completed", {"attempt": attempts})
            task.artifacts = [builder_result["output"]]

            task.transition(TaskStatus.REVIEWING, f"guard review {attempts}")
            guard_result = self.guard.run(
                task,
                {
                    "implementation": builder_result["output"],
                    "plan": task.plan,
                    "task_type": task_type,
                    "context_packet": context_packet,
                    "departments": departments,
                },
            )
            if guard_result.get("error"):
                task.transition(TaskStatus.BLOCKED, "guard failed")
                return self._finalize_failure(task, events, "guard_failed", guard_result)

            severity_counts = guard_result.get("meta", {}).get("severity_counts", {})
            record("guard", "guard completed", {"attempt": attempts, "severity": severity_counts})
            if guard_result.get("passed"):
                break
            review_feedback = guard_result.get("output", "")

        passed = bool(guard_result and guard_result.get("passed"))
        if not passed:
            task.transition(TaskStatus.BLOCKED, "guard did not approve within retry budget")
        else:
            task.transition(TaskStatus.DONE, "team workflow completed")

        synthesis = self.synthesizer.run(
            task,
            {
                "plan": task.plan,
                "acceptance": acceptance,
                "implementation": builder_result.get("output") if builder_result else "",
                "review": guard_result.get("output") if guard_result else "",
                "research": research_result.get("output") if research_result else "",
                "attempts": attempts,
                "context_packet": context_packet,
                "departments": departments,
            },
        )
        final_output = {
            "task_id": task.id,
            "status": task.status.value,
            "task_type": task_type,
            "plan": task.plan,
            "acceptance": acceptance,
            "risks": risks,
            "builder": builder_result.get("output") if builder_result else "",
            "guard": guard_result.get("output") if guard_result else "",
            "guard_passed": passed,
            "research": research_result.get("output") if research_result else "",
            "synthesis": synthesis.get("output", "") if synthesis else "",
            "attempts": attempts,
            "departments": departments,
            "context_packet": context_packet,
            "events": events,
        }
        task.result = final_output
        self._append_jsonl(self.memory_path, final_output)
        return final_output

    def _load_config(self) -> dict:
        with open(self.config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _append_jsonl(self, path: Path, payload: dict):
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _safe_llm_call(self, model: str, messages: list, system: str | None = None) -> str:
        future = self.executor.submit(self.llm_call, model, messages, system)
        try:
            return future.result(timeout=self.llm_timeout_seconds)
        except FutureTimeout as exc:
            future.cancel()
            raise TimeoutError(f"team llm timeout after {self.llm_timeout_seconds}s") from exc

    def _finalize_failure(self, task: Task, events: list, reason: str, data: dict) -> dict:
        payload = {
            "task_id": task.id,
            "status": task.status.value,
            "reason": reason,
            "result": data,
            "events": events,
        }
        self._append_jsonl(self.memory_path, payload)
        return payload

    def _classify_goal(self, goal: str) -> str:
        lower = goal.lower()
        for task_type, keywords in self.config.get("task_type_keywords", {}).items():
            if any(keyword in lower for keyword in keywords):
                return task_type
        return "general"

    def _should_run_research(self, goal: str, task_type: str) -> bool:
        if task_type in self.config.get("always_research_for", []):
            return True
        lower = goal.lower()
        return any(keyword in lower for keyword in self.config.get("research_keywords", []))
