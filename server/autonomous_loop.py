#!/usr/bin/env python3
"""
Jarvis autonomous loop manager.

Runs OpenCode in an isolated git worktree, persists runtime state, and sends
scheduled Telegram updates without touching the live working tree.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


SERVER_DIR = Path(__file__).resolve().parent
ROOT_DIR = SERVER_DIR.parent
WORKSPACE_DIR = ROOT_DIR / "server" / "agent_workspace" / "autonomous"
WORKTREES_DIR = WORKSPACE_DIR / "worktrees"
CONFIGS_DIR = WORKSPACE_DIR / "runtime_config"
LOG_DIR = ROOT_DIR / "server" / "logs" / "autonomous"
STATE_FILE = WORKSPACE_DIR / "current_job.json"
EVENTS_LOG = LOG_DIR / "jobs.jsonl"

DEFAULT_DURATION_HOURS = int(os.environ.get("AUTONOMOUS_DURATION_HOURS", "24"))
DEFAULT_REPORT_INTERVAL_MINUTES = int(os.environ.get("AUTONOMOUS_REPORT_INTERVAL_MINUTES", "60"))
DEFAULT_OPENCODE_TIMEOUT_SECONDS = int(os.environ.get("AUTONOMOUS_OPENCODE_TIMEOUT_SECONDS", "2400"))
DEFAULT_BRANCH_PREFIX = str(os.environ.get("AUTONOMOUS_BRANCH_PREFIX", "autonomous")).strip() or "autonomous"
PROMPT_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "server/config/assistant_operation_mode.json",
    "progress.md",
]

for directory in (WORKSPACE_DIR, WORKTREES_DIR, CONFIGS_DIR, LOG_DIR):
    directory.mkdir(parents=True, exist_ok=True)


LOGGER = logging.getLogger("jarvis.autonomous")
if not LOGGER.handlers:
    LOGGER.setLevel(logging.INFO)
    _file_handler = logging.FileHandler(LOG_DIR / "autonomous_manager.log", encoding="utf-8")
    _stream_handler = logging.StreamHandler()
    _formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    _file_handler.setFormatter(_formatter)
    _stream_handler.setFormatter(_formatter)
    LOGGER.addHandler(_file_handler)
    LOGGER.addHandler(_stream_handler)
    LOGGER.propagate = False


def _now() -> datetime:
    return datetime.now()


def _iso(ts: datetime | None = None) -> str:
    return (ts or _now()).isoformat(timespec="seconds")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _initial_state() -> dict[str, Any]:
    return {
        "status": "idle",
        "job_id": "",
        "goal": "",
        "duration_hours": 0,
        "report_interval_minutes": 0,
        "validation_command": "",
        "started_at": "",
        "deadline_at": "",
        "next_run_at": "",
        "stopped_at": "",
        "iteration": 0,
        "failure_count": 0,
        "branch_name": "",
        "worktree_dir": "",
        "runtime_config_home": "",
        "report_log_path": "",
        "telegram_chat_id": "",
        "engine": "opencode",
        "opencode_command": "",
        "opencode_session_id": "",
        "last_report_at": "",
        "last_summary": "",
        "last_commit": "",
        "last_changed_files": [],
        "last_validation": [],
        "last_error": "",
        "last_report_status": "",
        "thread_alive": False,
        "stop_requested": False,
    }


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default)


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _excerpt(text: str, limit: int = 320) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "…"


def _slugify(value: str, limit: int = 36) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    text = re.sub(r"-{2,}", "-", text)
    return (text or "job")[:limit].strip("-") or "job"


def _resolve_command(command: str) -> str:
    raw = str(command or "").strip()
    if not raw:
        return ""
    if os.name == "nt" and not Path(raw).suffix:
        candidates = [f"{raw}.cmd", f"{raw}.exe", f"{raw}.bat", raw]
    else:
        candidates = [raw]

    seen: set[str] = set()
    for candidate in candidates:
        resolved = shutil.which(candidate) or candidate
        key = str(resolved).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        try:
            completed = subprocess.run(
                [str(resolved), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            continue
        except Exception:
            continue
        if completed.returncode == 0:
            return str(resolved)
    return ""


def _run_process(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = 60,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _run_shell(
    command: str,
    *,
    cwd: Path,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd),
        shell=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _git_root() -> Path:
    result = _run_process(["git", "rev-parse", "--show-toplevel"], cwd=ROOT_DIR, timeout=20)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "git root bulunamadi").strip())
    return Path(result.stdout.strip())


def _extract_git_paths(status_output: str) -> list[str]:
    changed: list[str] = []
    for raw_line in status_output.splitlines():
        line = raw_line.rstrip()
        if len(line) < 4:
            continue
        candidate = line[3:].strip()
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1].strip()
        if candidate:
            changed.append(candidate.replace("\\", "/"))
    return changed


def _error_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, dict):
        return ""
    for key in ("message", "name", "code"):
        text = str(value.get(key) or "").strip()
        if text:
            return text
    nested = value.get("data")
    if isinstance(nested, dict):
        text = str(nested.get("message") or "").strip()
        if text:
            return text
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return ""


def _parse_opencode_jsonl(stdout: str) -> dict[str, Any]:
    session_id = ""
    messages: list[str] = []
    errors: list[str] = []
    usage = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    cost_usd = 0.0

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        current_session_id = str(event.get("sessionID") or "").strip()
        if current_session_id:
            session_id = current_session_id

        event_type = str(event.get("type") or "").strip()
        if event_type == "text":
            part = event.get("part") or {}
            if isinstance(part, dict):
                text = str(part.get("text") or "").strip()
                if text:
                    messages.append(text)
            continue

        if event_type == "step_finish":
            part = event.get("part") or {}
            if isinstance(part, dict):
                tokens = part.get("tokens") or {}
                cache = tokens.get("cache") if isinstance(tokens, dict) else {}
                if isinstance(tokens, dict):
                    usage["input_tokens"] += int(tokens.get("input") or 0)
                    usage["output_tokens"] += int(tokens.get("output") or 0) + int(tokens.get("reasoning") or 0)
                if isinstance(cache, dict):
                    usage["cached_input_tokens"] += int(cache.get("read") or 0)
                try:
                    cost_usd += float(part.get("cost") or 0)
                except Exception:
                    pass
            continue

        if event_type == "tool_use":
            part = event.get("part") or {}
            state = part.get("state") if isinstance(part, dict) else {}
            if isinstance(state, dict) and str(state.get("status") or "").strip() == "error":
                text = str(state.get("error") or "").strip()
                if text:
                    errors.append(text)
            continue

        if event_type == "error":
            text = _error_text(event.get("error") or event.get("message"))
            if text:
                errors.append(text)

    return {
        "session_id": session_id,
        "summary": "\n\n".join(messages).strip(),
        "usage": usage,
        "cost_usd": round(cost_usd, 6),
        "errors": errors,
    }


class AutonomousLoopManager:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._active_process: subprocess.Popen[str] | None = None
        self._telegram_token = ""
        self._state = _load_json(STATE_FILE, _initial_state())

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            snapshot = dict(self._state)
            snapshot["thread_alive"] = bool(self._thread and self._thread.is_alive())
            snapshot["opencode_active"] = bool(self._active_process and self._active_process.poll() is None)
            return snapshot

    def start(
        self,
        *,
        goal: str,
        duration_hours: int = DEFAULT_DURATION_HOURS,
        report_interval_minutes: int = DEFAULT_REPORT_INTERVAL_MINUTES,
        validation_command: str = "",
        telegram_chat_id: str = "",
        telegram_token: str = "",
    ) -> dict[str, Any]:
        goal = str(goal or "").strip()
        if not goal:
            return {"ok": False, "error": "goal_required", **self.get_status()}

        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"ok": False, "error": "already_running", **self.get_status()}

            opencode_command = _resolve_command(os.environ.get("AUTONOMOUS_OPENCODE_COMMAND", "opencode"))
            if not opencode_command:
                return {"ok": False, "error": "opencode_not_found", **self.get_status()}

            git_root = _git_root()
            job_id = f"{_now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
            branch_slug = _slugify(goal, limit=28)
            worktree_name = f"{branch_slug}-{job_id[-6:]}"
            branch_name = f"{DEFAULT_BRANCH_PREFIX}/{worktree_name}"
            worktree_dir = WORKTREES_DIR / worktree_name
            runtime_config_home = CONFIGS_DIR / job_id
            report_log_path = LOG_DIR / f"{job_id}.jsonl"

            worktree_result = _run_process(
                ["git", "worktree", "add", "-b", branch_name, str(worktree_dir), "HEAD"],
                cwd=git_root,
                timeout=180,
            )
            if worktree_result.returncode != 0:
                error_text = (worktree_result.stderr or worktree_result.stdout or "git worktree add fail").strip()
                return {"ok": False, "error": error_text, **self.get_status()}

            self._prepare_runtime_config(runtime_config_home)
            self._telegram_token = str(telegram_token or self._telegram_token or "").strip()
            duration_hours = max(1, int(duration_hours or DEFAULT_DURATION_HOURS))
            report_interval_minutes = max(5, int(report_interval_minutes or DEFAULT_REPORT_INTERVAL_MINUTES))

            state = _initial_state()
            state.update(
                {
                    "status": "running",
                    "job_id": job_id,
                    "goal": goal,
                    "duration_hours": duration_hours,
                    "report_interval_minutes": report_interval_minutes,
                    "validation_command": str(validation_command or "").strip(),
                    "started_at": _iso(),
                    "deadline_at": _iso(_now() + timedelta(hours=duration_hours)),
                    "next_run_at": _iso(),
                    "iteration": 0,
                    "failure_count": 0,
                    "branch_name": branch_name,
                    "worktree_dir": str(worktree_dir),
                    "runtime_config_home": str(runtime_config_home),
                    "report_log_path": str(report_log_path),
                    "telegram_chat_id": str(telegram_chat_id or "").strip(),
                    "opencode_command": opencode_command,
                    "thread_alive": True,
                    "stop_requested": False,
                    "last_error": "",
                    "last_report_status": "",
                }
            )
            self._state = state
            _save_json(STATE_FILE, self._state)
            _append_jsonl(
                EVENTS_LOG,
                {
                    "timestamp": _iso(),
                    "type": "job_started",
                    "job_id": job_id,
                    "goal": goal,
                    "branch_name": branch_name,
                    "worktree_dir": str(worktree_dir),
                },
            )

            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, name=f"autonomous-{job_id}", daemon=True)
            self._thread.start()
            return {"ok": True, **self.get_status()}

    def stop(self, reason: str = "manual_stop") -> dict[str, Any]:
        with self._lock:
            if self._state.get("status") not in {"running", "stopping"}:
                return {"ok": False, "error": "not_running", **self.get_status()}
            self._stop_event.set()
            self._state["stop_requested"] = True
            self._state["status"] = "stopping"
            self._state["last_error"] = str(reason or "manual_stop")
            self._state["thread_alive"] = bool(self._thread and self._thread.is_alive())
            _save_json(STATE_FILE, self._state)
            proc = self._active_process

        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass

        return {"ok": True, **self.get_status()}

    def resume_if_needed(self, *, telegram_token: str = "", telegram_chat_id: str = "") -> dict[str, Any]:
        with self._lock:
            state = _load_json(STATE_FILE, _initial_state())
            self._state = state
            self._telegram_token = str(telegram_token or self._telegram_token or "").strip()
            if state.get("status") != "running":
                return {"resumed": False, **self.get_status()}
            if self._thread and self._thread.is_alive():
                return {"resumed": False, **self.get_status()}
            deadline_at = _parse_iso(str(state.get("deadline_at") or ""))
            if not deadline_at or deadline_at <= _now():
                self._state["status"] = "completed"
                self._state["thread_alive"] = False
                self._state["stopped_at"] = _iso()
                _save_json(STATE_FILE, self._state)
                return {"resumed": False, **self.get_status()}
            if telegram_chat_id and not state.get("telegram_chat_id"):
                self._state["telegram_chat_id"] = str(telegram_chat_id).strip()
                _save_json(STATE_FILE, self._state)
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name=f"autonomous-{state.get('job_id') or 'resume'}",
                daemon=True,
            )
            self._thread.start()
            return {"resumed": True, **self.get_status()}

    def _persist_state(self) -> None:
        self._state["thread_alive"] = bool(self._thread and self._thread.is_alive())
        _save_json(STATE_FILE, self._state)

    def _prepare_runtime_config(self, runtime_config_home: Path) -> None:
        source_home = Path(os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config"))
        source_dir = source_home / "opencode"
        target_dir = runtime_config_home / "opencode"
        target_dir.mkdir(parents=True, exist_ok=True)
        if source_dir.exists():
            shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)

        config_path = target_dir / "opencode.json"
        existing = _load_json(config_path, {})
        permission = existing.get("permission")
        if not isinstance(permission, dict):
            permission = {}
        permission["external_directory"] = "allow"
        existing["permission"] = permission
        _save_json(config_path, existing)

    def _run_loop(self) -> None:
        try:
            while True:
                if self._stop_event.is_set():
                    self._finish("stopped", "Stop sinyali alindi.")
                    return

                with self._lock:
                    state = dict(self._state)
                deadline_at = _parse_iso(str(state.get("deadline_at") or ""))
                next_run_at = _parse_iso(str(state.get("next_run_at") or "")) or _now()
                if not deadline_at:
                    self._finish("failed", "deadline_at eksik.")
                    return
                if _now() >= deadline_at:
                    self._finish("completed", "Planlanan sure doldu.")
                    return

                wait_seconds = max(0.0, (next_run_at - _now()).total_seconds())
                if wait_seconds > 0 and self._sleep_with_stop(wait_seconds):
                    self._finish("stopped", "Stop sinyali alindi.")
                    return

                report = self._run_iteration()
                if report.get("status") in {"failed", "validation_failed", "agent_failed"}:
                    self._finish("failed", str(report.get("error") or report.get("status") or "iteration_failed"))
                    return

                with self._lock:
                    deadline_at = _parse_iso(str(self._state.get("deadline_at") or ""))
                    if not deadline_at:
                        self._finish("failed", "deadline_at eksik.")
                        return
                    if _now() >= deadline_at:
                        self._finish("completed", "Planlanan sure doldu.")
                        return
                    self._state["next_run_at"] = _iso(
                        min(deadline_at, _now() + timedelta(minutes=int(self._state["report_interval_minutes"])))
                    )
                    self._persist_state()
        except Exception as exc:
            LOGGER.exception("Autonomous loop hata verdi")
            self._finish("failed", str(exc)[:300])

    def _sleep_with_stop(self, seconds: float) -> bool:
        deadline = time.time() + float(seconds)
        while time.time() < deadline:
            if self._stop_event.is_set():
                return True
            time.sleep(min(2.0, deadline - time.time()))
        return self._stop_event.is_set()

    def _run_iteration(self) -> dict[str, Any]:
        with self._lock:
            state = dict(self._state)
            iteration = int(state.get("iteration") or 0) + 1
            self._state["iteration"] = iteration
            self._state["last_error"] = ""
            self._persist_state()

        worktree_dir = Path(str(state["worktree_dir"]))
        prompt = self._build_prompt(state, iteration)
        started_at = _now()
        opencode_result = self._run_opencode(
            command=str(state["opencode_command"]),
            prompt=prompt,
            worktree_dir=worktree_dir,
            runtime_config_home=Path(str(state["runtime_config_home"])),
            session_id=str(state.get("opencode_session_id") or ""),
        )

        changed_files = self._collect_changed_files(worktree_dir)
        validations = self._run_validations(worktree_dir, changed_files, str(state.get("validation_command") or ""))
        validation_ok = all(item.get("ok") for item in validations)

        commit_hash = ""
        status = "success"
        error_text = ""
        if opencode_result.get("returncode") not in (0, None):
            status = "agent_failed"
            error_text = _excerpt(opencode_result.get("error_message") or opencode_result.get("stderr") or "", 280)
        elif opencode_result.get("timed_out"):
            status = "agent_failed"
            error_text = "OpenCode run zaman asimina ugradi."
        elif not validation_ok:
            status = "validation_failed"
            failed_outputs = [item.get("output") for item in validations if not item.get("ok")]
            error_text = _excerpt(" | ".join(str(item or "") for item in failed_outputs), 280)
        elif changed_files:
            commit_hash = self._commit_changes(worktree_dir, iteration, str(state["goal"]))

        summary = str(opencode_result.get("summary") or "").strip()
        if not summary and not error_text:
            summary = "OpenCode calisti fakat ozet cikarmadi."
        if not summary and error_text:
            summary = error_text

        report = {
            "timestamp": _iso(),
            "job_id": state["job_id"],
            "iteration": iteration,
            "goal": state["goal"],
            "status": status,
            "duration_seconds": round((_now() - started_at).total_seconds(), 2),
            "summary": summary,
            "changed_files": changed_files,
            "validation": validations,
            "commit_hash": commit_hash,
            "branch_name": state["branch_name"],
            "worktree_dir": str(worktree_dir),
            "session_id": opencode_result.get("session_id") or "",
            "usage": opencode_result.get("usage") or {},
            "cost_usd": opencode_result.get("cost_usd") or 0,
            "stdout_excerpt": _excerpt(opencode_result.get("stdout") or "", 600),
            "stderr_excerpt": _excerpt(opencode_result.get("stderr") or "", 300),
            "error": error_text,
        }

        with self._lock:
            self._state["opencode_session_id"] = str(opencode_result.get("session_id") or self._state.get("opencode_session_id") or "")
            self._state["last_report_at"] = report["timestamp"]
            self._state["last_summary"] = _excerpt(summary, 600)
            self._state["last_commit"] = commit_hash
            self._state["last_changed_files"] = changed_files
            self._state["last_validation"] = validations
            self._state["last_error"] = error_text
            self._state["last_report_status"] = status
            self._state["failure_count"] = 0 if status == "success" else int(self._state.get("failure_count") or 0) + 1
            self._persist_state()

        report_log_path = Path(str(state["report_log_path"]))
        _append_jsonl(report_log_path, report)
        _append_jsonl(EVENTS_LOG, {"timestamp": _iso(), "type": "iteration", **report})
        self._send_telegram_report(report)
        return report

    def _build_prompt(self, state: dict[str, Any], iteration: int) -> str:
        validation_note = (
            f"Ek validasyon komutu: {state['validation_command']}"
            if state.get("validation_command")
            else "Ek validasyon komutu verilmedi. Runner, degisen Python dosyalari icin py_compile calistiracak."
        )
        previous_summary = str(state.get("last_summary") or "Ilk iterasyon.")
        previous_files = ", ".join(state.get("last_changed_files") or []) or "Henüz yok."

        lines = [
            f"Bugun tarih {_now().strftime('%Y-%m-%d %H:%M')} ve bu repo Jarvis Mission Control.",
            "Sen izole bir git worktree icinde calisan otonom bakim ajanisin.",
            "",
            f"Hedef: {state['goal']}",
            f"Iterasyon: {iteration}",
            f"Branch: {state['branch_name']}",
            "",
            "Mutlaka once su dosyalari oku ve sonra hareket et:",
        ]
        for filepath in PROMPT_FILES:
            if (ROOT_DIR / filepath).exists():
                lines.append(f"- {filepath}")
        lines.extend(
            [
                "",
                "Calisma kurallari:",
                "- Kullaniciya soru sorma; makul varsayimla ilerle.",
                "- Kucuk ama gercek bir iyilestirme yap; tek iterasyonda tek anlamli degisim seti yap.",
                "- Secrets, .env, token, billing, production deploy, branch protection ve dis hesap login akislarina dokunma.",
                "- Asla push, force-push, merge veya protected branch hedefleyen is yapma.",
                "- Git commit yapma; commit'i loop orchestrator yapacak.",
                "- Repo talimatlarini ihlal etme. Read-before-write ve smallest-correct-change yaklasimini koru.",
                "- Degisiklik sonrasi repo okunabilir ve calisir halde kalsin.",
                "",
                "Baglam:",
                f"- Onceki ozet: {previous_summary}",
                f"- Onceki degisen dosyalar: {previous_files}",
                f"- {validation_note}",
                "",
                "Bitirirken kisa bir rapor ver:",
                "Summary: ...",
                "Files: ...",
                "ValidationNotes: ...",
                "Next: ...",
            ]
        )
        return "\n".join(lines).strip()

    def _run_opencode(
        self,
        *,
        command: str,
        prompt: str,
        worktree_dir: Path,
        runtime_config_home: Path,
        session_id: str,
    ) -> dict[str, Any]:
        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(runtime_config_home)
        env.setdefault("CI", "1")
        env.setdefault("NO_COLOR", "1")

        args = [command, "run", "--format", "json", "--dir", str(worktree_dir)]
        if session_id:
            args.extend(["--continue", session_id])
        args.append(prompt)

        LOGGER.info("OpenCode iteration basliyor: %s", worktree_dir)
        proc: subprocess.Popen[str] | None = None
        stdout = ""
        stderr = ""
        timed_out = False
        try:
            proc = subprocess.Popen(
                args,
                cwd=str(worktree_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            with self._lock:
                self._active_process = proc

            try:
                stdout, stderr = proc.communicate(timeout=DEFAULT_OPENCODE_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                timed_out = True
        finally:
            with self._lock:
                self._active_process = None

        parsed = _parse_opencode_jsonl(stdout or "")
        error_message = "\n".join(parsed.get("errors") or []).strip()
        if not error_message and stderr:
            error_message = stderr.strip()

        return {
            "returncode": None if proc is None else proc.returncode,
            "timed_out": timed_out,
            "stdout": stdout,
            "stderr": stderr,
            "summary": parsed.get("summary") or "",
            "session_id": parsed.get("session_id") or "",
            "usage": parsed.get("usage") or {},
            "cost_usd": parsed.get("cost_usd") or 0,
            "error_message": error_message,
        }

    def _collect_changed_files(self, worktree_dir: Path) -> list[str]:
        result = _run_process(["git", "status", "--porcelain"], cwd=worktree_dir, timeout=20)
        if result.returncode != 0:
            return []
        return _extract_git_paths(result.stdout or "")

    def _run_validations(
        self,
        worktree_dir: Path,
        changed_files: list[str],
        validation_command: str,
    ) -> list[dict[str, Any]]:
        validations: list[dict[str, Any]] = []
        if validation_command:
            result = _run_shell(validation_command, cwd=worktree_dir, timeout=900)
            validations.append(
                {
                    "name": validation_command,
                    "ok": result.returncode == 0,
                    "output": _excerpt((result.stdout or result.stderr or "").strip(), 400),
                }
            )

        changed_python = [
            path for path in changed_files
            if path.lower().endswith(".py") and (worktree_dir / path).exists()
        ]
        if changed_python:
            result = _run_process(
                [sys.executable, "-m", "py_compile", *changed_python],
                cwd=worktree_dir,
                timeout=180,
            )
            validations.append(
                {
                    "name": f"python -m py_compile {' '.join(changed_python[:6])}".strip(),
                    "ok": result.returncode == 0,
                    "output": _excerpt((result.stdout or result.stderr or 'ok').strip(), 400),
                }
            )

        if not validations:
            validations.append(
                {
                    "name": "no-op",
                    "ok": True,
                    "output": "Degisen Python dosyasi veya explicit validation komutu yok.",
                }
            )
        return validations

    def _commit_changes(self, worktree_dir: Path, iteration: int, goal: str) -> str:
        add_result = _run_process(["git", "add", "-A"], cwd=worktree_dir, timeout=60)
        if add_result.returncode != 0:
            return ""
        message = f"autonomous: iteration {iteration:02d} - {_slugify(goal, limit=24)}"
        commit_result = _run_process(["git", "commit", "-m", message], cwd=worktree_dir, timeout=90)
        if commit_result.returncode != 0:
            return ""
        head_result = _run_process(["git", "rev-parse", "--short", "HEAD"], cwd=worktree_dir, timeout=20)
        if head_result.returncode != 0:
            return ""
        return head_result.stdout.strip()

    def _send_telegram_report(self, report: dict[str, Any]) -> None:
        token = str(self._telegram_token or "").strip()
        chat_id = str(self._state.get("telegram_chat_id") or "").strip()
        if not token or not chat_id:
            return

        summary = _excerpt(report.get("summary") or report.get("error") or "-", 500)
        changed = ", ".join(report.get("changed_files") or []) or "Degisiklik yok"
        validation_states = [
            f"{item.get('name')}: {'ok' if item.get('ok') else 'fail'}"
            for item in report.get("validation") or []
        ]
        message = "\n".join(
            [
                "Jarvis otonom dongu raporu",
                f"Durum: {report.get('status')}",
                f"Hedef: {_excerpt(report.get('goal') or '-', 120)}",
                f"Iterasyon: {report.get('iteration')}",
                f"Branch: {report.get('branch_name')}",
                f"Commit: {report.get('commit_hash') or '-'}",
                f"Dosyalar: {_excerpt(changed, 250)}",
                f"Validasyon: {_excerpt(' | '.join(validation_states), 250)}",
                f"Ozet: {summary}",
            ]
        )
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
        try:
            req = Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=10):
                pass
        except Exception as exc:
            LOGGER.warning("Telegram raporu gonderilemedi: %s", exc)

    def _finish(self, status: str, note: str) -> None:
        with self._lock:
            self._state["status"] = status
            self._state["thread_alive"] = False
            self._state["stop_requested"] = status in {"stopped", "failed"}
            self._state["stopped_at"] = _iso()
            self._state["last_error"] = str(note or "").strip()
            self._persist_state()
            _append_jsonl(
                EVENTS_LOG,
                {
                    "timestamp": _iso(),
                    "type": "job_finished",
                    "job_id": self._state.get("job_id"),
                    "status": status,
                    "note": str(note or "").strip(),
                },
            )


MANAGER = AutonomousLoopManager()


def start_autonomous_loop(
    *,
    goal: str,
    duration_hours: int = DEFAULT_DURATION_HOURS,
    report_interval_minutes: int = DEFAULT_REPORT_INTERVAL_MINUTES,
    validation_command: str = "",
    telegram_chat_id: str = "",
    telegram_token: str = "",
) -> dict[str, Any]:
    return MANAGER.start(
        goal=goal,
        duration_hours=duration_hours,
        report_interval_minutes=report_interval_minutes,
        validation_command=validation_command,
        telegram_chat_id=telegram_chat_id,
        telegram_token=telegram_token,
    )


def stop_autonomous_loop(reason: str = "manual_stop") -> dict[str, Any]:
    return MANAGER.stop(reason=reason)


def get_autonomous_status() -> dict[str, Any]:
    return MANAGER.get_status()


def resume_autonomous_loop_if_needed(*, telegram_token: str = "", telegram_chat_id: str = "") -> dict[str, Any]:
    return MANAGER.resume_if_needed(telegram_token=telegram_token, telegram_chat_id=telegram_chat_id)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Jarvis autonomous OpenCode loop")
    parser.add_argument("goal", nargs="?", help="Otonom gorev hedefi")
    parser.add_argument("duration", nargs="?", type=int, default=DEFAULT_DURATION_HOURS, help="Saat")
    parser.add_argument("--status", action="store_true", help="Mevcut runtime durumunu yazdir")
    parser.add_argument("--stop", action="store_true", help="Calisan isi durdur")
    parser.add_argument("--validation", default="", help="Iterasyon sonrasi calisacak ek validation komutu")
    parser.add_argument("--chat-id", default=os.environ.get("TELEGRAM_CHAT_ID", ""), help="Telegram chat id")
    parser.add_argument("--token", default=os.environ.get("TELEGRAM_BOT_TOKEN", ""), help="Telegram bot token")
    args = parser.parse_args()

    if args.status:
        print(json.dumps(get_autonomous_status(), ensure_ascii=False, indent=2))
        return 0
    if args.stop:
        print(json.dumps(stop_autonomous_loop(), ensure_ascii=False, indent=2))
        return 0
    if not args.goal:
        parser.error("goal gereklidir")

    result = start_autonomous_loop(
        goal=args.goal,
        duration_hours=args.duration,
        validation_command=args.validation,
        telegram_chat_id=args.chat_id,
        telegram_token=args.token,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        return 1

    while True:
        status = get_autonomous_status()
        if status.get("status") not in {"running", "stopping"}:
            break
        time.sleep(5)
    print(json.dumps(get_autonomous_status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
