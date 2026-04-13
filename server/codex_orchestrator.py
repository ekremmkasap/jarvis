from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from codex_task_router import ALL_AGENTS, SLOT_ROLES, CodexTaskRouter, normalize_slots, route, split_task

try:
    from account_manager import get_account_manager
except Exception:  # pragma: no cover
    from server.account_manager import get_account_manager  # type: ignore

try:
    from codex_job_manager import get_job_manager, get_job_result as _get_job_result, get_queue_stats as _get_queue_stats, load_job_map
except Exception:  # pragma: no cover
    from server.codex_job_manager import (  # type: ignore
        get_job_manager,
        get_job_result as _get_job_result,
        get_queue_stats as _get_queue_stats,
        load_job_map,
    )

try:
    from codex_quota_tracker import get_all_quotas as _get_all_quotas, get_quota_tracker
except Exception:  # pragma: no cover
    from server.codex_quota_tracker import get_all_quotas as _get_all_quotas, get_quota_tracker  # type: ignore

try:
    from skills.task_bus_hooks import emit_task_bus_event
except Exception:  # pragma: no cover
    try:
        from server.skills.task_bus_hooks import emit_task_bus_event
    except Exception:  # pragma: no cover
        emit_task_bus_event = None  # type: ignore[assignment]


SERVER_DIR = Path(__file__).resolve().parent
ROOT = SERVER_DIR.parent
PROFILES_DIR = SERVER_DIR / "agents" / "profiles"
LOG_DIR = SERVER_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LEGACY_JOBS_FILE = LOG_DIR / "codex_jobs.json"
DISPATCH_AUDIT_PATH = LOG_DIR / "codex_dispatch_audit.jsonl"
COOLDOWN_PATH = ROOT / "state" / "codex_cooldowns.json"

TERMINAL_JOB_STATES = {"done", "failed", "cancelled"}

AGENT_PROFILES: dict[str, str] = {
    "atlas": str(PROFILES_DIR / "atlas.md"),
    "forge": str(PROFILES_DIR / "forge.md"),
    "spark": str(PROFILES_DIR / "spark.md"),
    "shield": str(PROFILES_DIR / "shield.md"),
    "nexus": str(PROFILES_DIR / "nexus.md"),
}

_jobs: dict[str, dict[str, Any]] = load_job_map()
_processes: dict[tuple[str, str], subprocess.Popen[str]] = {}
_lock = threading.RLock()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _parse_datetime(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _job_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:18]


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent), suffix=".tmp") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def _ensure_jobs_loaded() -> None:
    global _jobs
    if _jobs:
        return
    _jobs = load_job_map()


def _refresh_jobs_cache() -> None:
    global _jobs
    _jobs = load_job_map()


