from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


SLOT_ORDER = ("atlas", "forge", "nexus", "shield", "spark")
TERMINAL_JOB_STATUSES = {"done", "failed", "cancelled"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_seconds(started_at: str | None, finished_at: str | None) -> float | None:
    start = _parse_datetime(started_at)
    if start is None:
        return None
    end = _parse_datetime(finished_at) if finished_at else datetime.now(start.tzinfo or timezone.utc)
    if end is None:
        end = datetime.now(start.tzinfo or timezone.utc)
    duration = (end - start).total_seconds()
    if duration < 0:
        return None
    return round(duration, 3)


def _normalize_status(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"queued", "pending"}:
        return "pending"
    if normalized in {"running"}:
        return "running"
    if normalized in {"done", "completed", "success"}:
        return "done"
    if normalized in {"cancelled", "canceled"}:
        return "cancelled"
    if normalized in {"partial", "error", "timeout", "failed"}:
        return "failed"
    return "pending"


def _normalize_priority(value: Any, fallback: int = 5) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(min(parsed, 10), 0)


def _task_dict_from_raw(raw: Any, role: str | None = None) -> dict[str, Any]:
    if isinstance(raw, dict):
        description = str(raw.get("description") or raw.get("task") or raw.get("summary") or "").strip()
        task_type = str(raw.get("type") or role or "any").strip() or "any"
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        return {
            "description": description,
            "type": task_type,
            "payload": payload,
        }
    description = str(raw or "").strip()
    return {"description": description, "type": str(role or "any").strip() or "any", "payload": {}}


def _task_text(task: Any) -> str:
    if isinstance(task, dict):
        return str(task.get("description") or "").strip()
    return str(task or "").strip()


def _job_summary(job: dict[str, Any]) -> str:
    output_summary = str(job.get("output_summary") or job.get("result_summary") or "").strip()
    if output_summary:
        return output_summary

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

    return _task_text(job.get("task"))[:220]


def _status_bucket(status: str) -> str:
    normalized = _normalize_status(status)
    if normalized == "running":
        return "running"
    if normalized == "pending":
        return "queued"
    if normalized == "done":
        return "done"
    if normalized in {"failed", "cancelled"}:
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

    @property
    def jsonl_path(self) -> Path:
        return self.ROOT_DIR / "state" / "codex_jobs.jsonl"

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

        raw_job_id = str(raw.get("job_id") or raw.get("id") or "").strip()
        job_id = raw_job_id or f"job_{uuid.uuid4().hex[:12]}"

        created_at = str(raw.get("created_at") or _now_iso()).strip() or _now_iso()
        updated_at = str(raw.get("updated_at") or created_at).strip() or created_at
        status = _normalize_status(raw.get("status"))
        raw_task = raw.get("task")
        role = str(
            raw.get("role")
            or (raw_task.get("type") if isinstance(raw_task, dict) else None)
            or raw.get("type")
            or "any"
        ).strip() or "any"
        task_source: Any
        if isinstance(raw_task, dict):
            task_source = raw_task
        elif any(key in raw for key in ("description", "summary", "payload", "type", "role")):
            task_source = {
                "description": raw.get("description") or raw.get("summary") or raw.get("task") or "",
                "type": raw.get("type") or role,
                "payload": raw.get("payload") if isinstance(raw.get("payload"), dict) else {},
            }
        else:
            task_source = raw_task
        task = _task_dict_from_raw(task_source, role=role)
        requested_slots = [
            str(slot).strip()
            for slot in (raw.get("requested_slots") or raw.get("requested_agents") or [])
            if str(slot).strip()
        ]
        selected_slots = [
            str(slot).strip()
            for slot in (raw.get("selected_slots") or raw.get("selected_agents") or [])
            if str(slot).strip()
        ]
        slot_id = str(raw.get("slot_id") or (selected_slots[0] if selected_slots else "")).strip() or None
        agents = raw.get("agents") if isinstance(raw.get("agents"), dict) else {}
        normalized_agents = {
            str(slot).strip(): self._normalize_agent_state(value)
            for slot, value in agents.items()
            if str(slot).strip()
        }
        retries = max(int(raw.get("retries") or 0), 0)
        max_retries = max(int(raw.get("max_retries") or 3), 1)
        started_at = raw.get("started_at")
        completed_at = raw.get("completed_at") or raw.get("finished_at")
        failure_reason = raw.get("failure_reason")
        selection = raw.get("selection") if isinstance(raw.get("selection"), dict) else {}
        output_summary = str(raw.get("output_summary") or raw.get("result_summary") or "").strip() or None

        job = {
            "job_id": job_id,
            "id": job_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "status": status,
            "priority": _normalize_priority(raw.get("priority"), fallback=5),
            "role": role,
            "slot_id": slot_id,
            "worktree": str(raw.get("worktree") or "").strip() or None,
            "task": task,
            "retries": retries,
            "max_retries": max_retries,
            "failure_reason": str(failure_reason).strip() if failure_reason else None,
            "started_at": started_at,
            "completed_at": completed_at,
            "finished_at": completed_at,
            "output_summary": output_summary,
            "result_summary": output_summary,
            "selection": selection,
            "requested_slots": requested_slots,
            "selected_slots": selected_slots,
            "agents": normalized_agents,
        }
        if not job["output_summary"]:
            summary = _job_summary(job)
            job["output_summary"] = summary or None
            job["result_summary"] = summary or None
        return job

    def _compat_job(self, job: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_job(job) or {}
        if not normalized:
            return {}
        compat = dict(normalized)
        compat["task"] = _task_text(normalized.get("task"))
        compat["type"] = normalized.get("role")
        compat["summary"] = _job_summary(normalized)
        compat["status"] = normalized.get("status")
        compat["result_summary"] = normalized.get("output_summary")
        compat["finished_at"] = normalized.get("completed_at")
        return compat

    def _read_canonical_job_map(self) -> dict[str, dict[str, Any]]:
        jobs: dict[str, dict[str, Any]] = {}
        if not self.jsonl_path.exists():
            return jobs
        try:
            lines = self.jsonl_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return jobs
        for line in lines:
            raw = str(line or "").strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            normalized = self._normalize_job(payload)
            if normalized is None:
                continue
            jobs[normalized["job_id"]] = normalized
        return jobs

    def _append_job(self, job: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_job(job)
        if normalized is None:
            raise ValueError("Invalid job payload")
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with self.jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(normalized, ensure_ascii=False))
            handle.write("\n")
        self._write_legacy_snapshot(self._read_canonical_job_map())
        return normalized

    def _write_legacy_snapshot(self, jobs: dict[str, dict[str, Any]]) -> None:
        payload = {"jobs": [self._compat_job(job) for job in self._sorted_jobs(jobs.values())]}
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

    def _sorted_jobs(self, jobs: list[dict[str, Any]] | Any) -> list[dict[str, Any]]:
        return sorted(
            [job for job in jobs if isinstance(job, dict)],
            key=lambda job: (
                _normalize_priority(job.get("priority"), fallback=5) * -1,
                str(job.get("created_at") or ""),
                str(job.get("job_id") or job.get("id") or ""),
            ),
        )

    def load_payload(self) -> dict[str, Any]:
        with self._lock:
            jobs = self._read_canonical_job_map()
        return {"jobs": [self._compat_job(job) for job in self._sorted_jobs(list(jobs.values()))]}

    def save_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        jobs = payload.get("jobs") if isinstance(payload, dict) else []
        canonical_jobs: dict[str, dict[str, Any]] = {}
        for item in jobs if isinstance(jobs, list) else []:
            normalized = self._normalize_job(item)
            if normalized is not None:
                canonical_jobs[normalized["job_id"]] = normalized
        with self._lock:
            self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            with self.jsonl_path.open("w", encoding="utf-8") as handle:
                for job in self._sorted_jobs(list(canonical_jobs.values())):
                    handle.write(json.dumps(job, ensure_ascii=False))
                    handle.write("\n")
            self._write_legacy_snapshot(canonical_jobs)
        return {"jobs": [self._compat_job(job) for job in self._sorted_jobs(list(canonical_jobs.values()))]}

    def load_job_map(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {job_id: self._compat_job(job) for job_id, job in self._read_canonical_job_map().items()}

    def save_job_map(self, jobs: dict[str, dict[str, Any]]) -> dict[str, Any]:
        return self.save_payload({"jobs": list(jobs.values())})

    def enqueue(self, job: dict[str, Any]) -> str:
        payload = dict(job)
        payload.setdefault("job_id", f"job_{uuid.uuid4().hex[:12]}")
        payload.setdefault("status", "pending")
        payload.setdefault("priority", 5)
        payload.setdefault("created_at", _now_iso())
        payload["updated_at"] = _now_iso()
        normalized = self._append_job(payload)
        return normalized["job_id"]

    def dequeue(self, role: str | None = None) -> dict[str, Any] | None:
        requested_role = str(role or "").strip().lower()
        with self._lock:
            jobs = self._read_canonical_job_map()
            pending_jobs = [
                job
                for job in self._sorted_jobs(list(jobs.values()))
                if _normalize_status(job.get("status")) == "pending"
                and (not requested_role or str(job.get("role") or "").strip().lower() == requested_role)
            ]
            if not pending_jobs:
                return None
            job = dict(pending_jobs[0])
            now = _now_iso()
            job["status"] = "running"
            job["started_at"] = job.get("started_at") or now
            job["updated_at"] = now
            self._append_job(job)
        return self._compat_job(job)

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
        job_id = self.enqueue(
            {
                "task": {"description": str(task or "").strip(), "type": "any", "payload": {}},
                "status": status,
                "requested_slots": requested_slots or [],
                "selected_slots": selected_slots or [],
                "selection": selection or {},
                "agents": agents or {},
                "output_summary": result_summary,
                "slot_id": (selected_slots or [None])[0],
            }
        )
        return self.get_job(job_id) or {}

    def update_job(self, job_id: str, status: str | None = None, result: str | None = None, **extra: Any) -> dict[str, Any] | None:
        key = str(job_id or "").strip()
        with self._lock:
            jobs = self._read_canonical_job_map()
            current = jobs.get(key)
            if current is None:
                return None
            updated = dict(current)
            if status is not None:
                updated["status"] = _normalize_status(status)
                if updated["status"] == "running" and not updated.get("started_at"):
                    updated["started_at"] = _now_iso()
                if updated["status"] in TERMINAL_JOB_STATUSES and not updated.get("completed_at"):
                    updated["completed_at"] = _now_iso()
                    updated["finished_at"] = updated["completed_at"]
            if result is not None:
                updated["output_summary"] = str(result).strip() or updated.get("output_summary")
                updated["result_summary"] = updated["output_summary"]
            for field, value in extra.items():
                updated[field] = value
            updated["updated_at"] = _now_iso()
            normalized = self._append_job(updated)
        return self._compat_job(normalized)

    def update_agent_state(self, job_id: str, slot: str, **fields: Any) -> dict[str, Any] | None:
        key = str(job_id or "").strip()
        slot_name = str(slot or "").strip()
        with self._lock:
            jobs = self._read_canonical_job_map()
            current = jobs.get(key)
            if current is None or not slot_name:
                return None
            updated = dict(current)
            agents = dict(updated.get("agents") or {})
            agent_state = self._normalize_agent_state(agents.get(slot_name))
            agent_state.update(fields)
            agents[slot_name] = self._normalize_agent_state(agent_state)
            updated["agents"] = agents
            updated["slot_id"] = updated.get("slot_id") or slot_name
            if slot_name not in updated.get("selected_slots", []):
                updated["selected_slots"] = [*updated.get("selected_slots", []), slot_name]
            agent_statuses = {
                str(info.get("status") or "").strip().lower()
                for info in agents.values()
                if isinstance(info, dict)
            }
            if "running" in agent_statuses:
                updated["status"] = "running"
                updated["started_at"] = updated.get("started_at") or _now_iso()
            elif agent_statuses and agent_statuses <= {"done"}:
                updated["status"] = "done"
                updated["completed_at"] = _now_iso()
                updated["finished_at"] = updated["completed_at"]
            elif "cancelled" in agent_statuses and len(agent_statuses) == 1:
                updated["status"] = "cancelled"
                updated["completed_at"] = _now_iso()
                updated["finished_at"] = updated["completed_at"]
            elif any(state in {"error", "timeout", "failed"} for state in agent_statuses):
                updated["status"] = "failed"
                updated["completed_at"] = _now_iso()
                updated["finished_at"] = updated["completed_at"]
            updated["output_summary"] = _job_summary(updated)
            updated["result_summary"] = updated["output_summary"]
            updated["updated_at"] = _now_iso()
            normalized = self._append_job(updated)
        return self._compat_job(normalized)

    def finalize_job(self, job_id: str, status: str, result_summary: str | None = None, **extra: Any) -> dict[str, Any] | None:
        return self.update_job(job_id, status=status, result=result_summary, **extra)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        key = str(job_id or "").strip()
        with self._lock:
            job = self._read_canonical_job_map().get(key)
        return self._compat_job(job) if job is not None else None

    def list_jobs(self, status: str | None = None, slot_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        requested_status = _normalize_status(status) if status else None
        requested_slot = str(slot_id or "").strip().lower()
        requested_limit = max(int(limit or 0), 0)
        if requested_limit == 0:
            return []
        with self._lock:
            jobs = self._sorted_jobs(list(self._read_canonical_job_map().values()))
        filtered: list[dict[str, Any]] = []
        for job in jobs:
            if requested_status and _normalize_status(job.get("status")) != requested_status:
                continue
            if requested_slot and str(job.get("slot_id") or "").strip().lower() != requested_slot:
                continue
            filtered.append(self._compat_job(job))
            if len(filtered) >= requested_limit:
                break
        return filtered

    def list_recent_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        jobs = self.list_jobs(limit=max(int(limit or 0), 0))
        recent: list[dict[str, Any]] = []
        for job in jobs:
            duration_seconds = _duration_seconds(
                str(job.get("started_at") or job.get("created_at") or ""),
                str(job.get("finished_at") or "") or None,
            )
            recent.append(
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
        return recent

    def retry_job(self, job_id: str) -> dict[str, Any] | None:
        key = str(job_id or "").strip()
        with self._lock:
            jobs = self._read_canonical_job_map()
            current = jobs.get(key)
            if current is None:
                return None
            updated = dict(current)
            updated["retries"] = int(updated.get("retries") or 0) + 1
            updated["status"] = "pending"
            updated["failure_reason"] = None
            updated["started_at"] = None
            updated["completed_at"] = None
            updated["finished_at"] = None
            updated["updated_at"] = _now_iso()
            normalized = self._append_job(updated)
        return self._compat_job(normalized)

    def cancel_job(self, job_id: str) -> dict[str, Any] | None:
        return self.update_job(job_id, status="cancelled", completed_at=_now_iso(), finished_at=_now_iso())

    def purge_old_jobs(self, days: int = 7) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(int(days or 0), 0))
        with self._lock:
            jobs = self._read_canonical_job_map()
            kept: dict[str, dict[str, Any]] = {}
            removed = 0
            for job_id, job in jobs.items():
                finished_at = _parse_datetime(job.get("completed_at") or job.get("finished_at"))
                if (
                    _normalize_status(job.get("status")) in TERMINAL_JOB_STATUSES
                    and finished_at is not None
                    and finished_at < cutoff
                ):
                    removed += 1
                    continue
                kept[job_id] = job
            self.save_payload({"jobs": list(kept.values())})
        return removed

    def find_stuck_jobs(self, timeout_minutes: int = 30) -> list[dict[str, Any]]:
        threshold_seconds = max(int(timeout_minutes or 0), 0) * 60
        stuck: list[dict[str, Any]] = []
        for job in self.list_jobs(status="running", limit=500):
            duration = _duration_seconds(
                str(job.get("started_at") or job.get("created_at") or ""),
                None,
            )
            if duration is not None and duration > threshold_seconds:
                stuck.append(job)
        return stuck

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
        jobs = self.list_jobs(limit=500)
        totals = {"queued": 0, "running": 0, "done": 0, "failed": 0, "other": 0}
        slots: dict[str, dict[str, int]] = {
            slot_name: {"queued": 0, "running": 0, "done": 0, "failed": 0, "other": 0, "total": 0}
            for slot_name in SLOT_ORDER
        }
        for job in jobs:
            bucket = _status_bucket(str(job.get("status") or ""))
            totals[bucket] = totals.get(bucket, 0) + 1
            assigned_slots = job.get("selected_slots") or ([job.get("slot_id")] if job.get("slot_id") else [])
            for slot_name in assigned_slots:
                slot_key = str(slot_name or "").strip().lower()
                if not slot_key:
                    continue
                slot_bucket = slots.setdefault(slot_key, {"queued": 0, "running": 0, "done": 0, "failed": 0, "other": 0, "total": 0})
                slot_bucket[bucket] = slot_bucket.get(bucket, 0) + 1
                slot_bucket["total"] = slot_bucket.get("total", 0) + 1
        totals["total"] = len(jobs)
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
