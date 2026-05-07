from __future__ import annotations

from pathlib import Path

from server.codex_autonomous_runner import AutonomousRunner


class _FakeJobManager:
    def __init__(self, jobs: list[dict[str, object]]) -> None:
        self.jobs = {str(job["id"]): dict(job) for job in jobs}

    def list_pending_jobs(self, limit: int = 100) -> list[dict[str, object]]:
        pending = [dict(job) for job in self.jobs.values() if str(job.get("status")) == "pending"]
        return pending[:limit]

    def get_job(self, job_id: str) -> dict[str, object] | None:
        job = self.jobs.get(str(job_id))
        return dict(job) if job is not None else None

    def update_job(self, job_id: str, **fields: object) -> dict[str, object] | None:
        job = self.jobs.get(str(job_id))
        if job is None:
            return None
        job.update(fields)
        return dict(job)

    def update_agent_state(self, job_id: str, slot: str, **fields: object) -> None:
        job = self.jobs[str(job_id)]
        agents = job.setdefault("agents", {})
        assert isinstance(agents, dict)
        state = agents.setdefault(slot, {})
        assert isinstance(state, dict)
        state.update(fields)

    def list_jobs(self, status: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        jobs = [dict(job) for job in self.jobs.values()]
        if status:
            jobs = [job for job in jobs if str(job.get("status")) == status]
        return jobs[:limit]


class _FakeRouter:
    def route_task(self, task: dict[str, object]) -> str:
        payload = task.get("payload", {})
        if isinstance(payload, dict) and payload.get("slot"):
            return str(payload["slot"])
        return "forge"

    def get_fallback_chain(self, role: str) -> list[str]:
        return ["forge", "atlas", "nexus", "shield", "spark"]


def _job(job_id: str, task_type: str, *, slot: str = "forge", description: str | None = None) -> dict[str, object]:
    return {
        "id": job_id,
        "job_id": job_id,
        "status": "pending",
        "role": "backend",
        "task": {
            "description": description or f"{task_type} gorevi",
            "type": task_type,
            "payload": {"slot": slot},
        },
        "requested_slots": [],
        "selected_slots": [],
    }


def test_runner_respects_kill_switch(tmp_path: Path) -> None:
    manager = _FakeJobManager([_job("job-1", "read_file")])
    dispatches: list[tuple[str, str, str]] = []
    runner = AutonomousRunner(
        root_dir=tmp_path,
        job_manager=manager,
        router=_FakeRouter(),
        dispatch_fn=lambda job_id, slot, task_text: dispatches.append((job_id, slot, task_text)),
        slot_available_fn=lambda slot: True,
    )
    runner.kill_switch_path.parent.mkdir(parents=True, exist_ok=True)
    runner.kill_switch_path.write_text("paused", encoding="utf-8")

    runner.tick()

    assert dispatches == []
    assert runner.get_status()["enabled"] is False


def test_allowlist_positive_and_negative_decisions(tmp_path: Path) -> None:
    manager = _FakeJobManager(
        [
            _job("job-allow", "read_file", description="read_file state/codex-accounts/atlas/job_queue.json"),
            _job("job-block", "env_edit", description="edit .env production secret"),
        ]
    )
    dispatches: list[tuple[str, str, str]] = []
    runner = AutonomousRunner(
        root_dir=tmp_path,
        job_manager=manager,
        router=_FakeRouter(),
        dispatch_fn=lambda job_id, slot, task_text: dispatches.append((job_id, slot, task_text)),
        slot_available_fn=lambda slot: True,
    )

    allow_decision = runner.evaluate_job(manager.get_job("job-allow") or {})
    block_decision = runner.evaluate_job(manager.get_job("job-block") or {})

    assert allow_decision["decision"] == "approved"
    assert block_decision["decision"] == "blocked"
    assert ".env" in str(block_decision["reason"])


def test_runner_dispatches_at_most_one_job_per_slot(tmp_path: Path) -> None:
    jobs = []
    slots = ["atlas", "forge", "nexus", "shield", "spark"]
    for index in range(10):
        jobs.append(_job(f"job-{index}", "read_file", slot=slots[index % len(slots)]))

    manager = _FakeJobManager(jobs)
    dispatches: list[tuple[str, str, str]] = []
    runner = AutonomousRunner(
        root_dir=tmp_path,
        job_manager=manager,
        router=_FakeRouter(),
        dispatch_fn=lambda job_id, slot, task_text: dispatches.append((job_id, slot, task_text)),
        slot_available_fn=lambda slot: True,
    )

    runner.tick()

    assert len(dispatches) == 5
    assert len({slot for _, slot, _ in dispatches}) == 5
    assert runner.get_status()["pending"] == 5