def _mirror_jobs_to_legacy_file() -> None:
    try:
        LEGACY_JOBS_FILE.write_text(json.dumps(_jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _sync_job_cache() -> None:
    _refresh_jobs_cache()
    _mirror_jobs_to_legacy_file()


def _load_profile(agent: str) -> str:
    path = AGENT_PROFILES.get(agent)
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return f"Sen {agent.upper()} ajansin. JARVIS projesinde calisiyorsun. Turkce yanit ver."


def _resolve_codex_command() -> list[str]:
    override = os.environ.get("CODEX_CLI_PATH", "").strip()
    candidates: list[str] = [override] if override else []
    if os.name == "nt":
        candidates.extend(candidate for candidate in (shutil.which("codex.cmd"), shutil.which("codex.exe"), shutil.which("codex")) if candidate)
    else:
        path = shutil.which("codex")
        if path:
            candidates.append(path)
    for candidate in candidates:
        if not candidate:
            continue
        if Path(candidate).suffix.lower() == ".ps1":
            continue
        if Path(candidate).exists():
            return [str(Path(candidate))]
    return ["codex"]


def _emit_codex_event(event_name: str, payload: dict[str, Any]) -> None:
    if not callable(emit_task_bus_event):
        return
    try:
        emit_task_bus_event(
            event_name,
            payload,
            to_agent="mission_control",
            from_agent="backend",
            task_type="codex_job",
            policy_check=False,
        )
    except Exception:
        pass


def _clean_codex_output(text: str) -> str:
    if not text:
        return ""
    return "\n".join(line for line in text.splitlines() if "could not update PATH" not in line).strip()


def _load_cooldown_payload() -> dict[str, Any]:
    if not COOLDOWN_PATH.exists():
        return {"slots": {}}
    try:
        payload = json.loads(COOLDOWN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"slots": {}}
    slots = payload.get("slots") if isinstance(payload, dict) else {}
    return {"slots": slots if isinstance(slots, dict) else {}}


def _save_cooldown_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = {"slots": payload.get("slots") if isinstance(payload.get("slots"), dict) else {}}
    _write_json_atomic(COOLDOWN_PATH, normalized)
    return normalized


def get_slot_cooldown_until(slot_id: str) -> datetime | None:
    entry = _load_cooldown_payload().get("slots", {}).get(str(slot_id or "").strip().lower(), {})
    if not isinstance(entry, dict):
        return None
    return _parse_datetime(entry.get("until"))


def get_cooldown_state() -> dict[str, dict[str, Any]]:
    now = _now()
    state: dict[str, dict[str, Any]] = {}
    for slot_id, entry in _load_cooldown_payload().get("slots", {}).items():
        if not isinstance(entry, dict):
            continue
        until = _parse_datetime(entry.get("until"))
        remaining_seconds = max(int((until - now).total_seconds()), 0) if until and until > now else 0
        state[str(slot_id)] = {
            "until": until.isoformat() if until else None,
            "reason": str(entry.get("reason") or "").strip() or None,
            "active": bool(until and until > now),
            "remaining_seconds": remaining_seconds,
        }
    return state


def is_in_cooldown(slot_id: str) -> bool:
    cooldown = get_slot_cooldown_until(slot_id)
    return cooldown is not None and cooldown > _now()


def set_cooldown(slot_id: str, minutes: int = 5, reason: str = "dispatch_backoff") -> dict[str, Any]:
    slot_name = str(slot_id or "").strip().lower()
    payload = _load_cooldown_payload()
    slots = payload.setdefault("slots", {})
    slots[slot_name] = {
        "until": (_now() + timedelta(minutes=max(int(minutes or 0), 0))).isoformat(),
        "reason": str(reason or "dispatch_backoff").strip() or "dispatch_backoff",
    }
    _save_cooldown_payload(payload)
    return get_cooldown_state().get(slot_name, {})


def clear_cooldown(slot_id: str | None = None) -> dict[str, Any]:
    payload = _load_cooldown_payload()
    slots = payload.setdefault("slots", {})
    if slot_id is None:
        slots.clear()
    else:
        slots.pop(str(slot_id or "").strip().lower(), None)
    return _save_cooldown_payload(payload)


def _append_dispatch_audit(entry: dict[str, Any]) -> None:
    DISPATCH_AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DISPATCH_AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False))
        handle.write("\n")


def read_dispatch_audit(limit: int = 50) -> list[dict[str, Any]]:
    if not DISPATCH_AUDIT_PATH.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in DISPATCH_AUDIT_PATH.read_text(encoding="utf-8").splitlines()[-max(int(limit or 0), 0) :]:
        raw = str(line or "").strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def _log_dispatch_decision(
    *,
    job_id: str,
    role: str,
    affinity_chain: list[str],
    selected_slot: str | None,
    reason: str,
    quota_before: dict[str, Any],
    cooldown_state: dict[str, Any],
) -> None:
    _append_dispatch_audit(
        {
            "ts": _now_iso(),
            "job_id": job_id,
            "role": role,
            "affinity_chain": affinity_chain,
            "selected_slot": selected_slot,
            "reason": reason,
            "quota_before": quota_before,
            "cooldown_state": cooldown_state,
        }
    )


