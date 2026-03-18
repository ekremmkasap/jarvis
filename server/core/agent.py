import uuid
import json
import logging
import datetime
from enum import Enum
from pathlib import Path

# --- Logging ---
LOG_DIR = Path("/opt/jarvis/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "agent.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("core.agent")


# --- Task State Machine (j.txt Section 2 & 6.2) ---
class TaskStatus(Enum):
    QUEUED    = "queued"
    PLANNING  = "planning"
    RUNNING   = "running"
    REVIEWING = "reviewing"
    WAITING   = "waiting"
    BLOCKED   = "blocked"
    DONE      = "done"
    FAILED    = "failed"
    CANCELLED = "cancelled"


# --- Task Model (j.txt Section 2) ---
class Task:
    def __init__(self, goal: str, constraints: list = None, inputs: dict = None):
        self.id = str(uuid.uuid4())[:8]
        self.title = goal[:60]
        self.goal = goal
        self.constraints = constraints or []
        self.inputs = inputs or {}
        self.acceptance_criteria = []
        self.status = TaskStatus.QUEUED
        self.plan = []
        self.artifacts = []
        self.events = []
        self.created_at = datetime.datetime.utcnow().isoformat()
        self.result = None

    def transition(self, new_status: TaskStatus, reason: str = ""):
        old = self.status.value
        self.status = new_status
        event = {
            "time": datetime.datetime.utcnow().isoformat(),
            "from": old,
            "to": new_status.value,
            "reason": reason
        }
        self.events.append(event)
        log.info(f"[Task {self.id}] {old} -> {new_status.value} | {reason}")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "goal": self.goal,
            "status": self.status.value,
            "plan": self.plan,
            "artifacts": self.artifacts,
            "events": self.events,
            "result": self.result,
            "created_at": self.created_at,
        }


# --- Sub-Agent Base (j.txt Section 4) ---
class SubAgent:
    def __init__(self, role: str, permissions: list):
        self.role = role
        self.permissions = permissions  # capability-based (j.txt Section 7)

    def can(self, action: str) -> bool:
        return action in self.permissions

    def run(self, task: "Task", context: dict) -> dict:
        raise NotImplementedError


# --- Memory Manager (j.txt Section 3) ---
class MemoryManager:
    MEMORY_DIR = Path("/opt/jarvis/memory")

    def read_project_memory(self) -> str:
        path = self.MEMORY_DIR / "project_memory" / "MEMORY.md"
        return path.read_text() if path.exists() else ""

    def write_project_memory(self, content: str, append: bool = True):
        path = self.MEMORY_DIR / "project_memory" / "MEMORY.md"
        mode = "a" if append else "w"
        with open(path, mode) as f:
            f.write(f"\n---\n{datetime.datetime.utcnow().date()}\n{content}\n")
        log.info("Project memory updated.")

    def save_working_memory(self, task_id: str, data: dict):
        path = self.MEMORY_DIR / "working_memory" / f"{task_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def memory_gate(self, info: str) -> bool:
        """j.txt Section 3 - Memory Gate: only strategic/repeated info gets saved"""
        keywords = [
            "karar", "mimari", "standart", "kural", "tercih", "politika",
            "decision", "architecture", "standard", "rule", "preference"
        ]
        return any(k in info.lower() for k in keywords)


