from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from codex_task_router import ALL_AGENTS, normalize_slots, route, split_task

try:
    from account_manager import get_account_manager
except Exception:  # pragma: no cover
    from server.account_manager import get_account_manager

try:
    from codex_job_manager import (
        get_job_manager,
        get_job_result as _get_job_result,
        get_queue_stats as _get_queue_stats,
        load_job_map,
    )
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

AGENT_PROFILES: dict[str, str] = {
    "atlas": str(PROFILES_DIR / "atlas.md"),
    "forge": str(PROFILES_DIR / "forge.md"),
    "spark": str(PROFILES_DIR / "spark.md"),
    "shield": str(PROFILES_DIR / "shield.md"),
    "nexus": str(PROFILES_DIR / "nexus.md"),
}

TERMINAL_AGENT_STATES = {"done", "error", "timeout", "cancelled"}
TERMINAL_JOB_STATES = {"done", "partial", "error", "cancelled"}

_jobs: dict[str, dict[str, Any]] = load_job_map()
_processes: dict[tuple[str, str], subprocess.Popen[str]] = {}
_lock = threading.RLock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:18]


def _mirror_jobs_to_legacy_file() -> None:
    try:
        LEGACY_JOBS_FILE.write_text(
            json.dumps(_jobs, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _save_jobs() -> None:
    get_job_manager().save_job_map(_jobs)
    _mirror_jobs_to_legacy_file()


def _ensure_jobs_loaded() -> None:
    global _jobs
    if _jobs:
        return
    _jobs = load_job_map()


def _load_profile(agent: str) -> str:
    path = AGENT_PROFILES.get(agent)
    if path and Path(path).exists():
        return Path(path).read_text(encoding="utf-8")
    return f"Sen {agent.upper()} ajansin. JARVIS projesinde calisiyorsun. Turkce yanit ver."


def _resolve_codex_command() -> list[str]:
    override = os.environ.get("CODEX_CLI_PATH", "").strip()
    candidates: list[str] = [override] if override else []

    if os.name == "nt":
        candidates.extend(
            candidate
            for candidate in (shutil.which("codex.cmd"), shutil.which("codex.exe"), shutil.which("codex"))
            if candidate
        )
    else:
        path = shutil.which("codex")
        if path:
            candidates.append(path)

    for candidate in candidates:
        suffix = Path(candidate).suffix.lower()
        if suffix == ".ps1":
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
    cleaned_lines = [line for line in text.splitlines() if "could not update PATH" not in line]
    return "\n".join(cleaned_lines).strip()


def _resolve_codex_home(slot: str) -> str:
    account_manager = get_account_manager()
    account = account_manager.get_codex_account_by_slot(slot)
    if account and account.codex_home:
        account_manager.mark_used(account.id)
        return account.codex_home
    return str(ROOT / "state" / "codex-accounts" / slot)


def _selection_without_accounts(selection: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in selection.items() if key != "accounts"}


def _first_nonempty_output(job: dict[str, Any]) -> str:
    agents = job.get("agents")
    if not isinstance(agents, dict):
        return ""

    for slot in job.get("selected_slots", []):
        agent_state = agents.get(slot)
        if not isinstance(agent_state, dict):
            continue
        output = str(agent_state.get("output") or "").strip()
        if output:
            return output

    for agent_state in agents.values():
        if not isinstance(agent_state, dict):
            continue
        output = str(agent_state.get("output") or "").strip()
        if output:
            return output
    return ""


def _summarize_job(job: dict[str, Any]) -> str:
    output = _first_nonempty_output(job)
    if output:
        return output.splitlines()[0][:220]
    return str(job.get("task") or "").strip()[:220]


def _refresh_job_status(job_id: str) -> None:
    job = _jobs[job_id]
    agents = job.get("agents", {})
    if not agents:
        return

    statuses = {str(info.get("status", "?")).strip().lower() for info in agents.values() if isinstance(info, dict)}
    if not statuses:
        return

    if statuses <= TERMINAL_AGENT_STATES:
        job["finished_at"] = _now_iso()
        if "cancelled" in statuses:
            job["status"] = "cancelled"
        elif statuses <= {"error", "timeout"}:
            job["status"] = "error"
        elif statuses == {"done"}:
            job["status"] = "done"
        else:
            job["status"] = "partial"
        job["result_summary"] = _summarize_job(job)


def _available_slot_pool() -> list[str]:
    account_manager = get_account_manager()
    available: list[str] = []
    for account in account_manager.get_all_accounts("codex"):
        slot = str(account.runtime_slot or "").strip()
        if slot:
            available.append(slot)
    return normalize_slots(available)


def _resolve_slots(requested_slots: list[str]) -> dict[str, Any]:
    account_manager = get_account_manager()
    quota_tracker = get_quota_tracker()

    selection = account_manager.resolve_codex_accounts(requested_slots)
    manager_selected = normalize_slots(selection.get("selected_slots") or requested_slots)
    quota_exhausted = [slot for slot in manager_selected if quota_tracker.is_exhausted(slot)]
    running_slots = [slot for slot in manager_selected if slot not in quota_exhausted]
    fallback_slots = normalize_slots(selection.get("fallback_slots") or [])

    if not running_slots and "atlas" in _available_slot_pool() and not quota_tracker.is_exhausted("atlas"):
        running_slots = ["atlas"]
        if "atlas" not in requested_slots:
            fallback_slots = normalize_slots([*fallback_slots, "atlas"])

    if not running_slots:
        for slot in _available_slot_pool():
            if quota_tracker.is_exhausted(slot):
                continue
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
        "fallback_slots": fallback_slots,
    }


def _spawn_agent_threads(job_id: str, slices: dict[str, str], cwd: str) -> None:
    for agent, sub_task in slices.items():
        get_quota_tracker().record_dispatch(agent)
        thread = threading.Thread(
            target=_run_codex_task,
            args=(job_id, agent, sub_task, cwd),
            daemon=True,
            name=f"codex_{agent}_{job_id}",
        )
        thread.start()


def _run_codex_task(job_id: str, agent: str, task: str, cwd: str) -> None:
    profile = _load_profile(agent)
    full_prompt = f"{profile}\n\n---\n\nGOREV:\n{task}"
    proc: subprocess.Popen[str] | None = None
    last_message_path: str | None = None

    with _lock:
        _ensure_jobs_loaded()
        job = _jobs.get(job_id)
        if job is None:
            return
        agent_state = job.setdefault("agents", {}).setdefault(
            agent,
            {"status": "pending", "output": None, "started_at": None, "finished_at": None},
        )
        if agent_state["status"] == "cancelled":
            agent_state["finished_at"] = _now_iso()
            _refresh_job_status(job_id)
            _save_jobs()
            return

        agent_state["status"] = "running"
        agent_state["started_at"] = _now_iso()
    _save_jobs()

    try:
        fd, last_message_path = tempfile.mkstemp(
            prefix=f"codex_{job_id}_{agent}_",
            suffix=".txt",
            dir=LOG_DIR,
        )
        os.close(fd)

        agent_codex_home = _resolve_codex_home(agent)
        env = {**os.environ, "CODEX_HOME": agent_codex_home}

        proc = subprocess.Popen(
            [
                *_resolve_codex_command(),
                "exec",
                "--full-auto",
                "--color",
                "never",
                "--output-last-message",
                last_message_path,
                full_prompt,
            ],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        with _lock:
            _processes[(job_id, agent)] = proc

        stdout, stderr = proc.communicate(timeout=300)
        last_message = ""
        if last_message_path and Path(last_message_path).exists():
            last_message = Path(last_message_path).read_text(encoding="utf-8", errors="replace").strip()

        output = last_message or _clean_codex_output(stdout or "") or _clean_codex_output(stderr or "") or "(cikti yok)"
        status = "done" if proc.returncode == 0 else "error"
    except subprocess.TimeoutExpired:
        tail = ""
        if proc is not None:
            proc.kill()
            stdout, stderr = proc.communicate()
            tail = _clean_codex_output(stdout or "") or _clean_codex_output(stderr or "")
        output = "Zaman asimi (300s)"
        if tail:
            output = f"{output}\n\nSon cikti:\n{tail[:1200]}"
        status = "timeout"
    except FileNotFoundError:
        output = "codex CLI bulunamadi. Windows icin codex.cmd yolunu veya CODEX_CLI_PATH env degerini kontrol et."
        status = "error"
    except Exception as exc:
        output = f"Hata: {exc}"
        status = "error"
    finally:
        with _lock:
            _processes.pop((job_id, agent), None)
        if last_message_path:
            try:
                Path(last_message_path).unlink(missing_ok=True)
            except Exception:
                pass

    get_quota_tracker().record_completion(agent, status)
    completed_job_event: dict[str, Any] | None = None

    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return

        previous_job_status = job.get("status", "running")
        agent_state = job.setdefault("agents", {}).setdefault(agent, {})
        if agent_state.get("status") == "cancelled":
            agent_state["output"] = agent_state.get("output") or "Iptal edildi."
        else:
            agent_state["status"] = status
            agent_state["output"] = output[:2000]
        agent_state["finished_at"] = _now_iso()
        _refresh_job_status(job_id)

        if previous_job_status == "running" and job.get("status") in TERMINAL_JOB_STATES:
            completed_job_event = {
                "job_id": job_id,
                "task": str(job.get("task") or "")[:240],
                "status": job.get("status", "unknown"),
                "requested_agents": job.get("requested_slots", []),
                "selected_agents": job.get("selected_slots", []),
                "selection": job.get("selection", {}),
            }
    _save_jobs()

    _emit_codex_event(
        "codex_agent_completed",
        {
            "job_id": job_id,
            "agent": agent,
            "status": status,
            "task": task[:220],
            "output": output[:280],
        },
    )
    if completed_job_event:
        _emit_codex_event("codex_job_completed", completed_job_event)


def dispatch_job(
    task: str,
    *,
    swarm: bool = False,
    requested_slots: list[str] | None = None,
) -> dict[str, Any]:
    task_text = str(task or "").strip()
    if not task_text:
        return {"ok": False, "error": "Gorev bos.", "status": "error", "job_id": None}

    requested = normalize_slots(requested_slots or (ALL_AGENTS if swarm else route(task_text)))
    selection = _resolve_slots(requested)
    selected_slots = normalize_slots(selection.get("selected_slots") or [])
    selection_meta = _selection_without_accounts(selection)

    job_id = _job_id()
    job = {
        "id": job_id,
        "task": task_text,
        "status": "queued" if not selected_slots else "running",
        "created_at": _now_iso(),
        "finished_at": _now_iso() if not selected_slots else None,
        "requested_slots": requested,
        "selected_slots": selected_slots,
        "selection": selection_meta,
        "result_summary": "Uygun Codex slot'u yok; gorev kuyrukta bekliyor." if not selected_slots else None,
        "agents": {
            slot: {"status": "pending", "output": None, "started_at": None, "finished_at": None}
            for slot in selected_slots
        },
    }

    with _lock:
        _jobs[job_id] = job
    _save_jobs()

    _emit_codex_event(
        "codex_job_started",
        {
            "job_id": job_id,
            "task": task_text[:240],
            "swarm": swarm,
            "requested_agents": requested,
            "selected_agents": selected_slots,
            "selection": selection_meta,
        },
    )

    if not selected_slots:
        return {
            "ok": True,
            "queued": True,
            "job_id": job_id,
            "status": "queued",
            "requested_slots": requested,
            "selected_slots": [],
            "selection": selection_meta,
            "message": f"Job kuyruga alindi: {job_id}",
        }

    slices = split_task(task_text, selected_slots)
    _spawn_agent_threads(job_id, slices, str(ROOT))

    lines = [
        "Codex Orchestrator baslatildi!",
        f"Job ID: {job_id}",
        f"Istenen slot'lar: {', '.join(slot.upper() for slot in requested)}",
        f"Calisan slot'lar: {', '.join(slot.upper() for slot in selected_slots)}",
    ]
    if selection_meta.get("fallback_slots"):
        lines.append(f"Fallback slot'lar: {', '.join(slot.upper() for slot in selection_meta['fallback_slots'])}")
    if selection_meta.get("quota_exhausted_slots"):
        lines.append(f"Quota nedeniyle pas gecilen: {', '.join(slot.upper() for slot in selection_meta['quota_exhausted_slots'])}")
    if selection_meta.get("unavailable_slots"):
        lines.append(f"Hazir olmayan slot'lar: {', '.join(slot.upper() for slot in selection_meta['unavailable_slots'])}")
    lines.append("Durum icin: /codex-durum")

    return {
        "ok": True,
        "queued": False,
        "job_id": job_id,
        "status": "running",
        "requested_slots": requested,
        "selected_slots": selected_slots,
        "selection": selection_meta,
        "message": "\n".join(lines),
    }


def dispatch(task: str, swarm: bool = False, requested_slots: list[str] | None = None) -> str:
    return dispatch_job(task, swarm=swarm, requested_slots=requested_slots).get("message", "Codex dispatch tamamlanamadi.")


def get_status_payload(limit: int = 10) -> dict[str, Any]:
    _ensure_jobs_loaded()
    queue_stats = _get_queue_stats()
    return {
        "jobs": get_job_manager().list_recent_jobs(limit=limit),
        "queue": queue_stats,
        "quotas": _get_all_quotas(),
    }


def get_job_result_payload(job_id: str) -> dict[str, Any] | None:
    return _get_job_result(job_id)


def status(job_id: str | None = None) -> str:
    _ensure_jobs_loaded()
    if not _jobs:
        return "Henuz Codex job'u yok."

    if job_id:
        job = _jobs.get(str(job_id or "").strip())
        if not job:
            return f"Job bulunamadi: {job_id}"
        return _format_job(job)

    recent = get_job_manager().list_recent_jobs(limit=5)
    lines = []
    for item in recent:
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
    selection = job.get("selection") or {}
    if selection.get("quota_exhausted_slots"):
        lines.append(f"Quota pas: {', '.join(slot.upper() for slot in selection['quota_exhausted_slots'])}")
    if selection.get("unavailable_slots"):
        lines.append(f"Hazir degil: {', '.join(slot.upper() for slot in selection['unavailable_slots'])}")
    for slot, info in (job.get("agents") or {}).items():
        state = str(info.get("status", "?"))
        output = str(info.get("output") or "")[:100]
        lines.append(f"  {slot.upper()}: [{state}] {output}")
    return "\n".join(lines)


def stop_all() -> str:
    with _lock:
        _ensure_jobs_loaded()
        active_job_ids = [job_id for job_id, job in _jobs.items() if job.get("status") == "running"]
        if not active_job_ids:
            return "Aktif Codex job'u yok."

        processes_to_kill: list[subprocess.Popen[str]] = []
        for job_id in active_job_ids:
            job = _jobs[job_id]
            job["status"] = "cancelled"
            job["finished_at"] = _now_iso()
            job["result_summary"] = job.get("result_summary") or "Iptal edildi."

            for agent, info in (job.get("agents") or {}).items():
                if info.get("status") in ("pending", "running"):
                    info["status"] = "cancelled"
                    info["output"] = info.get("output") or "Iptal edildi."
                    info["finished_at"] = _now_iso()

                proc = _processes.get((job_id, agent))
                if proc is not None and proc.poll() is None:
                    processes_to_kill.append(proc)

    for proc in processes_to_kill:
        try:
            proc.kill()
        except Exception:
            pass

    _save_jobs()
    return f"{len(active_job_ids)} job iptal edildi."