def _infer_role_from_task(task_text: str, requested_slots: list[str] | None = None) -> str:
    lower = str(task_text or "").strip().lower()
    if any(keyword in lower for keyword in ("security", "audit", "secret", "redact", "policy", "guvenlik", "güvenlik")):
        return "security"
    if any(keyword in lower for keyword in ("voice", "ses", "tts", "stt", "hologram", "desktop")):
        return "voice"
    if any(keyword in lower for keyword in ("video", "visual", "render", "ui", "frontend", "web", "dashboard")):
        return "video"
    if any(keyword in lower for keyword in ("overflow", "reserve", "backup")):
        return "overflow"
    if any(keyword in lower for keyword in ("core", "manager", "plan", "koordine", "koordin", "yonet", "mimari", "strateji")):
        return "manager"
    if any(keyword in lower for keyword in ("backend", "bridge", "server", "api", "skill", "router", "telegram")):
        return "backend"
    if requested_slots:
        return SLOT_ROLES.get(str(requested_slots[0] or "").strip().lower(), "any")
    return "any"


def _task_text(job: dict[str, Any]) -> str:
    task = job.get("task")
    if isinstance(task, dict):
        return str(task.get("description") or "").strip()
    return str(task or "").strip()


def _job_role(job: dict[str, Any]) -> str:
    return str(job.get("role") or job.get("type") or "any").strip().lower() or "any"


def _resolve_codex_home(slot: str) -> str:
    account_manager = get_account_manager()
    account = account_manager.get_codex_account_by_slot(slot)
    if account and account.codex_home:
        account_manager.mark_used(account.id)
        return account.codex_home
    return str(ROOT / "state" / "codex-accounts" / slot)


def _resolve_execution_context(slot: str) -> dict[str, str]:
    worktree_path = ""
    try:
        from codex_workspace import ensure_worktree, get_worktree_path
    except Exception:
        try:
            from server.codex_workspace import ensure_worktree, get_worktree_path  # type: ignore
        except Exception:
            ensure_worktree = None  # type: ignore[assignment]
            get_worktree_path = None  # type: ignore[assignment]

    if callable(ensure_worktree):
        try:
            worktree_path = str(ensure_worktree(slot))
        except Exception:
            worktree_path = ""
    elif callable(get_worktree_path):
        try:
            worktree_path = str(get_worktree_path(slot))
        except Exception:
            worktree_path = ""

    codex_home = worktree_path or _resolve_codex_home(slot)
    return {"worktree": worktree_path or "", "codex_home": codex_home, "cwd": worktree_path or str(ROOT)}


def _available_slot_pool() -> list[str]:
    account_manager = get_account_manager()
    tracker = get_quota_tracker()
    available: list[str] = []
    for slot in ALL_AGENTS:
        if not account_manager.is_slot_available(slot):
            continue
        if is_in_cooldown(slot):
            continue
        if not tracker.has_quota(slot, estimated_tokens=1):
            continue
        available.append(slot)
    return normalize_slots(available)


def _resolve_slots(requested_slots: list[str]) -> dict[str, Any]:
    account_manager = get_account_manager()
    tracker = get_quota_tracker()
    selection = account_manager.resolve_codex_accounts(requested_slots)
    manager_selected = normalize_slots(selection.get("selected_slots") or requested_slots)
    quota_exhausted = [slot for slot in manager_selected if not tracker.has_quota(slot, estimated_tokens=1)]
    cooldown_blocked = [slot for slot in manager_selected if is_in_cooldown(slot)]
    running_slots = [slot for slot in manager_selected if slot not in quota_exhausted and slot not in cooldown_blocked]
    fallback_slots = normalize_slots(selection.get("fallback_slots") or [])

    if not running_slots and "atlas" in _available_slot_pool():
        running_slots = ["atlas"]
        if "atlas" not in requested_slots:
            fallback_slots = normalize_slots([*fallback_slots, "atlas"])

    if not running_slots:
        for slot in _available_slot_pool():
            running_slots = [slot]
            if slot not in requested_slots:
                fallback_slots = normalize_slots([*fallback_slots, slot])
            break

    return {
        "requested_slots": normalize_slots(requested_slots),
        "selected_slots": normalize_slots(running_slots),
        "account_manager_selected_slots": manager_selected,
        "available_slots": normalize_slots(selection.get("available_slots") or []),
        "unavailable_slots": normalize_slots(selection.get("unavailable_slots") or []),
        "quota_exhausted_slots": normalize_slots(quota_exhausted),
        "cooldown_blocked_slots": normalize_slots(cooldown_blocked),
        "fallback_slots": fallback_slots,
    }


