from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "config" / "account_registry.json"
SESSION_PROFILES_PATH = ROOT / "config" / "session_profiles.json"
SESSION_ROLES_PATH = ROOT / "config" / "session_roles.yaml"

ALLOWED_UPDATE_FIELDS = {
    "label",
    "provider",
    "role",
    "status",
    "execution_slot",
    "runtime_account_id",
    "daily_limit",
    "weekly_limit",
    "remaining_estimate",
    "last_seen",
    "notes",
}

PUBLIC_ACCOUNT_FIELDS = {
    "id",
    "label",
    "provider",
    "role",
    "status",
    "execution_slot",
    "runtime_account_id",
    "daily_limit",
    "weekly_limit",
    "remaining_estimate",
    "last_seen",
    "notes",
}

DEFAULT_ACCOUNT = {
    "id": "",
    "label": "",
    "provider": "local",
    "role": "-",
    "status": "unknown",
    "execution_slot": "",
    "runtime_account_id": "",
    "daily_limit": "-",
    "weekly_limit": "-",
    "remaining_estimate": "-",
    "last_seen": "-",
    "notes": "",
}


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _coerce_field_value(field: str, value: Any) -> str | int:
    text = str(value or "").strip()
    if field in {"daily_limit", "weekly_limit"}:
        if not text:
            return "-"
        if text.isdigit():
            return int(text)
        return text
    return text or "-"


def _load_session_profile_defaults() -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(SESSION_PROFILES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

    profiles = data.get("profiles") if isinstance(data, dict) else []
    result: dict[str, dict[str, Any]] = {}
    for item in profiles or []:
        if not isinstance(item, dict):
            continue
        profile_id = str(item.get("id") or "").strip()
        if not profile_id:
            continue
        result[profile_id] = {
            "id": profile_id,
            "label": str(item.get("role") or profile_id).strip() or profile_id,
            "provider": "local",
            "role": str(item.get("role") or "-").strip() or "-",
            "status": str(item.get("status") or "unknown").strip() or "unknown",
            "notes": str(item.get("notes") or "").strip(),
        }
    return result


def _load_role_aliases() -> dict[str, str]:
    try:
        lines = SESSION_ROLES_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}

    aliases: dict[str, str] = {}
    current_role = ""
    in_roles = False
    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.strip() == "roles:":
            in_roles = True
            continue
        if not in_roles:
            continue
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            current_role = line.strip()[:-1].strip()
            continue
        if current_role and line.startswith("    assigned_profile:"):
            aliases[current_role] = line.split(":", 1)[1].strip().strip('"\'')
    return aliases


def _resolve_account_id(account_id: str) -> str:
    key = str(account_id or "").strip()
    if not key:
        return ""
    aliases = _load_role_aliases()
    return aliases.get(key, key)


def _normalize_account(raw: Any) -> dict[str, Any]:
    account = dict(DEFAULT_ACCOUNT)
    if isinstance(raw, dict):
        for key in account:
            if key in raw:
                account[key] = raw[key]
    account["id"] = str(account.get("id") or "").strip()
    account["label"] = str(account.get("label") or account["id"] or "").strip()
    account["provider"] = str(account.get("provider") or "local").strip() or "local"
    account["role"] = str(account.get("role") or "-").strip() or "-"
    account["status"] = str(account.get("status") or "unknown").strip() or "unknown"
    account["execution_slot"] = str(account.get("execution_slot") or "").strip()
    account["runtime_account_id"] = str(account.get("runtime_account_id") or "").strip()
    account["daily_limit"] = _coerce_field_value("daily_limit", account.get("daily_limit"))
    account["weekly_limit"] = _coerce_field_value("weekly_limit", account.get("weekly_limit"))
    account["remaining_estimate"] = str(account.get("remaining_estimate") or "-").strip() or "-"
    account["last_seen"] = str(account.get("last_seen") or "-").strip() or "-"
    account["notes"] = str(account.get("notes") or "").strip()
    return account


def load_account_registry() -> dict[str, list[dict[str, Any]]]:
    defaults = _load_session_profile_defaults()
    try:
        if REGISTRY_PATH.exists():
            data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            accounts = data.get("accounts") if isinstance(data, dict) else []
            normalized = []
            seen_ids: set[str] = set()
            for item in accounts or []:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("id") or "").strip()
                merged = dict(defaults.get(item_id, {}))
                merged.update(item)
                account = _normalize_account(merged)
                if account["id"]:
                    seen_ids.add(account["id"])
                normalized.append(account)
            for profile_id, profile_defaults in defaults.items():
                if profile_id not in seen_ids:
                    normalized.append(_normalize_account(profile_defaults))
            return {"accounts": normalized}
    except Exception:
        pass
    return {"accounts": [_normalize_account(item) for item in defaults.values()]}


