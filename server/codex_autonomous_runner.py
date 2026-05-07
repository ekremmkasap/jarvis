from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Callable

import yaml


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_ALLOWLIST = {
    "auto_approved_task_types": [
        "read_file",
        "list_files",
        "grep",
        "run_tests",
        "check_format",
        "docstring_generation",
    ],
    "blocked_patterns": [
        "git_commit*",
        "git_push*",
        "*deploy*",
        "*.env*",
        "*state/codex-accounts/*/auth.json*",
        "*auth.json*",
    ],
}
TERMINAL_JOB_STATES = {"done", "failed", "cancelled"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AutonomousRunner:
    def __init__(
        self,
        *,
        root_dir: Path | str | None = None,
        job_manager=None,
        router=None,
        dispatch_fn: Callable[[str, str, str], Any] | None = None,
        slot_available_fn: Callable[[str], bool] | None = None,
    ) -> None:
        self.root_dir = Path(root_dir or ROOT_DIR)
        self.config_path = self.root_dir / "config" / "autonomous_allowlist.yml"
        self.kill_switch_path = self.root_dir / "state" / "autonomous_runner.disabled"
        self.log_path = self.root_dir / "server" / "logs" / "autonomous_runner.jsonl"
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()
        self._last_tick = ""
        self._in_flight: dict[str, dict[str, Any]] = {}
        self.job_manager = job_manager
        self.router = router
        self.dispatch_fn = dispatch_fn
        self.slot_available_fn = slot_available_fn

    def _get_job_manager(self):
        if self.job_manager is not None:
            return self.job_manager
        try:
            from codex_job_manager import get_job_manager
        except Exception:
            from server.codex_job_manager import get_job_manager  # type: ignore
        self.job_manager = get_job_manager()
        return self.job_manager

    def _get_router(self):
        if self.router is not None:
            return self.router
        try:
            from codex_task_router import CodexTaskRouter
        except Exception:
            from server.codex_task_router import CodexTaskRouter  # type: ignore
        self.router = CodexTaskRouter()
        return self.router

    def _default_slot_available(self, slot: str) -> bool:
        try:
            from account_manager import get_account_manager
        except Exception:
            from server.account_manager import get_account_manager  # type: ignore
        return get_account_manager().is_slot_available(slot)

    def _is_slot_available(self, slot: str) -> bool:
        checker = self.slot_available_fn or self._default_slot_available
        return bool(checker(str(slot or "").strip().lower()))

    def _default_dispatch(self, job_id: str, slot: str, task_text: str) -> Any:
        try:
            import codex_orchestrator as codex_orchestrator_module
        except Exception:
            import server.codex_orchestrator as codex_orchestrator_module  # type: ignore
        return codex_orchestrator_module._spawn_slot_thread(job_id, slot, task_text)

    def _dispatch(self, job_id: str, slot: str, task_text: str) -> Any:
        handler = self.dispatch_fn or self._default_dispatch
        return handler(job_id, slot, task_text)

    def _load_allowlist(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return dict(DEFAULT_ALLOWLIST)
        try:
            payload = yaml.safe_load(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return dict(DEFAULT_ALLOWLIST)
        if not isinstance(payload, dict):
            return dict(DEFAULT_ALLOWLIST)
        return {
            "auto_approved_task_types": list(payload.get("auto_approved_task_types") or DEFAULT_ALLOWLIST["auto_approved_task_types"]),
            "blocked_patterns": list(payload.get("blocked_patterns") or DEFAULT_ALLOWLIST["blocked_patterns"]),
        }

    def _append_decision(self, payload: dict[str, Any]) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")

    def recent_decisions(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        decisions: list[dict[str, Any]] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines()[-max(int(limit or 0), 0) :]:
            raw = str(line or "").strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                decisions.append(payload)
        return decisions

    def evaluate_job(self, job: dict[str, Any]) -> dict[str, Any]:
        allowlist = self._load_allowlist()
        task = job.get("task") if isinstance(job.get("task"), dict) else {}
        description = str(task.get("description") or job.get("task") or "").strip()
        task_type = str(task.get("type") or job.get("role") or "").strip().lower()
        text = f"{task_type} {description}".lower()

        for pattern in allowlist["blocked_patterns"]:
            normalized = str(pattern or "").strip().lower()
            if fnmatch(text, normalized) or fnmatch(description.lower(), normalized) or fnmatch(task_type, normalized):
                return {"decision": "blocked", "reason": normalized}

        if task_type in {str(item).strip().lower() for item in allowlist["auto_approved_task_types"]}:
            return {"decision": "approved", "reason": task_type}

        return {"decision": "blocked", "reason": "approval-required"}

    def _reap_in_flight(self) -> None:
        manager = self._get_job_manager()
        finished: list[str] = []
        for job_id, info in self._in_flight.items():
            current = manager.get_job(job_id)
            if current is None:
                finished.append(job_id)
                continue
            status = str(current.get("status") or "").strip().lower()
            if status in TERMINAL_JOB_STATES:
                finished.append(job_id)
        for job_id in finished:
            self._in_flight.pop(job_id, None)

    def _select_slot(self, job: dict[str, Any], busy_slots: set[str]) -> str | None:
        router = self._get_router()
        task = job.get("task") if isinstance(job.get("task"), dict) else {}
        preferred = ""
        try:
            preferred = str(router.route_task(task) or "").strip().lower()
        except Exception:
            preferred = ""
        role = str(job.get("role") or task.get("type") or "any").strip().lower()
        chain: list[str] = []
        if preferred:
            chain.append(preferred)
        try:
            chain.extend(router.get_fallback_chain(role))
        except Exception:
            pass
        seen: set[str] = set()
        for slot in chain:
            slot_name = str(slot or "").strip().lower()
            if not slot_name or slot_name in seen:
                continue
            seen.add(slot_name)
            if slot_name in busy_slots:
                continue
            if self._is_slot_available(slot_name):
                return slot_name
        return None

    def tick(self) -> list[str]:
        with self._lock:
            self._last_tick = _now_iso()
            self._reap_in_flight()
            if self.kill_switch_path.exists():
                self._append_decision({"ts": self._last_tick, "decision": "paused"})
                return []

            manager = self._get_job_manager()
            pending_jobs = manager.list_pending_jobs(limit=100)
            busy_slots = {str(info.get("slot") or "").strip().lower() for info in self._in_flight.values()}
            dispatched: list[str] = []

            for job in pending_jobs:
                job_id = str(job.get("id") or job.get("job_id") or "").strip()
                decision = self.evaluate_job(job)
                if decision["decision"] != "approved":
                    self._append_decision(
                        {
                            "ts": self._last_tick,
                            "job_id": job_id,
                            "decision": decision["decision"],
                            "reason": decision["reason"],
                        }
                    )
                    continue

                slot = self._select_slot(job, busy_slots)
                if not slot:
                    continue

                task = job.get("task") if isinstance(job.get("task"), dict) else {}
                task_text = str(task.get("description") or job.get("task") or "").strip()
                manager.update_job(
                    job_id,
                    status="running",
                    slot_id=slot,
                    selected_slots=[slot],
                    failure_reason=None,
                )
                manager.update_agent_state(job_id, slot, status="running", started_at=self._last_tick, finished_at=None)
                self._in_flight[job_id] = {"slot": slot, "started_at": self._last_tick}
                busy_slots.add(slot)
                self._dispatch(job_id, slot, task_text)
                self._append_decision(
                    {
                        "ts": self._last_tick,
                        "job_id": job_id,
                        "slot": slot,
                        "decision": "dispatched",
                    }
                )
                dispatched.append(job_id)

            return dispatched

    def get_status(self) -> dict[str, Any]:
        manager = self._get_job_manager()
        pending = len(manager.list_pending_jobs(limit=500))
        return {
            "enabled": not self.kill_switch_path.exists(),
            "in_flight": dict(self._in_flight),
            "pending": pending,
            "last_tick": self._last_tick,
            "recent_decisions": self.recent_decisions(limit=10),
        }

    def pause(self) -> dict[str, Any]:
        self.kill_switch_path.parent.mkdir(parents=True, exist_ok=True)
        self.kill_switch_path.write_text("paused", encoding="utf-8")
        return self.get_status()

    def resume(self) -> dict[str, Any]:
        self.kill_switch_path.unlink(missing_ok=True)
        return self.get_status()

    def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(10)

    def start_background(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_forever,
                daemon=True,
                name="codex-autonomous-runner",
            )
            self._thread.start()
            return True


_RUNNER: AutonomousRunner | None = None


def get_runner() -> AutonomousRunner:
    global _RUNNER
    if _RUNNER is None:
        _RUNNER = AutonomousRunner()
    return _RUNNER


def start_background() -> bool:
    return get_runner().start_background()


def get_status_payload() -> dict[str, Any]:
    return get_runner().get_status()


def pause_runner() -> dict[str, Any]:
    return get_runner().pause()


def resume_runner() -> dict[str, Any]:
    return get_runner().resume()