def dispatch(job_id: str, estimated_tokens: int = 1) -> str | None:
    key = str(job_id or "").strip()
    if not key:
        return None

    job_manager = get_job_manager()
    job = job_manager.get_job(key)
    if job is None:
        return None

    role = _job_role(job)
    affinity_chain = CodexTaskRouter().get_fallback_chain(role)
    tracker = get_quota_tracker()
    account_manager = get_account_manager()
    quota_before: dict[str, Any] = {}
    cooldown_state: dict[str, Any] = {}
    selected_slot: str | None = None
    reason = "requeued_no_slot"

    for slot in affinity_chain:
        quota_before[slot] = tracker.get_slot_quota(slot)
        cooldown = get_slot_cooldown_until(slot)
        cooldown_state[slot] = cooldown.isoformat() if cooldown else None
        if not account_manager.is_slot_available(slot):
            reason = f"{slot}_unavailable"
            continue
        if is_in_cooldown(slot):
            reason = f"{slot}_cooldown"
            continue
        if not tracker.has_quota(slot, estimated_tokens=estimated_tokens):
            reason = f"{slot}_quota_exhausted"
            continue
        selected_slot = slot
        reason = "selected"
        break

    if selected_slot is None:
        job_manager.update_job(
            key,
            status="pending",
            failure_reason="no_slot_available",
            dispatch_after=(_now() + timedelta(minutes=5)).isoformat(),
        )
        _sync_job_cache()
        _log_dispatch_decision(
            job_id=key,
            role=role,
            affinity_chain=affinity_chain,
            selected_slot=None,
            reason=reason,
            quota_before=quota_before,
            cooldown_state=cooldown_state,
        )
        return None

    execution = _resolve_execution_context(selected_slot)
    job_manager.update_job(
        key,
        status="running",
        slot_id=selected_slot,
        requested_slots=job.get("requested_slots") or [],
        selected_slots=[selected_slot],
        failure_reason=None,
        worktree=execution.get("worktree") or None,
        dispatch_after=None,
    )
    job_manager.update_agent_state(key, selected_slot, status="running", started_at=_now_iso(), finished_at=None)
    _sync_job_cache()
    _log_dispatch_decision(
        job_id=key,
        role=role,
        affinity_chain=affinity_chain,
        selected_slot=selected_slot,
        reason=reason,
        quota_before=quota_before,
        cooldown_state=cooldown_state,
    )
    return selected_slot


def _spawn_slot_thread(job_id: str, slot_id: str, task_text: str) -> None:
    thread = threading.Thread(target=_run_codex_task, args=(job_id, slot_id, task_text), daemon=True, name=f"codex_{slot_id}_{job_id}")
    thread.start()


def _spawn_swarm_threads(job_id: str, slices: dict[str, str]) -> None:
    for slot_id, task_text in slices.items():
        execution = _resolve_execution_context(slot_id)
        get_job_manager().update_agent_state(job_id, slot_id, status="running", started_at=_now_iso(), finished_at=None)
        get_job_manager().update_job(job_id, status="running", worktree=execution.get("worktree") or None)
        _sync_job_cache()
        _spawn_slot_thread(job_id, slot_id, task_text)