def save_account_registry(data: dict[str, Any]) -> None:
    accounts = data.get("accounts") if isinstance(data, dict) else []
    normalized = [_normalize_account(item) for item in (accounts or []) if isinstance(item, dict)]
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps({"accounts": normalized}, ensure_ascii=False, indent=2), encoding="utf-8")


def get_public_account_registry() -> dict[str, list[dict[str, Any]]]:
    registry = load_account_registry()
    accounts = registry.get("accounts") if isinstance(registry, dict) else []
    public_accounts: list[dict[str, Any]] = []
    for item in accounts or []:
        account = _normalize_account(item)
        public_accounts.append({key: account.get(key) for key in PUBLIC_ACCOUNT_FIELDS})
    return {"accounts": public_accounts}


def build_account_status_report() -> str:
    registry = load_account_registry()
    accounts = registry.get("accounts") or []
    if not accounts:
        return "HESAP DURUM\n\nKayitli hesap yok. /hesap-guncelle ile ilk kaydi ekleyebilirsin."

    normalized = [_normalize_account(item) for item in accounts]

    def _status_bucket(value: str) -> str:
        text = str(value or "").strip().lower()
        if text in {"active", "online", "ready", "standby", "aktif"}:
            return "aktif"
        if text in {"quota_exceeded", "limitte", "limited", "rate_limited"}:
            return "limitte"
        if text in {"offline_pending", "idle", "paused", "unknown", "inactive"}:
            return "bosta"
        return "bosta"

    def _short(value: Any, limit: int = 48) -> str:
        text = str(value or "-").strip() or "-"
        return text if len(text) <= limit else text[: limit - 3] + "..."

    total = len(normalized)
    active_count = sum(1 for account in normalized if _status_bucket(account.get("status")) == "aktif")
    limited_count = sum(1 for account in normalized if _status_bucket(account.get("status")) == "limitte")
    idle_count = total - active_count - limited_count
    limited_accounts = [
        _short(account.get("label") or account.get("id") or "-", 32)
        for account in normalized
        if _status_bucket(account.get("status")) == "limitte"
    ]

    lines = ["HESAP DURUM", f"Toplam hesap: {total} | aktif: {active_count} | limitte: {limited_count} | bosta: {idle_count}", ""]
    if limited_accounts:
        lines.append(f"[LIMITTE HESAPLAR] {', '.join(limited_accounts[:4])}")
        lines.append("")
    for account in sorted(normalized, key=lambda item: (0 if _status_bucket(item.get("status")) == "aktif" else 1 if _status_bucket(item.get("status")) == "limitte" else 2, str(item.get("label") or item.get("id") or "").lower())):
        label = _short(account.get("label") or account.get("id") or "-")
        account_id = _short(account.get("id") or "-")
        role = _short(account.get("role") or "-")
        provider = _short(account.get("provider") or "local", 24)
        status = _short(account.get("status") or "unknown", 24)
        remaining = _short(account.get("remaining_estimate") or "-", 24)
        last_seen = _short(account.get("last_seen") or "-")
        daily_limit = _short(account.get("daily_limit") or "-", 16)
        weekly_limit = _short(account.get("weekly_limit") or "-", 16)
        note = _short(account.get("notes") or "-", 72)
        lines.append(f"- {label} ({account_id})")
        lines.append(f"  rol: {role} | saglayici: {provider} | durum: {status}")
        lines.append(f"  gunluk: {daily_limit} | haftalik: {weekly_limit} | kalan tahmini kredi: {remaining}")
        lines.append(f"  son gorulme: {last_seen}")
        lines.append(f"  not: {note}")
        lines.append("")
    return "\n".join(lines).rstrip()


def update_account_field(account_id: str, field: str, value: Any) -> str:
    account_key = _resolve_account_id(account_id)
    field_name = str(field or "").strip().lower()
    if not account_key:
        return "Hesap ID gerekli."
    if field_name not in ALLOWED_UPDATE_FIELDS:
        return "Izin verilmeyen alan."

    registry = load_account_registry()
    accounts = registry.get("accounts") or []
    defaults = _load_session_profile_defaults()
    account = next((item for item in accounts if str(item.get("id") or "").strip().lower() == account_key.lower()), None)
    if account is None:
        seed = dict(defaults.get(account_key, {}))
        seed.setdefault("id", account_key)
        seed.setdefault("label", account_key)
        account = _normalize_account(seed)
        accounts.append(account)

    account[field_name] = _coerce_field_value(field_name, value)
    if field_name != "last_seen":
        account["last_seen"] = _now_str()
    save_account_registry({"accounts": accounts})
    return f"Hesap guncellendi: {account['id']} | {field_name}={account[field_name]}"
