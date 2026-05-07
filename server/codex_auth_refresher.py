from __future__ import annotations

import base64
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any
from urllib import parse, request


ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = ROOT_DIR / "state" / "codex-accounts"
LOG_DIR = ROOT_DIR / "server" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

SLOT_ORDER = ("atlas", "forge", "nexus", "shield", "spark")
AUTH_REFRESH_INTERVAL_SECONDS = 6 * 60 * 60
REFRESH_THRESHOLD = timedelta(hours=48)
OAUTH_TOKEN_URL = "https://auth.openai.com/oauth/token"

LOGGER = logging.getLogger("jarvis.codex_auth_refresher")
if not LOGGER.handlers:
    LOGGER.setLevel(logging.INFO)
    file_handler = logging.FileHandler(LOG_DIR / "codex_auth_refresher.log", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    LOGGER.addHandler(file_handler)
    LOGGER.propagate = False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None = None) -> str:
    return (value or _now()).replace(microsecond=0).isoformat()


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = str(token or "").split(".")
    if len(parts) < 2:
        return {}
    payload = parts[1]
    padding = "=" * ((4 - len(payload) % 4) % 4)
    try:
        raw = base64.urlsafe_b64decode((payload + padding).encode("ascii"))
        decoded = json.loads(raw.decode("utf-8"))
        return decoded if isinstance(decoded, dict) else {}
    except Exception:
        return {}


def get_access_token_expiry(token: str) -> datetime | None:
    payload = _decode_jwt_payload(token)
    exp = payload.get("exp")
    if exp in (None, ""):
        return None
    try:
        return datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except Exception:
        return None


def get_client_id(token: str) -> str:
    payload = _decode_jwt_payload(token)
    return str(payload.get("client_id") or "").strip()


def should_refresh_payload(
    auth_payload: dict[str, Any],
    *,
    now: datetime | None = None,
    threshold: timedelta = REFRESH_THRESHOLD,
) -> bool:
    current_time = now or _now()
    access_token = (
        auth_payload.get("tokens", {}).get("access_token")
        if isinstance(auth_payload.get("tokens"), dict)
        else ""
    )
    expiry = get_access_token_expiry(str(access_token or ""))
    if expiry is None:
        return True
    return expiry <= current_time + threshold


