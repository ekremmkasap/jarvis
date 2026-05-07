from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_BUS_PATH = ROOT_DIR / "state" / "codex-accounts" / "_bus.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CodexBus:
    def __init__(self, *, path: Path | None = None) -> None:
        self.path = Path(path or DEFAULT_BUS_PATH)
        self._lock = threading.RLock()

    def _read_all_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        for raw_line in self.path.read_text(encoding="utf-8").splitlines():
            raw = str(raw_line or "").strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
        return events

    def _append_unlocked(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")

    def _fingerprint(
        self,
        *,
        slot: str,
        event_type: str,
        job_id: str | None,
        payload: dict[str, Any],
    ) -> str:
        material = json.dumps(
            {
                "slot": slot,
                "event_type": event_type,
                "job_id": job_id,
                "payload": payload,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def post(
        self,
        slot: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        job_id: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        event_payload = dict(payload or {})
        normalized_slot = str(slot or "").strip().lower()
        normalized_type = str(event_type or "").strip()
        normalized_job = str(job_id or "").strip() or None
        fingerprint = self._fingerprint(
            slot=normalized_slot,
            event_type=normalized_type,
            job_id=normalized_job,
            payload=event_payload,
        )
        resolved_event_id = str(event_id or fingerprint or uuid.uuid4().hex).strip()

        with self._lock:
            for existing in self._read_all_unlocked():
                if str(existing.get("event_id") or "").strip() == resolved_event_id:
                    return existing

            record = {
                "event_id": resolved_event_id,
                "ts": _now_iso(),
                "slot": normalized_slot,
                "event_type": normalized_type,
                "job_id": normalized_job,
                "payload": event_payload,
            }
            self._append_unlocked(record)
            return record

    def read_since(self, after_ts: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        requested_limit = max(int(limit or 0), 0)
        if requested_limit == 0:
            return []
        with self._lock:
            events = self._read_all_unlocked()
        if after_ts:
            events = [event for event in events if str(event.get("ts") or "") > str(after_ts)]
        return events[-requested_limit:]

    def read_for_slot(self, slot: str, limit: int = 50) -> list[dict[str, Any]]:
        slot_name = str(slot or "").strip().lower()
        selected: list[dict[str, Any]] = []
        for event in self.read_since(limit=500):
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            target_slot = str(payload.get("target_slot") or "").strip().lower()
            if target_slot and target_slot != slot_name:
                continue
            selected.append(event)
        return selected[-max(int(limit or 0), 0) :]

    def _active_locks(self) -> dict[str, str]:
        locks: dict[str, str] = {}
        for event in self.read_since(limit=5000):
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            target_path = str(payload.get("path") or "").strip()
            if not target_path:
                continue
            event_type = str(event.get("event_type") or "").strip()
            if event_type == "lock_claim":
                locks[target_path] = str(event.get("slot") or "").strip().lower()
            elif event_type == "lock_release":
                locks.pop(target_path, None)
        return locks

    def claim_lock(self, slot: str, path: str, *, job_id: str | None = None) -> bool:
        slot_name = str(slot or "").strip().lower()
        target_path = str(path or "").strip()
        if not target_path:
            return False
        owner = self._active_locks().get(target_path)
        if owner and owner != slot_name:
            return False
        self.post(slot_name, "lock_claim", {"path": target_path}, job_id=job_id)
        return True

    def release_lock(self, slot: str, path: str, *, job_id: str | None = None) -> bool:
        slot_name = str(slot or "").strip().lower()
        target_path = str(path or "").strip()
        if self._active_locks().get(target_path) != slot_name:
            return False
        self.post(slot_name, "lock_release", {"path": target_path}, job_id=job_id)
        return True

    def build_peer_context_block(self, slot: str, limit: int = 10) -> str:
        slot_name = str(slot or "").strip().lower()
        lines = ["# Peer Context"]
        for event in self.read_for_slot(slot_name, limit=limit):
            if str(event.get("slot") or "").strip().lower() == slot_name:
                continue
            payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
            summary = (
                str(payload.get("summary") or "")
                or str(payload.get("question") or "")
                or str(payload.get("error") or "")
                or str(payload.get("path") or "")
            ).strip()
            lines.append(
                f"- [{event.get('ts')}] {event.get('slot')} {event.get('event_type')} job={event.get('job_id') or '-'} {summary}".rstrip()
            )
        return "\n".join(lines) if len(lines) > 1 else ""


_BUS: CodexBus | None = None


def get_bus() -> CodexBus:
    global _BUS
    if _BUS is None:
        _BUS = CodexBus()
    return _BUS


def read_bus_events(*, since: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    return get_bus().read_since(after_ts=since, limit=limit)


def post_bus_event(
    slot: str,
    event_type: str,
    payload: dict[str, Any],
    *,
    job_id: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    return get_bus().post(slot, event_type, payload, job_id=job_id, event_id=event_id)


def build_peer_context_block(slot: str, limit: int = 10) -> str:
    return get_bus().build_peer_context_block(slot, limit=limit)
