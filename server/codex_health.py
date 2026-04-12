from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timezone
from typing import Any

try:
    from codex_job_manager import list_recent_jobs
except Exception:
    from server.codex_job_manager import list_recent_jobs  # type: ignore

try:
    from codex_quota_tracker import get_all_quotas, get_quota_tracker
except Exception:
    from server.codex_quota_tracker import get_all_quotas, get_quota_tracker  # type: ignore

try:
    from telegram_webhook import send_telegram_message
except Exception:
    from server.telegram_webhook import send_telegram_message  # type: ignore


log = logging.getLogger("jarvis.codex_health")

_SILENT_SLOT_SECONDS = 2 * 60 * 60
_STUCK_JOB_SECONDS = 30 * 60
_SENSITIVE_PATTERN = re.compile(
    r"(access[_-]?token|refresh[_-]?token|id[_-]?token|\bbearer\b|\bsecret\b|api[_-]?key|\bauth(?:orization)?\b)",
    re.IGNORECASE,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _sanitize_text(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    if _SENSITIVE_PATTERN.search(text):
        return "sensitive content redacted"
    return text[:limit]


class CodexHealthWatcher:
    def __init__(self, interval_seconds: int = 600, notify_chat_id: int | None = None):
        self.interval = max(int(interval_seconds or 0), 1)
        self.notify_chat_id = int(notify_chat_id) if notify_chat_id is not None else None
        self._thread: threading.Thread | None = None
        self._alert_cache: dict[tuple[str, str], float] = {}
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return self._thread
            self._thread = threading.Thread(
                target=self._loop,
                daemon=True,
                name="codex-health",
            )
            self._thread.start()
            return self._thread

    def _loop(self):
        while True:
            try:
                self._check()
            except Exception as exc:
                log.error(f"[HealthWatcher] {exc}")
            time.sleep(self.interval)

    def _check(self):
        quotas = get_all_quotas()
        tracker = get_quota_tracker()
        now = _utc_now()
        exhausted_slots: list[str] = []

        for slot, entry in quotas.items():
            if not isinstance(entry, dict):
                continue

            remaining_pct = int(entry.get("remaining_pct") or 0)
            if remaining_pct < 5:
                self._notify("critical", f"{slot.upper()} quota kritik: %{remaining_pct}")
            elif remaining_pct < 20:
                self._notify("warning", f"{slot.upper()} quota dusuk: %{remaining_pct}")

            try:
                exhausted = bool(tracker.is_exhausted(slot))
            except Exception:
                exhausted = remaining_pct <= 0
            if exhausted:
                exhausted_slots.append(str(slot))

            last_task_at = _parse_timestamp(entry.get("last_task_at"))
            if last_task_at is None:
                continue
            age_seconds = max((now - last_task_at).total_seconds(), 0)
            if age_seconds > _SILENT_SLOT_SECONDS:
                age_minutes = int(age_seconds // 60)
                self._notify("warning", f"{slot.upper()} sessiz: son aktivite {age_minutes} dk once")

        if quotas and len(exhausted_slots) == len(quotas):
            slot_text = ", ".join(slot.upper() for slot in exhausted_slots)
            self._notify("critical", f"tum Codex slotlari exhausted: {slot_text}")

        for job in list_recent_jobs(limit=100):
            if not isinstance(job, dict):
                continue
            if str(job.get("status") or "").strip().lower() != "running":
                continue
            duration_seconds = float(job.get("duration_seconds") or 0)
            if duration_seconds <= _STUCK_JOB_SECONDS:
                continue

            slot_text = ", ".join(str(slot).upper() for slot in (job.get("selected_slots") or []))
            summary = _sanitize_text(job.get("summary") or job.get("task"))
            details = [f"job {job.get('id')}"]
            if slot_text:
                details.append(f"slot {slot_text}")
            details.append(f"{int(duration_seconds // 60)} dk")
            if summary:
                details.append(summary)
            self._notify("warning", "takili calisan " + " | ".join(details))

    def _notify(self, level: str, message: str):
        safe_message = _sanitize_text(message, limit=320)
        if not safe_message:
            return

        cache_key = (str(level or "info"), safe_message)
        cooldown = max(self.interval, 600)
        now = time.monotonic()

        with self._lock:
            last_sent = self._alert_cache.get(cache_key)
            if last_sent is not None and (now - last_sent) < cooldown:
                return
            self._alert_cache[cache_key] = now

        prefix = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
        }.get(str(level or "").strip().lower(), "ℹ️")

        log_method = {
            "info": log.info,
            "warning": log.warning,
            "critical": log.error,
        }.get(str(level or "").strip().lower(), log.info)
        log_method("[HealthWatcher] %s", safe_message)

        if not self.notify_chat_id:
            return

        try:
            send_telegram_message(
                self.notify_chat_id,
                f"{prefix} Codex Health: {safe_message}",
                parse_mode=None,
            )
        except Exception as exc:
            log.warning(f"[HealthWatcher] Telegram notify failed: {exc}")