def _failover_job(job_id: str, failed_slot: str, reason: str, task_text: str) -> str | None:
    job_manager = get_job_manager()
    current = job_manager.get_job(job_id)
    if current is None:
        return None

    retries = int(current.get("retries") or 0) + 1
    max_retries = int(current.get("max_retries") or 3)
    if retries > max_retries:
        job_manager.update_job(job_id, status="failed", retries=retries, failure_reason=reason, completed_at=_now_iso(), finished_at=_now_iso())
        _sync_job_cache()
        return None

    set_cooldown(failed_slot, minutes=5, reason=reason)
    role = _job_role(current)
    tried_slots = normalize_slots(current.get("selected_slots") or [])
    fallback_chain = [slot for slot in CodexTaskRouter().get_fallback_chain(role) if slot not in tried_slots and slot != failed_slot]
    tracker = get_quota_tracker()
    account_manager = get_account_manager()
    quota_before: dict[str, Any] = {}
    cooldown_state: dict[str, Any] = {}

    for slot in fallback_chain:
        quota_before[slot] = tracker.get_slot_quota(slot)
        cooldown = get_slot_cooldown_until(slot)
        cooldown_state[slot] = cooldown.isoformat() if cooldown else None
        if not account_manager.is_slot_available(slot):
            continue
        if is_in_cooldown(slot):
            continue
        if not tracker.has_quota(slot, estimated_tokens=1):
            continue

        execution = _resolve_execution_context(slot)
        selected_slots = normalize_slots([*tried_slots, slot])
        job_manager.update_job(
            job_id,
            status="running",
            retries=retries,
            slot_id=slot,
            selected_slots=selected_slots,
            failure_reason=reason,
            worktree=execution.get("worktree") or None,
        )
        job_manager.update_agent_state(job_id, slot, status="running", started_at=_now_iso(), finished_at=None)
        _sync_job_cache()
        _log_dispatch_decision(
            job_id=job_id,
            role=role,
            affinity_chain=fallback_chain,
            selected_slot=slot,
            reason=f"failover_after_{failed_slot}",
            quota_before=quota_before,
            cooldown_state=cooldown_state,
        )
        _spawn_slot_thread(job_id, slot, task_text)
        return slot

    job_manager.update_job(job_id, status="failed", retries=retries, failure_reason=reason, completed_at=_now_iso(), finished_at=_now_iso())
    _sync_job_cache()
    _log_dispatch_decision(
        job_id=job_id,
        role=role,
        affinity_chain=fallback_chain,
        selected_slot=None,
        reason=f"failover_exhausted_after_{failed_slot}",
        quota_before=quota_before,
        cooldown_state=cooldown_state,
    )
    return None


