from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable


SLOT_ORDER = ("atlas", "forge", "nexus", "shield", "spark")
ROLE_HINTS = {
    "atlas": ("manager", "core", "planner", "plan"),
    "forge": ("backend", "bridge", "ops", "server", "api"),
    "nexus": ("voice", "hologram", "desktop", "tts", "stt"),
    "shield": ("security", "redaction", "audit", "policy"),
    "spark": ("creative", "ui", "frontend", "visual", "web"),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_int(value: Any, fallback: int) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _remaining_pct(entry: dict[str, Any]) -> int:
    daily_limit = max(int(entry.get("daily_limit") or 0), 1)
    weekly_limit = max(int(entry.get("weekly_limit") or 0), 1)
    daily_left = max(daily_limit - int(entry.get("daily_used") or 0), 0)
    weekly_left = max(weekly_limit - int(entry.get("weekly_used") or 0), 0)
    daily_pct = int(round((daily_left / daily_limit) * 100))
    weekly_pct = int(round((weekly_left / weekly_limit) * 100))
    return max(min(daily_pct, weekly_pct), 0)


class CodexQuotaTracker:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    DEFAULT_DAILY_LIMIT = 100
    DEFAULT_WEEKLY_LIMIT = 500

    def __init__(self, root_dir: str | Path | None = None) -> None:
        if root_dir is not None:
            self.ROOT_DIR = Path(root_dir).resolve()
        self._lock = threading.RLock()

    @property
    def quota_path(self) -> Path:
        return self.ROOT_DIR / "state" / "codex-accounts" / "quota.json"

    @property
    def registry_path(self) -> Path:
        return self.ROOT_DIR / "config" / "account_registry.json"

    def _default_payload(self) -> dict[str, Any]:
        return {"slots": {}}

    def _load_registry_accounts(self) -> list[dict[str, Any]]:
        try:
            payload = json.loads(self.registry_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        accounts = payload.get("accounts") if isinstance(payload, dict) else []
        return [item for item in accounts if isinstance(item, dict)]

    def _match_registry_entry(self, slot: str) -> dict[str, Any]:
        slot_key = str(slot or "").strip().lower()
        if not slot_key:
            return {}

        for item in self._load_registry_accounts():
            execution_slot = str(item.get("execution_slot") or "").strip().lower()
            candidate_id = str(item.get("id") or "").strip().lower()
            if execution_slot == slot_key or candidate_id in {slot_key, f"codex_{slot_key}"}:
                return item

        hints = ROLE_HINTS.get(slot_key, ())
        for item in self._load_registry_accounts():
            haystack = " ".join(
                [
                    str(item.get("role") or ""),
                    str(item.get("label") or ""),
                    str(item.get("notes") or ""),
                ]
            ).lower()
            if any(hint in haystack for hint in hints):
                return item
        return {}

    def _resolve_limits(self, slot: str) -> tuple[int, int]:
        matched = self._match_registry_entry(slot)
        return (
            _coerce_int(matched.get("daily_limit"), self.DEFAULT_DAILY_LIMIT),
            _coerce_int(matched.get("weekly_limit"), self.DEFAULT_WEEKLY_LIMIT),
        )

    def _normalize_slot_entry(self, slot: str, raw: Any) -> dict[str, Any]:
        now = _utc_now()
        today_key = now.date().isoformat()
        week_key = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
        daily_limit, weekly_limit = self._resolve_limits(slot)
        source = raw if isinstance(raw, dict) else {}

        entry = {
            "daily_used": _coerce_int(source.get("daily_used"), 0) if str(source.get("daily_used", "")).strip() else 0,
            "weekly_used": _coerce_int(source.get("weekly_used"), 0) if str(source.get("weekly_used", "")).strip() else 0,
            "daily_limit": daily_limit,
            "weekly_limit": weekly_limit,
            "remaining_pct": 100,
            "cooldown_until": source.get("cooldown_until"),
            "last_task_at": source.get("last_task_at"),
            "last_day": str(source.get("last_day") or today_key),
            "last_week": str(source.get("last_week") or week_key),
            "last_status": str(source.get("last_status") or "").strip(),
        }

        if entry["last_day"] != today_key:
            entry["daily_used"] = 0
            entry["last_day"] = today_key
            entry["cooldown_until"] = None

        if entry["last_week"] != week_key:
            entry["weekly_used"] = 0
            entry["last_week"] = week_key
            entry["cooldown_until"] = None

        entry["remaining_pct"] = _remaining_pct(entry)
        return entry

    def load_payload(self) -> dict[str, Any]:
        with self._lock:
            try:
                if not self.quota_path.exists():
                    return self._default_payload()
                payload = json.loads(self.quota_path.read_text(encoding="utf-8"))
            except Exception:
                return self._default_payload()

        slots = payload.get("slots") if isinstance(payload, dict) else {}
        normalized_slots = {
            slot: self._normalize_slot_entry(slot, value)
            for slot, value in (slots.items() if isinstance(slots, dict) else [])
        }
        for slot in SLOT_ORDER:
            normalized_slots.setdefault(slot, self._normalize_slot_entry(slot, {}))
        return {"slots": normalized_slots}

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.quota_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(self.quota_path.parent),
            suffix=".tmp",
        ) as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            temp_path = Path(handle.name)
        temp_path.replace(self.quota_path)

    def save_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        slots = payload.get("slots") if isinstance(payload, dict) else {}
        normalized_slots = {}
        for slot in SLOT_ORDER:
            normalized_slots[slot] = self._normalize_slot_entry(slot, slots.get(slot, {}) if isinstance(slots, dict) else {})
        normalized_payload = {"slots": normalized_slots}
        with self._lock:
            self._atomic_write(normalized_payload)
        return normalized_payload

    def get_slot_quota(self, slot: str) -> dict[str, Any]:
        slot_key = str(slot or "").strip()
        payload = self.load_payload()
        slots = payload.get("slots", {})
        return dict(slots.get(slot_key, self._normalize_slot_entry(slot_key, {})))

    def get_all_quotas(self) -> dict[str, dict[str, Any]]:
        payload = self.load_payload()
        return dict(payload.get("slots", {}))

    def _next_daily_reset(self, now: datetime) -> str:
        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_day.isoformat()

    def _next_weekly_reset(self, now: datetime) -> str:
        days_until_next_week = 8 - now.isoweekday()
        next_week = (now + timedelta(days=days_until_next_week)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_week.isoformat()

    def _update_slot(self, slot: str, mutate: Callable[[dict[str, Any]], None]) -> dict[str, Any]:
        slot_key = str(slot or "").strip()
        payload = self.load_payload()
        slots = payload.setdefault("slots", {})
        current = dict(slots.get(slot_key, self._normalize_slot_entry(slot_key, {})))
        mutate(current)
        normalized = self._normalize_slot_entry(slot_key, current)
        slots[slot_key] = normalized
        self.save_payload(payload)
        return normalized

    def record_dispatch(self, slot: str) -> dict[str, Any]:
        now = _utc_now()

        def mutate(entry: dict[str, Any]) -> None:
            entry["daily_used"] = int(entry.get("daily_used") or 0) + 1
            entry["weekly_used"] = int(entry.get("weekly_used") or 0) + 1
            entry["last_task_at"] = now.isoformat()
            entry["last_status"] = "dispatched"

        updated = self._update_slot(slot, mutate)
        if int(updated.get("remaining_pct") or 0) <= 0 and not updated.get("cooldown_until"):
            def set_cooldown(entry: dict[str, Any]) -> None:
                daily_limit = int(entry.get("daily_limit") or self.DEFAULT_DAILY_LIMIT)
                weekly_limit = int(entry.get("weekly_limit") or self.DEFAULT_WEEKLY_LIMIT)
                daily_used = int(entry.get("daily_used") or 0)
                weekly_used = int(entry.get("weekly_used") or 0)
                if weekly_used >= weekly_limit:
                    entry["cooldown_until"] = self._next_weekly_reset(now)
                elif daily_used >= daily_limit:
                    entry["cooldown_until"] = self._next_daily_reset(now)

            updated = self._update_slot(slot, set_cooldown)
        return updated

    def record_completion(self, slot: str, status: str) -> dict[str, Any]:
        now = _utc_now()

        def mutate(entry: dict[str, Any]) -> None:
            entry["last_task_at"] = now.isoformat()
            entry["last_status"] = str(status or "").strip().lower()
            if entry.get("cooldown_until"):
                try:
                    cooldown = datetime.fromisoformat(str(entry["cooldown_until"]))
                except ValueError:
                    cooldown = None
                if cooldown and cooldown <= now:
                    entry["cooldown_until"] = None

        return self._update_slot(slot, mutate)

    def cooldown_until(self, slot: str) -> datetime | None:
        quota = self.get_slot_quota(slot)
        raw_value = str(quota.get("cooldown_until") or "").strip()
        if not raw_value:
            return None
        try:
            return datetime.fromisoformat(raw_value)
        except ValueError:
            return None

    def is_exhausted(self, slot: str) -> bool:
        quota = self.get_slot_quota(slot)
        cooldown = self.cooldown_until(slot)
        if cooldown and cooldown > _utc_now():
            return True
        return int(quota.get("remaining_pct") or 0) <= 0

    def has_quota(self, slot: str, estimated_tokens: int = 1) -> bool:
        _ = estimated_tokens
        quota = self.get_slot_quota(slot)
        if self.is_exhausted(slot):
            return False
        return int(quota.get("remaining_pct") or 0) > 0


_quota_tracker: CodexQuotaTracker | None = None


def get_quota_tracker() -> CodexQuotaTracker:
    global _quota_tracker
    if _quota_tracker is None:
        _quota_tracker = CodexQuotaTracker()
    return _quota_tracker


def get_all_quotas() -> dict[str, dict[str, Any]]:
    return get_quota_tracker().get_all_quotas()


def is_exhausted(slot: str) -> bool:
    return get_quota_tracker().is_exhausted(slot)


def cooldown_until(slot: str) -> datetime | None:
    return get_quota_tracker().cooldown_until(slot)


def has_quota(slot: str, estimated_tokens: int = 1) -> bool:
    return get_quota_tracker().has_quota(slot, estimated_tokens=estimated_tokens)