# --- Core Agent / Mission Control (j.txt Section 1-A, 1-B) ---
class CoreAgent:
    """
    Tek karar verici merkez.
    Akis: Intake -> Plan -> Dispatch -> Execute -> Review -> Synthesize -> Memory
    (j.txt Section 6.1)
    """

    def __init__(self):
        self.memory = MemoryManager()
        self.sub_agents: dict[str, SubAgent] = {}
        self.task_history: list[Task] = []
        log.info("CoreAgent initialized.")

    def register_agent(self, agent: SubAgent):
        self.sub_agents[agent.role] = agent
        log.info(f"Sub-agent registered: {agent.role}")

    # --- Policy Gate (j.txt Section 7) ---
    def _policy_check(self, task: Task) -> tuple[bool, str]:
        if not task.goal or len(task.goal.strip()) < 3:
            return False, "Goal too short or empty."
        forbidden = ["rm -rf /", "drop database", "format c:"]
        for pattern in forbidden:
            if pattern in task.goal.lower():
                return False, f"Forbidden pattern detected: {pattern}"
        return True, "ok"

    # --- Quality Gate (j.txt Section 4 - Reviewer) ---
    def _quality_gate(self, result: dict) -> tuple[bool, str]:
        if not result:
            return False, "Empty result"
        if result.get("error"):
            return False, f"Agent error: {result['error']}"
        if not result.get("output"):
            return False, "No output produced"
        return True, "ok"

    # --- Ana Orkestrasyon (j.txt Section 6.1) ---
    def run(self, goal: str, constraints: list = None, inputs: dict = None) -> dict:
        task = Task(goal=goal, constraints=constraints, inputs=inputs)
        self.task_history.append(task)
        log.info(f"New task: [{task.id}] {task.title}")

        # 1. Policy check
        ok, reason = self._policy_check(task)
        if not ok:
            task.transition(TaskStatus.FAILED, reason)
            return {"task_id": task.id, "status": "failed", "reason": reason}

        # 2. PLANNING
        task.transition(TaskStatus.PLANNING, "Starting plan phase")
        plan_result = self._dispatch("planner", task, {"goal": goal})
        if not self._quality_gate(plan_result)[0]:
            task.transition(TaskStatus.FAILED, "Planning failed")
            return {"task_id": task.id, "status": "failed", "reason": plan_result}
        task.plan = plan_result.get("output", [])

        # 3. RUNNING
        task.transition(TaskStatus.RUNNING, "Dispatching to implementer")
        impl_result = self._dispatch("implementer", task, {"plan": task.plan, "inputs": inputs})
        if not self._quality_gate(impl_result)[0]:
            task.transition(TaskStatus.BLOCKED, "Implementation failed")
            return {"task_id": task.id, "status": "blocked", "reason": impl_result}
        task.artifacts.append(impl_result.get("output"))

        # 4. REVIEWING
        task.transition(TaskStatus.REVIEWING, "Quality review")
        review_result = self._dispatch("reviewer", task, {"artifacts": task.artifacts})
        passed, _ = self._quality_gate(review_result)

        # 5. SYNTHESIZE
        final_output = {
            "plan": task.plan,
            "implementation": task.artifacts,
            "review": review_result.get("output"),
            "review_passed": passed,
        }
        task.result = final_output

        # 6. MEMORY UPDATE (j.txt Section 6.1 - Step 8)
        summary = f"Task [{task.id}]: {task.goal[:80]}"
        if self.memory.memory_gate(summary):
            self.memory.write_project_memory(summary)
        self.memory.save_working_memory(task.id, task.to_dict())

        task.transition(TaskStatus.DONE, "All phases complete")
        log.info(f"Task {task.id} completed successfully.")
        return {"task_id": task.id, "status": "done", "result": final_output}

    def _dispatch(self, role: str, task: Task, context: dict) -> dict:
        agent = self.sub_agents.get(role)
        if not agent:
            log.warning(f"No agent registered for role: {role} - skipping")
            return {"output": f"[{role}] not registered, skipped.", "error": None}
        log.info(f"Dispatching to [{role}]")
        try:
            return agent.run(task, context)
        except Exception as e:
            log.error(f"{role} agent error: {e}")
            return {"output": None, "error": str(e)}

    def status(self) -> dict:
        return {
            "registered_agents": list(self.sub_agents.keys()),
            "total_tasks": len(self.task_history),
            "last_tasks": [t.to_dict() for t in self.task_history[-5:]]
        }


if __name__ == "__main__":
    core = CoreAgent()
    print("CoreAgent ready.")
    print("Registered agents:", list(core.sub_agents.keys()))
    print("Run: core.run(goal='...') to start a task.")
