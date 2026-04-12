from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


SLOT_ORDER = ("atlas", "forge", "nexus", "shield", "spark")
TERMINAL_JOB_STATUSES = {"done", "partial", "error", "cancelled"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _duration_seconds(started_at: str | None, finished_at: str | None) -> float | None:
    if not started_at:
        return None
    try:
        start = datetime.fromisoformat(str(started_at))
    except ValueError:
        return None

    if finished_at:
        try:
            end = datetime.fromisoformat(str(finished_at))
        except ValueError:
            end = datetime.now(start.tzinfo or timezone.utc)
    else:
        end = datetime.now(start.tzinfo or timezone.utc)

    duration = (end - start).total_seconds()
    if duration < 0:
        return None
    return round(duration, 3)


def _job_summary(job: dict[str, Any]) -> str:
    result_summary = str(job.get("result_summary") or "").strip()
    if result_summary:
        return result_summary

    agents = job.get("agents")
    if isinstance(agents, dict):
        for slot in SLOT_ORDER:
            agent_state = agents.get(slot)
            if not isinstance(agent_state, dict):
                continue
            output = str(agent_state.get("output") or "").strip()
            if output:
                return output.splitlines()[0][:220]

        for agent_state in agents.values():
            if not isinstance(agent_state, dict):
                continue
            output = str(agent_state.get("output") or "").strip()
            if output:
                return output.splitlines()[0][:220]

    task = str(job.get("task") or "").strip()
    return task[:220]


def _status_bucket(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"running"}:
        return "running"
    if normalized in {"queued", "pending"}:
        return "queued"
    if normalized in {"done"}:
        return "done"
    if normalized in {"partial", "error", "timeout", "cancelled", "failed"}:
        return "failed"
    return "other"


class CodexJobManager:
    ROOT_DIR = Path(__file__).resolve().parent.parent

    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is not None:
            self.ROOT_DIR = Path(root_dir).resolve()
        self._lock = threading.RLock()

    @property
    def queue_path(self) -> Path:
        return self.ROOT_DIR / "state" / "codex-accounts" / "job_queue.json"

    def _empty_payload(self) -> dict[str, Any]:
        return {"jobs": []}

    def _normalize_agent_state(self, raw: Any) -> dict[str, Any]:
        source = raw if isinstance(raw, dict) else {}
        return {
            "status": str(source.get("status") or "pending").strip() or "pending",
            "output": source.get("output"),
            "started_at": source.get("started_at"),
            "finished_at": source.get("finished_at"),
        }

    def _normalize_job(self, raw: Any) -> dict[str, Any] | None:
        if not isinstance(raw, dict):
            return None

        job_id = str(raw.get("id") or "").strip()
        if not job_id:
            return None

        requested_slots = [
            str(slot).strip()
            for slot in (raw.get("requested_slots") or raw.get("requested_agents") or [])
            if str(slot).strip()
        ]
        selected_slots = [
            str(slot).strip()
            for slot in (raw.get("selected_slots") or [])
            if str(slot).strip()
        ]

        agents: dict[str, Any] = {}
        raw_agents = raw.get("agents")
        if isinstance(raw_agents, dict):
            agents = {
                str(slot).strip(): self._normalize_agent_state(state)
                for slot, state in raw_agents.items()
                if str(slot).strip()
            }

        created_at = str(raw.get("created_at") or _now_iso()).strip() or _now_iso()
        finished_at = raw.get("finished_at")
        result_summary = raw.get("result_summary")

        job = {
            "id": job_id,
            "task": str(raw.get("task") or "").strip(),
            "status": str(raw.get("status") or "queued").strip() or "queued",
            "created_at": created_at,
            "finished_at": finished_at,
            "requested_slots": requested_slots,
            "selected_slots": selected_slots,
            "selection": raw.get("selection") if isinstance(raw.get("selection"), dict) else {},
            "result_summary": result_summary,
            "agents": agents,
        }

        if not job["result_summary"]:
            job["result_summary"] = _job_summary(job)

        return job

    def load_payload(self) -> dict[str, Any]:
        with self._lock:
            try:
                if not self.queue_path.exists():
                    return self._empty_payload()
                payload = json.loads(self.queue_path.read_text(encoding="utf-8"))
            except Exception:
                return self._empty_payload()

        jobs = []
        for item in payload.get("jobs", []) if isinstance(payload, dict) else []:
            normalized = self._normalize_job(item)
            if normalized is not None:
                jobs.append(normalized)
        return {"jobs": jobs}

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(self.queue_path.parent),
            suffix=".tmp",
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            temp_path = Path(handle.name)
        temp_path.replace(self.queue_path)

    def save_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized_jobs = []
        for item in payload.get("jobs", []) if isinstance(payload, dict) else []:
            normalized = self._normalize_job(item)
            if normalized is not None:
                normalized_jobs.append(normalized)
        normalized_jobs.sort(key=lambda job: str(job.get("created_at") or ""), reverse=True)
        normalized_payload = {"jobs": normalized_jobs}
        with self._lock:
            self._atomic_write(normalized_payload)
        return normalized_payload

    def load_job_map(self) -> dict[str, dict[str, Any]]:
        payload = self.load_payload()
        return {
            job["id"]: job
            for job in payload.get("jobs", [])
            if isinstance(job, dict) and str(job.get("id") or "").strip()
        }

    def save_job_map(self, jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        payload = {"jobs": list(jobs.values())}
        return self.save_payload(payload)

    def create_job(
        self,
        *,
        task: str,
        status: str = "queued",
        requested_slots: list[str] | None = None,
        selected_slots: list[str] | None = None,
        selection: dict[str, Any] | None = None,
        agents: dict[str, Any] | None = None,
        result_summary: str | None = None,
    ) -> dict[str, Any]:
        job = {
            "id": f"job_{uuid.uuid4().hex[:12]}",
            "task": str(task or "").strip(),
            "status": str(status or "queued").strip() or "queued",
            "created_at": _now_iso(),
            "finished_at": None,
            "requested_slots": requested_slots or [],
            "selected_slots": selected_slots or [],
            "selection": selection or {},
            "result_summary": result_summary,
            "agents": agents or {},
        }
        job = self._normalize_job(job) or job
        jobs = self.load_job_map()
        jobs[job["id"]] = job
        self.save_job_map(jobs)
        return job

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        return self.load_job_map().get(str(job_id or "").strip())

    def update_job(self, job_id: str, status: str | None = None, result: str | None = None, **extra: Any) -> dict[str, Any] | None:
        jobs = self.load_job_map()
        key = str(job_id or "").strip()
        job = jobs.get(key)
        if job is None:
            return None

        if status is not None:
            job["status"] = str(status).strip() or job.get("status", "queued")
            if job["status"] in TERMINAL_JOB_STATUSES and not job.get("finished_at"):
                job["finished_at"] = _now_iso()

        if result is not None:
            job["result_summary"] = str(result).strip() or job.get("result_summary")

        for field, value in extra.items():
            job[field] = value

        normalized = self._normalize_job(job)
        if normalized is None:
            return None
        jobs[key] = normalized
        self.save_job_map(jobs)
        return normalized

    def update_agent_state(self, job_id: str, slot: str, **fields: Any) -> dict[str, Any] | None:
        jobs = self.load_job_map()
        key = str(job_id or "").strip()
        slot_name = str(slot or "").strip()
        job = jobs.get(key)
        if job is None or not slot_name:
            return None

        agents = job.setdefault("agents", {})
        current = self._normalize_agent_state(agents.get(slot_name))
        current.update(fields)
        agents[slot_name] = self._normalize_agent_state(current)
        normalized = self._normalize_job(job)
        if normalized is None:
            return None
        jobs[key] = normalized
        self.save_job_map(jobs)
        return normalized

    def finalize_job(self, job_id: str, status: str, result_summary: str | None = None, **extra: Any) -> dict[str, Any] | None:
        return self.update_job(job_id, status=status, result=result_summary, **extra)

    def list_recent_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        payload = self.load_payload()
        jobs = payload.get("jobs", [])
        recent = jobs[: max(int(limit or 0), 0)]
        normalized_recent: list[dict[str, Any]] = []
        for job in recent:
            duration_seconds = _duration_seconds(
                str(job.get("created_at") or ""),
                str(job.get("finished_at") or "") or None,
            )
            normalized_recent.append(
                {
                    "id": job.get("id"),
                    "status": job.get("status"),
                    "summary": _job_summary(job),
                    "task": job.get("task"),
                    "created_at": job.get("created_at"),
                    "finished_at": job.get("finished_at"),
                    "requested_slots": job.get("requested_slots", []),
                    "selected_slots": job.get("selected_slots", []),
                    "duration_seconds": duration_seconds,
                }
            )
        return normalized_recent

    def get_job_result(self, job_id: str) -> dict[str, Any] | None:
        job = self.get_job(job_id)
        if job is None:
            return None

        result_text = ""
        agents = job.get("agents")
        if isinstance(agents, dict):
            for slot in job.get("selected_slots", []):
                agent_state = agents.get(slot)
                if not isinstance(agent_state, dict):
                    continue
                output = str(agent_state.get("output") or "").strip()
                if output:
                    result_text = output
                    break

            if not result_text:
                for agent_state in agents.values():
                    if not isinstance(agent_state, dict):
                        continue
                    output = str(agent_state.get("output") or "").strip()
                    if output:
                        result_text = output
                        break

        if not result_text:
            result_text = str(job.get("result_summary") or "").strip()

        return {
            "ok": True,
            "job_id": job.get("id"),
            "status": job.get("status"),
            "result": result_text,
            "summary": _job_summary(job),
            "selected_slots": job.get("selected_slots", []),
            "requested_slots": job.get("requested_slots", []),
        }

    def get_queue_stats(self) -> dict[str, Any]:
        payload = self.load_payload()
        jobs = payload.get("jobs", [])
        totals = {"queued": 0, "running": 0, "done": 0, "failed": 0, "other": 0}
        slots: dict[str, dict[str, int]] = {}

        for slot_name in SLOT_ORDER:
            slots[slot_name] = {"queued": 0, "running": 0, "done": 0, "failed": 0, "other": 0, "total": 0}

        for job in jobs:
            bucket = _status_bucket(str(job.get("status") or ""))
            totals[bucket] = totals.get(bucket, 0) + 1
            target_slots = job.get("selected_slots") or job.get("requested_slots") or []
            for slot_name in target_slots:
                slot_key = str(slot_name or "").strip()
                if not slot_key:
                    continue
                slot_stats = slots.setdefault(slot_key, {"queued": 0, "running": 0, "done": 0, "failed": 0, "other": 0, "total": 0})
                slot_stats[bucket] = slot_stats.get(bucket, 0) + 1
                slot_stats["total"] = slot_stats.get("total", 0) + 1

        return {
            "totals": totals,
            "slots": slots,
            "recent": self.list_recent_jobs(limit=10),
        }


_job_manager: CodexJobManager | None = None


def get_job_manager() -> CodexJobManager:
    global _job_manager
    if _job_manager is None:
        _job_manager = CodexJobManager()
    return _job_manager


def load_jobs() -> list[dict[str, Any]]:
    return get_job_manager().load_payload().get("jobs", [])


def load_job_map() -> dict[str, dict[str, Any]]:
    return get_job_manager().load_job_map()


def save_job_map(jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return get_job_manager().save_job_map(jobs)


def create_job(**kwargs: Any) -> dict[str, Any]:
    return get_job_manager().create_job(**kwargs)


def get_job(job_id: str) -> dict[str, Any] | None:
    return get_job_manager().get_job(job_id)


def update_job(job_id: str, status: str | None = None, result: str | None = None, **extra: Any) -> dict[str, Any] | None:
    return get_job_manager().update_job(job_id, status=status, result=result, **extra)


def update_agent_state(job_id: str, slot: str, **fields: Any) -> dict[str, Any] | None:
    return get_job_manager().update_agent_state(job_id, slot, **fields)


def finalize_job(job_id: str, status: str, result_summary: str | None = None, **extra: Any) -> dict[str, Any] | None:
    return get_job_manager().finalize_job(job_id, status=status, result_summary=result_summary, **extra)


def list_recent_jobs(limit: int = 10) -> list[dict[str, Any]]:
    return get_job_manager().list_recent_jobs(limit=limit)


def get_job_result(job_id: str) -> dict[str, Any] | None:
    return get_job_manager().get_job_result(job_id)


def get_queue_stats() -> dict[str, Any]:
    return get_job_manager().get_queue_stats()