def sanitize_auth_payload(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        from account_manager import get_account_manager
    except Exception:
        try:
            from server.account_manager import get_account_manager  # type: ignore
        except Exception:
            get_account_manager = None  # type: ignore[assignment]

    if callable(get_account_manager):
        return get_account_manager()._redact_secrets(payload)
    return {}


def write_auth_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        delete=False,
        dir=str(path.parent),
        suffix=".tmp",
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def load_auth_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def request_token_refresh(
    *,
    refresh_token: str,
    client_id: str,
    opener=None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    request_body = parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }
    ).encode("utf-8")
    opener_fn = opener or request.urlopen
    http_request = request.Request(
        OAUTH_TOKEN_URL,
        data=request_body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with opener_fn(http_request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def refresh_auth_file(
    auth_path: Path,
    *,
    now: datetime | None = None,
    opener=None,
) -> dict[str, Any]:
    payload = load_auth_payload(auth_path)
    tokens = payload.get("tokens") if isinstance(payload.get("tokens"), dict) else {}
    refresh_token = str(tokens.get("refresh_token") or "").strip()
    access_token = str(tokens.get("access_token") or "").strip()
    client_id = get_client_id(access_token)
    if not refresh_token:
        raise ValueError("refresh_token missing")
    if not client_id:
        raise ValueError("client_id missing")

    refreshed = request_token_refresh(
        refresh_token=refresh_token,
        client_id=client_id,
        opener=opener,
    )
    if not refreshed.get("access_token"):
        raise ValueError("access_token missing in refresh response")

    updated_tokens = dict(tokens)
    updated_tokens["access_token"] = refreshed["access_token"]
    if refreshed.get("refresh_token"):
        updated_tokens["refresh_token"] = refreshed["refresh_token"]
    if refreshed.get("id_token"):
        updated_tokens["id_token"] = refreshed["id_token"]

    payload["tokens"] = updated_tokens
    payload["last_refresh"] = _iso(now)
    write_auth_payload(auth_path, payload)
    return payload


def _auth_path_for_slot(slot: str, *, root_dir: Path = ROOT_DIR) -> Path:
    candidate = root_dir / "state" / "codex-accounts" / slot / ".codex" / "auth.json"
    if candidate.exists():
        return candidate
    return root_dir / "state" / "codex-accounts" / f"{slot}.json"


def _status_for_slot(slot: str, *, root_dir: Path = ROOT_DIR) -> dict[str, Any]:
    auth_path = _auth_path_for_slot(slot, root_dir=root_dir)
    payload = load_auth_payload(auth_path)
    tokens = payload.get("tokens") if isinstance(payload.get("tokens"), dict) else {}
    expiry = get_access_token_expiry(str(tokens.get("access_token") or ""))
    hours = None
    if expiry is not None:
        hours = round((expiry - _now()).total_seconds() / 3600, 2)
    return {
        "slot": slot,
        "auth_path": str(auth_path),
        "expires_at": expiry.isoformat() if expiry else None,
        "expires_in_hours": hours,
        "last_refresh": payload.get("last_refresh"),
        "needs_refresh": should_refresh_payload(payload) if payload else True,
    }


class CodexAuthRefresher:
    def __init__(self, *, root_dir: Path | None = None) -> None:
        self.root_dir = Path(root_dir or ROOT_DIR)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._lock = threading.RLock()

    def get_auth_status(self) -> list[dict[str, Any]]:
        return [_status_for_slot(slot, root_dir=self.root_dir) for slot in SLOT_ORDER]

    def refresh_slot(self, slot: str) -> dict[str, Any]:
        auth_path = _auth_path_for_slot(slot, root_dir=self.root_dir)
        payload = load_auth_payload(auth_path)
        if not payload:
            result = {"slot": slot, "status": "missing", "auth_path": str(auth_path)}
            LOGGER.warning("auth refresh skipped %s", json.dumps(result, ensure_ascii=False))
            return result

        if not should_refresh_payload(payload):
            result = {
                "slot": slot,
                "status": "fresh",
                "auth_path": str(auth_path),
                "last_refresh": payload.get("last_refresh"),
            }
            LOGGER.info("auth refresh skipped %s", json.dumps(result, ensure_ascii=False))
            return result

        try:
            refreshed = refresh_auth_file(auth_path, now=_now())
            result = {
                "slot": slot,
                "status": "refreshed",
                "auth_path": str(auth_path),
                "payload": sanitize_auth_payload(refreshed),
            }
            LOGGER.info("auth refresh ok %s", json.dumps(result, ensure_ascii=False))
            return result
        except Exception as exc:
            try:
                from account_manager import get_account_manager
            except Exception:
                from server.account_manager import get_account_manager  # type: ignore

            get_account_manager().set_operator_status(slot, "pending_login")
            result = {
                "slot": slot,
                "status": "failed",
                "auth_path": str(auth_path),
                "error": str(exc),
                "payload": sanitize_auth_payload(payload),
            }
            LOGGER.warning("auth refresh failed %s", json.dumps(result, ensure_ascii=False))
            return result

    def refresh_due_slots(self) -> list[dict[str, Any]]:
        return [self.refresh_slot(slot) for slot in SLOT_ORDER]

    def _run_forever(self) -> None:
        while not self._stop_event.is_set():
            self.refresh_due_slots()
            self._stop_event.wait(AUTH_REFRESH_INTERVAL_SECONDS)

    def start_background(self) -> bool:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return False
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._run_forever,
                daemon=True,
                name="codex-auth-refresher",
            )
            self._thread.start()
            return True

    def stop_background(self) -> None:
        self._stop_event.set()


_REFRESHER: CodexAuthRefresher | None = None


def get_refresher() -> CodexAuthRefresher:
    global _REFRESHER
    if _REFRESHER is None:
        _REFRESHER = CodexAuthRefresher()
    return _REFRESHER


def start_background() -> bool:
    return get_refresher().start_background()


def stop_background() -> None:
    get_refresher().stop_background()


def get_auth_status_payload() -> list[dict[str, Any]]:
    return get_refresher().get_auth_status()