def _run_codex_task(job_id: str, agent: str, task: str) -> None:
    profile = _load_profile(agent)
    full_prompt = f"{profile}\n\n---\n\nGOREV:\n{task}"
    proc: subprocess.Popen[str] | None = None
    last_message_path: str | None = None
    execution = _resolve_execution_context(agent)
    job_manager = get_job_manager()

    get_quota_tracker().record_dispatch(agent)

    try:
        fd, last_message_path = tempfile.mkstemp(prefix=f"codex_{job_id}_{agent}_", suffix=".txt", dir=LOG_DIR)
        os.close(fd)
        env = {**os.environ, "CODEX_HOME": execution["codex_home"]}
        if execution.get("worktree"):
            env["GIT_WORK_TREE"] = execution["worktree"]
        proc = subprocess.Popen(
            [*_resolve_codex_command(), "exec", "--full-auto", "--color", "never", "--output-last-message", last_message_path, full_prompt],
            cwd=execution["cwd"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        with _lock:
            _processes[(job_id, agent)] = proc
        stdout, stderr = proc.communicate(timeout=300)
        last_message = Path(last_message_path).read_text(encoding="utf-8", errors="replace").strip() if last_message_path and Path(last_message_path).exists() else ""
        output = last_message or _clean_codex_output(stdout or "") or _clean_codex_output(stderr or "") or "(cikti yok)"
        status = "done" if proc.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        tail = ""
        if proc is not None:
            proc.kill()
            stdout, stderr = proc.communicate()
            tail = _clean_codex_output(stdout or "") or _clean_codex_output(stderr or "")
        output = "Zaman asimi (300s)"
        if tail:
            output = f"{output}\n\nSon cikti:\n{tail[:1200]}"
        status = "failed"
    except FileNotFoundError:
        output = "codex CLI bulunamadi. Windows icin codex.cmd yolunu veya CODEX_CLI_PATH env degerini kontrol et."
        status = "failed"
    except Exception as exc:
        output = f"Hata: {exc}"
        status = "failed"
    finally:
        with _lock:
            _processes.pop((job_id, agent), None)
        if last_message_path:
            try:
                Path(last_message_path).unlink(missing_ok=True)
            except Exception:
                pass

    get_quota_tracker().record_completion(agent, status)
    job_manager.update_agent_state(job_id, agent, status=status, output=output[:2000], finished_at=_now_iso())
    _sync_job_cache()

    if status != "done":
        failover_slot = _failover_job(job_id, agent, f"{agent}_execution_failed", task)
        if failover_slot is not None:
            _emit_codex_event("codex_slot_failover", {"job_id": job_id, "failed_slot": agent, "selected_slot": failover_slot, "reason": f"{agent}_execution_failed"})
            return

    _emit_codex_event(
        "codex_agent_completed",
        {"job_id": job_id, "agent": agent, "status": status, "task": task[:220], "output": output[:280]},
    )


def dispatch_job(
    task: str,
    *,
    swarm: bool = False,
    requested_slots: list[str] | None = None,
    role: str | None = None,
    priority: int = 5,
) -> dict[str, Any]:
    task_text = str(task or "").strip()
    if not task_text:
        return {"ok": False, "error": "Gorev bos.", "status": "error", "job_id": None}

    requested = normalize_slots(requested_slots or (ALL_AGENTS if swarm else route(task_text)))
    inferred_role = str(role or _infer_role_from_task(task_text, requested)).strip().lower() or "any"
    job_manager = get_job_manager()

    if swarm and len(requested) > 1:
        selection = _resolve_slots(requested)
        selected_slots = normalize_slots(selection.get("selected_slots") or [])
        job_id = job_manager.enqueue(
            {
                "role": inferred_role,
                "priority": priority,
                "requested_slots": requested,
                "selected_slots": selected_slots,
                "status": "running" if selected_slots else "pending",
                "task": {"description": task_text, "type": inferred_role, "payload": {}},
                "failure_reason": None if selected_slots else "no_slot_available",
            }
        )
        if selected_slots:
            _spawn_swarm_threads(job_id, split_task(task_text, selected_slots))
        else:
            job_manager.update_job(job_id, status="pending", dispatch_after=(_now() + timedelta(minutes=5)).isoformat())
            _sync_job_cache()
        return {
            "ok": True,
            "queued": not selected_slots,
            "job_id": job_id,
            "status": "running" if selected_slots else "queued",
            "requested_slots": requested,
            "selected_slots": selected_slots,
            "selection": selection,
            "message": f"Swarm job baslatildi: {job_id}" if selected_slots else f"Job kuyruga alindi: {job_id}",
        }

    job_id = job_manager.enqueue(
        {"role": inferred_role, "priority": priority, "requested_slots": requested, "status": "pending", "task": {"description": task_text, "type": inferred_role, "payload": {}}}
    )
    selected_slot = dispatch(job_id)
    if selected_slot:
        _spawn_slot_thread(job_id, selected_slot, task_text)
    return {
        "ok": True,
        "queued": selected_slot is None,
        "job_id": job_id,
        "status": "running" if selected_slot else "queued",
        "requested_slots": requested,
        "selected_slots": [selected_slot] if selected_slot else [],
        "selection": {"requested_slots": requested, "selected_slots": [selected_slot] if selected_slot else []},
        "message": f"Codex job baslatildi: {job_id} -> {selected_slot.upper()}" if selected_slot else f"Job kuyruga alindi: {job_id}",
    }


def get_status_payload(limit: int = 10) -> dict[str, Any]:
    _sync_job_cache()
    return {
        "jobs": get_job_manager().list_recent_jobs(limit=limit),
        "queue": _get_queue_stats(),
        "quotas": _get_all_quotas(),
        "cooldowns": get_cooldown_state(),
    }


def get_job_result_payload(job_id: str) -> dict[str, Any] | None:
    return _get_job_result(job_id)


def status(job_id: str | None = None) -> str:
    _sync_job_cache()
    if not _jobs:
        return "Henuz Codex job'u yok."
    if job_id:
        job = _jobs.get(str(job_id or "").strip())
        if not job:
            return f"Job bulunamadi: {job_id}"
        return _format_job(job)

    lines = []
    for item in get_job_manager().list_recent_jobs(limit=5):
        job = _jobs.get(str(item.get("id") or "").strip())
        if job:
            lines.append(_format_job(job))
    return "\n\n".join(lines) if lines else "Henuz Codex job'u yok."


def _format_job(job: dict[str, Any]) -> str:
    lines = [f"Job {job['id']} [{str(job.get('status') or '').upper()}]", f"Gorev: {str(job.get('task') or '')[:80]}"]
    requested_slots = job.get("requested_slots") or []
    selected_slots = job.get("selected_slots") or list((job.get("agents") or {}).keys())
    if requested_slots and requested_slots != selected_slots:
        lines.append(f"Istek: {', '.join(slot.upper() for slot in requested_slots)}")
        lines.append(f"Secilen: {', '.join(slot.upper() for slot in selected_slots)}")
    for slot, info in (job.get("agents") or {}).items():
        lines.append(f"  {slot.upper()}: [{str(info.get('status') or '?')}] {str(info.get('output') or '')[:100]}")
    return "\n".join(lines)


def stop_all() -> str:
    _sync_job_cache()
    active_job_ids = [job_id for job_id, job in _jobs.items() if str(job.get("status") or "").strip().lower() == "running"]
    if not active_job_ids:
        return "Aktif Codex job'u yok."

    processes_to_kill: list[subprocess.Popen[str]] = []
    for job_id in active_job_ids:
        job = _jobs[job_id]
        get_job_manager().update_job(job_id, status="cancelled", completed_at=_now_iso(), finished_at=_now_iso(), failure_reason="cancelled_by_operator")
        for agent, info in (job.get("agents") or {}).items():
            if str(info.get("status") or "").strip().lower() in {"pending", "running"}:
                get_job_manager().update_agent_state(job_id, agent, status="cancelled", output=info.get("output") or "Iptal edildi.", finished_at=_now_iso())
            proc = _processes.get((job_id, agent))
            if proc is not None and proc.poll() is None:
                processes_to_kill.append(proc)

    for proc in processes_to_kill:
        try:
            proc.kill()
        except Exception:
            pass

    _sync_job_cache()
    return f"{len(active_job_ids)} job iptal edildi."


def dispatch_text(task: str, swarm: bool = False, requested_slots: list[str] | None = None) -> str:
    return dispatch_job(task, swarm=swarm, requested_slots=requested_slots).get("message", "Codex dispatch tamamlanamadi.")


def dispatch_message(task: str, swarm: bool = False, requested_slots: list[str] | None = None) -> str:
    return dispatch_text(task, swarm=swarm, requested_slots=requested_slots)


def dispatch_compat(task: str, swarm: bool = False, requested_slots: list[str] | None = None) -> str:
    return dispatch_text(task, swarm=swarm, requested_slots=requested_slots)


def dispatch_string(task: str, swarm: bool = False, requested_slots: list[str] | None = None) -> str:
    return dispatch_text(task, swarm=swarm, requested_slots=requested_slots)
