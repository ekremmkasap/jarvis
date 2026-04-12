from __future__ import annotations

"""
Multi-Account Manager for JARVIS.
Codex execution truth lives in state/codex-accounts/.
Operator metadata truth lives in config/account_registry.json.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Account:
    """Single provider account."""

    id: str
    provider: str
    auth_token: Optional[str] = None
    codex_home: Optional[str] = None
    runtime_slot: Optional[str] = None
    runtime_account_id: Optional[str] = None
    operator_account_id: str = ""
    operator_label: str = ""
    operator_role: str = ""
    operator_status: str = ""
    operator_notes: str = ""
    operator_daily_limit: Any = None
    operator_weekly_limit: Any = None
    operator_remaining_estimate: Any = None
    operator_last_seen: str = ""
    email: str = ""
    status: str = "active"
    last_used: Optional[str] = None
    failover_priority: int = 0
    last_synced_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AccountManager:
    """Unified account orchestration."""

    ROOT_DIR = Path(__file__).resolve().parent.parent
    CODEX_ACCOUNTS_PATH = ROOT_DIR / "state" / "codex-accounts"
    PUBLIC_REGISTRY_PATH = ROOT_DIR / "config" / "account_registry.json"
    CODEX_ACCOUNT_NAMES = ["atlas", "forge", "nexus", "shield", "spark"]
    ELIGIBLE_STATUSES = {"active", "online", "ready", "standby"}
    BLOCKED_OPERATOR_STATUSES = {
        "quota_exceeded",
        "limited",
        "rate_limited",
        "pending_login",
        "offline",
        "inactive",
        "failed",
    }
    _REDACT_KEYS = {
        "auth_token",
        "password",
        "secret",
        "tokens",
        "access_token",
        "refresh_token",
        "id_token",
        "openai_api_key",
        "authorization",
        "bearer",
    }
    _NON_SLOT_JSON_BASENAMES = {
        "registry",
        "quota",
        "job_queue",
        "_last_active_backup",
        "_last_active_codex_backup",
        "_last_active_opencode_backup",
    }
    SLOT_ROLE_HINTS = {
        "atlas": ("atlas", "manager", "core", "planner", "plan", "architecture", "mimari"),
        "forge": ("forge", "backend", "ops", "server", "api", "deployment", "n8n", "shell"),
        "nexus": ("nexus", "overflow", "reserve", "backup", "archived", "swarm backup"),
        "shield": ("shield", "security", "audit", "redaction", "policy", "guvenlik"),
        "spark": ("spark", "voice", "video", "visual", "hologram", "tts", "stt"),
    }

    def __init__(self, vault_path: str | Path = "server/data/.account_vault"):
        requested_vault_path = Path(vault_path)
        if requested_vault_path.is_absolute():
            self.vault_path = requested_vault_path
        else:
            self.vault_path = self.ROOT_DIR / requested_vault_path
        self.accounts: Dict[str, Account] = {}
        self._ensure_vault()
        self._load_codex_accounts()
        self._load_accounts()

    def _ensure_vault(self) -> None:
        self.vault_path.mkdir(parents=True, exist_ok=True)

    def _vault_file(self) -> Path:
        return self.vault_path / "accounts.json"

    def _normalize_status(self, value: str | None) -> str:
        return str(value or "").strip().lower()

    def _load_json(self, path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _runtime_slot_path(self, slot_id: str) -> Path:
        return self.CODEX_ACCOUNTS_PATH / f"{str(slot_id or '').strip()}.json"

    def _load_public_registry(self) -> list[dict[str, Any]]:
        registry = self._load_json(self.PUBLIC_REGISTRY_PATH)
        accounts = registry.get("accounts")
        if isinstance(accounts, list):
            return [item for item in accounts if isinstance(item, dict)]
        return []

    def _load_runtime_registry(self) -> dict[str, dict[str, Any]]:
        registry_path = self.CODEX_ACCOUNTS_PATH / "registry.json"
        raw_registry = self._load_json(registry_path)
        return {
            slot: value
            for slot, value in raw_registry.items()
            if isinstance(slot, str) and isinstance(value, dict)
        }

    def _iter_codex_slots(self, runtime_registry: dict[str, dict[str, Any]]) -> list[str]:
        slots: list[str] = list(self.CODEX_ACCOUNT_NAMES)
        seen = set(slots)

        for slot in runtime_registry:
            normalized = str(slot).strip()
            if normalized and normalized not in seen:
                seen.add(normalized)
                slots.append(normalized)

        if self.CODEX_ACCOUNTS_PATH.exists():
            for candidate in self.CODEX_ACCOUNTS_PATH.glob("*.json"):
                if candidate.stem in self._NON_SLOT_JSON_BASENAMES or candidate.stem.startswith("_"):
                    continue
                if candidate.stem not in seen:
                    seen.add(candidate.stem)
                    slots.append(candidate.stem)

        return slots

    def _match_operator_metadata(
        self,
        public_registry: list[dict[str, Any]],
        *,
        runtime_slot: str,
        runtime_account_id: str,
    ) -> dict[str, Any]:
        slot_key = runtime_slot.strip().lower()
        runtime_id_key = runtime_account_id.strip().lower()
        known_ids = {slot_key, f"codex_{slot_key}"}

        def _haystack(item: dict[str, Any]) -> str:
            return " ".join(
                [
                    str(item.get("id") or ""),
                    str(item.get("label") or ""),
                    str(item.get("role") or ""),
                    str(item.get("notes") or ""),
                ]
            ).strip().lower()

        for item in public_registry:
            candidate_slot = str(
                item.get("execution_slot")
                or item.get("runtime_slot")
                or ""
            ).strip().lower()
            candidate_runtime_id = str(
                item.get("runtime_account_id")
                or item.get("account_id")
                or ""
            ).strip().lower()
            candidate_id = str(item.get("id") or "").strip().lower()

            if candidate_slot and candidate_slot == slot_key:
                return item
            if runtime_id_key and candidate_runtime_id and candidate_runtime_id == runtime_id_key:
                return item
            if candidate_id and candidate_id in known_ids:
                return item

        hints = self.SLOT_ROLE_HINTS.get(slot_key, ())
        scored_matches: list[tuple[int, dict[str, Any]]] = []
        for item in public_registry:
            haystack = _haystack(item)
            if not haystack:
                continue
            score = sum(1 for hint in hints if hint and hint in haystack)
            if score:
                scored_matches.append((score, item))
        if scored_matches:
            scored_matches.sort(key=lambda pair: pair[0], reverse=True)
            return scored_matches[0][1]

        for item in public_registry:
            candidate_id = str(item.get("id") or "").strip().lower()
            if candidate_id in {f"slot_{slot_key}", f"agent_{slot_key}", slot_key}:
                return item

        return {}

    def _infer_runtime_status(self, account_data: dict[str, Any]) -> str:
        raw_status = self._normalize_status(str(account_data.get("status") or ""))
        if raw_status:
            return raw_status
        if bool(account_data.get("disabled")):
            return "inactive"
        return "active"

    def _effective_status(self, account: Account) -> str:
        runtime_status = self._normalize_status(account.status)
        if runtime_status in {"failed", "inactive"}:
            return runtime_status

        operator_status = self._normalize_status(account.operator_status)
        if operator_status in self.BLOCKED_OPERATOR_STATUSES:
            return operator_status

        return runtime_status or "unknown"

    def _is_selectable(self, account: Account) -> bool:
        effective_status = self._effective_status(account)
        if effective_status in self.ELIGIBLE_STATUSES:
            return True
        return False

    def _priority_sort_key(self, account: Account) -> tuple[int, int, str]:
        selectable_rank = 0 if self._is_selectable(account) else 1
        return (selectable_rank, account.failover_priority, account.id)

    def _load_balance_sort_key(self, account: Account) -> tuple[str, int, str]:
        return (str(account.last_used or ""), account.failover_priority, account.id)

    def _load_codex_accounts(self) -> None:
        if not self.CODEX_ACCOUNTS_PATH.exists():
            return

        runtime_registry = self._load_runtime_registry()
        public_registry = self._load_public_registry()
        slots = self._iter_codex_slots(runtime_registry)

        for priority, slot in enumerate(slots):
            account_json_path = self.CODEX_ACCOUNTS_PATH / f"{slot}.json"
            if not account_json_path.exists():
                continue

            try:
                account_data = json.loads(account_json_path.read_text(encoding="utf-8"))
                if not isinstance(account_data, dict):
                    continue
            except Exception as exc:
                print(f"[ERROR] Failed to load Codex account {slot}: {exc}")
                continue

            runtime_metadata = runtime_registry.get(slot, {})
            runtime_account_id = str(runtime_metadata.get("account_id") or "").strip()
            operator_metadata = self._match_operator_metadata(
                public_registry,
                runtime_slot=slot,
                runtime_account_id=runtime_account_id,
            )
            email = str(
                account_data.get("email")
                or runtime_metadata.get("email")
                or operator_metadata.get("email")
                or f"{slot}@jarvis.local"
            ).strip()

            account = Account(
                id=f"codex_{slot}",
                provider="codex",
                codex_home=str(self.CODEX_ACCOUNTS_PATH / slot),
                runtime_slot=slot,
                runtime_account_id=runtime_account_id or None,
                operator_account_id=str(operator_metadata.get("id") or "").strip(),
                operator_label=str(operator_metadata.get("label") or "").strip(),
                operator_role=str(operator_metadata.get("role") or "").strip(),
                operator_status=str(operator_metadata.get("status") or "").strip(),
                operator_notes=str(operator_metadata.get("notes") or "").strip(),
                operator_daily_limit=operator_metadata.get("daily_limit"),
                operator_weekly_limit=operator_metadata.get("weekly_limit"),
                operator_remaining_estimate=operator_metadata.get("remaining_estimate"),
                operator_last_seen=str(operator_metadata.get("last_seen") or "").strip(),
                email=email,
                status=self._infer_runtime_status(account_data),
                last_used=str(account_data.get("last_used") or "").strip() or None,
                failover_priority=priority,
                last_synced_at=str(runtime_metadata.get("saved_at") or "").strip() or None,
            )
            self.accounts[account.id] = account

    def _load_accounts(self) -> None:
        vault_file = self._vault_file()
        if not vault_file.exists():
            return

        try:
            data = json.loads(vault_file.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[ERROR] Failed to load accounts: {exc}")
            return

        if not isinstance(data, dict):
            return

        for account_id, account_data in data.items():
            if account_id in self.accounts or not isinstance(account_data, dict):
                continue
            try:
                self.accounts[account_id] = Account(**account_data)
            except Exception as exc:
                print(f"[ERROR] Failed to hydrate account {account_id}: {exc}")

    def _save_accounts(self) -> None:
        """Persist only non-Codex accounts to avoid a third Codex truth source."""
        try:
            persisted = {
                account_id: account.to_dict()
                for account_id, account in self.accounts.items()
                if account.provider != "codex"
            }
            self._vault_file().write_text(
                json.dumps(persisted, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            print(f"[ERROR] Failed to save accounts: {exc}")

    def _redact_sensitive(self, data: Any) -> Any:
        def _is_sensitive_key(value: str) -> bool:
            key_name = str(value or "").strip().lower()
            if key_name in self._REDACT_KEYS:
                return True
            sensitive_markers = ("token", "secret", "password", "authorization", "bearer", "api_key")
            return any(marker in key_name for marker in sensitive_markers)

        if isinstance(data, dict):
            redacted: dict[str, Any] = {}
            for key, value in data.items():
                key_name = str(key or "")
                if _is_sensitive_key(key_name):
                    continue
                redacted[key_name] = self._redact_sensitive(value)
            return redacted
        if isinstance(data, list):
            return [self._redact_sensitive(item) for item in data]
        return data

    def _build_slot_payload(self, slot_id: str, account: Account | None) -> dict[str, Any]:
        slot_name = str(slot_id or "").strip().lower()
        runtime_path = self._runtime_slot_path(slot_name)
        runtime_data = self._load_json(runtime_path) if runtime_path.exists() else {}
        effective_status = self._effective_status(account) if account is not None else self._infer_runtime_status(runtime_data)
        payload = {
            "slot_id": slot_name,
            "id": account.id if account is not None else f"codex_{slot_name}",
            "label": account.operator_label if account and account.operator_label else slot_name.upper(),
            "role": account.operator_role if account and account.operator_role else "",
            "status": account.status if account is not None else self._infer_runtime_status(runtime_data),
            "effective_status": effective_status,
            "provider": "codex",
            "runtime_slot": slot_name,
            "runtime_account_id": account.runtime_account_id if account is not None else None,
            "operator_account_id": account.operator_account_id if account is not None else "",
            "operator_status": account.operator_status if account is not None else "",
            "operator_notes": account.operator_notes if account is not None else "",
            "quota_estimate": self.get_quota_estimate(slot_name),
            "daily_limit": account.operator_daily_limit if account is not None else None,
            "weekly_limit": account.operator_weekly_limit if account is not None else None,
            "last_completion": account.operator_last_seen if account is not None else "",
            "last_seen": (account.operator_last_seen if account and account.operator_last_seen else account.last_used if account else "") or "",
            "last_used": account.last_used if account is not None else None,
            "last_synced_at": account.last_synced_at if account is not None else None,
            "codex_home": account.codex_home if account is not None else str(self.CODEX_ACCOUNTS_PATH / slot_name),
            "is_available": False,
            "cooldown_until": None,
            "runtime": runtime_data,
        }
        payload["is_available"] = self.is_slot_available(slot_name)
        try:
            from codex_quota_tracker import cooldown_until
        except Exception:
            try:
                from server.codex_quota_tracker import cooldown_until  # type: ignore
            except Exception:
                cooldown_until = None  # type: ignore[assignment]
        if callable(cooldown_until):
            cooldown = cooldown_until(slot_name)
            payload["cooldown_until"] = cooldown.isoformat() if cooldown else None
        try:
            from codex_orchestrator import get_slot_cooldown_until as get_control_cooldown_until
        except Exception:
            try:
                from server.codex_orchestrator import get_slot_cooldown_until as get_control_cooldown_until  # type: ignore
            except Exception:
                get_control_cooldown_until = None  # type: ignore[assignment]
        if callable(get_control_cooldown_until):
            cooldown = get_control_cooldown_until(slot_name)
            if cooldown is not None:
                payload["cooldown_until"] = cooldown.isoformat()
        return self._redact_sensitive(payload)

    def get_slot(self, slot_id: str) -> dict[str, Any] | None:
        slot_name = str(slot_id or "").strip().lower()
        if not slot_name:
            return None
        account = self.get_codex_account_by_slot(slot_name)
        runtime_path = self._runtime_slot_path(slot_name)
        if account is None and not runtime_path.exists() and slot_name not in self.CODEX_ACCOUNT_NAMES:
            return None
        return self._build_slot_payload(slot_name, account)

    def list_slots(self) -> list[dict[str, Any]]:
        return [payload for payload in (self.get_slot(slot_id) for slot_id in self.CODEX_ACCOUNT_NAMES) if payload is not None]

    def get_active_slot(self) -> dict[str, Any] | None:
        active = self.get_active_account("codex")
        if active is None or not active.runtime_slot:
            return None
        return self.get_slot(active.runtime_slot)

    def set_slot_status(self, slot_id: str, status: str) -> bool:
        slot_name = str(slot_id or "").strip().lower()
        runtime_path = self._runtime_slot_path(slot_name)
        if not slot_name or not runtime_path.exists():
            return False
        runtime_data = self._load_json(runtime_path)
        runtime_data["status"] = str(status or "").strip().lower() or runtime_data.get("status") or "unknown"
        runtime_path.write_text(json.dumps(runtime_data, ensure_ascii=False, indent=2), encoding="utf-8")
        account = self.get_codex_account_by_slot(slot_name)
        if account is not None:
            account.status = str(runtime_data["status"])
        return True

    def get_quota_estimate(self, slot_id: str) -> Any:
        slot_name = str(slot_id or "").strip().lower()
        account = self.get_codex_account_by_slot(slot_name)
        if account is None:
            return None
        return account.operator_remaining_estimate

    def is_slot_available(self, slot_id: str) -> bool:
        slot_name = str(slot_id or "").strip().lower()
        account = self.get_codex_account_by_slot(slot_name)
        if account is None or not self._is_selectable(account):
            return False
        try:
            from codex_quota_tracker import get_quota_tracker
        except Exception:
            try:
                from server.codex_quota_tracker import get_quota_tracker  # type: ignore
            except Exception:
                get_quota_tracker = None  # type: ignore[assignment]
        if not callable(get_quota_tracker):
            return True
        tracker = get_quota_tracker()
        if tracker.is_exhausted(slot_name):
            return False
        cooldown = tracker.cooldown_until(slot_name)
        if cooldown is not None:
            return False
        try:
            from codex_orchestrator import get_slot_cooldown_until as get_control_cooldown_until
        except Exception:
            try:
                from server.codex_orchestrator import get_slot_cooldown_until as get_control_cooldown_until  # type: ignore
            except Exception:
                get_control_cooldown_until = None  # type: ignore[assignment]
        if callable(get_control_cooldown_until):
            return get_control_cooldown_until(slot_name) is None
        return True

    def add_account(self, provider: str, api_key: str, email: str, failover_priority: int = 0) -> str:
        account_id = f"{provider}_{len(self.accounts) + 1}"
        account = Account(
            id=account_id,
            provider=provider,
            auth_token=api_key,
            email=email,
            status="active",
            failover_priority=failover_priority,
        )
        self.accounts[account_id] = account
        self._save_accounts()
        return account_id

    def get_account(self, account_id: str) -> Optional[Account]:
        return self.accounts.get(account_id)

    def get_codex_account_by_slot(self, runtime_slot: str) -> Optional[Account]:
        slot = str(runtime_slot or "").strip()
        if not slot:
            return None
        return self.accounts.get(f"codex_{slot}")

    def get_active_account(self, provider: str) -> Optional[Account]:
        candidates = [
            account
            for account in self.accounts.values()
            if account.provider == provider and self._is_selectable(account)
        ]
        if not candidates:
            return None
        return sorted(candidates, key=self._priority_sort_key)[0]

    def get_all_accounts(self, provider: Optional[str] = None) -> List[Account]:
        accounts = list(self.accounts.values())
        if provider:
            accounts = [account for account in accounts if account.provider == provider]
        return sorted(accounts, key=self._priority_sort_key)

    def mark_used(self, account_id: str) -> bool:
        account = self.accounts.get(account_id)
        if not account:
            return False
        account.last_used = datetime.now().isoformat()
        if account.provider != "codex":
            self._save_accounts()
        return True

    def switch_account(self, account_id: str) -> bool:
        if account_id not in self.accounts:
            return False

        account = self.accounts[account_id]
        provider = account.provider

        if provider == "codex":
            codex_accounts = self.get_all_accounts("codex")
            new_order = [candidate for candidate in codex_accounts if candidate.id == account_id]
            new_order.extend(candidate for candidate in codex_accounts if candidate.id != account_id)
            for index, candidate in enumerate(new_order):
                if self._normalize_status(candidate.status) != "failed":
                    candidate.status = "active"
                candidate.failover_priority = index
                if candidate.id == account_id:
                    candidate.last_used = datetime.now().isoformat()
            return True

        for candidate in self.get_all_accounts(provider):
            if candidate.id != account_id:
                candidate.status = "inactive"

        account.status = "active"
        account.last_used = datetime.now().isoformat()
        self._save_accounts()
        return True

    def mark_failed(self, account_id: str) -> bool:
        account = self.accounts.get(account_id)
        if not account:
            return False

        account.status = "failed"
        if account.provider != "codex":
            self._save_accounts()

        if account.provider == "codex":
            return any(
                candidate.id != account_id and self._is_selectable(candidate)
                for candidate in self.get_all_accounts("codex")
            )

        next_account = self.get_active_account(account.provider)
        if next_account and next_account.id != account_id:
            return self.switch_account(next_account.id)
        return False

    def resolve_codex_accounts(self, requested_slots: list[str]) -> dict[str, Any]:
        normalized_requested: list[str] = []
        seen_slots: set[str] = set()
        for item in requested_slots:
            slot = str(item or "").strip()
            if not slot or slot in seen_slots:
                continue
            seen_slots.add(slot)
            normalized_requested.append(slot)

        available_accounts = [
            account
            for account in self.get_all_accounts("codex")
            if self._is_selectable(account)
        ]
        available_by_slot = {
            str(account.runtime_slot or ""): account
            for account in available_accounts
            if account.runtime_slot
        }

        selected_accounts: list[Account] = []
        selected_ids: set[str] = set()
        unavailable_slots: list[str] = []

        for slot in normalized_requested:
            account = available_by_slot.get(slot)
            if account is None:
                unavailable_slots.append(slot)
                continue
            if account.id in selected_ids:
                continue
            selected_accounts.append(account)
            selected_ids.add(account.id)

        remaining_slots = max(len(normalized_requested) - len(selected_accounts), 0)
        fallback_pool = sorted(
            [account for account in available_accounts if account.id not in selected_ids],
            key=self._load_balance_sort_key,
        )
        while remaining_slots > 0 and fallback_pool:
            account = fallback_pool.pop(0)
            selected_accounts.append(account)
            selected_ids.add(account.id)
            remaining_slots -= 1

        if not selected_accounts and fallback_pool:
            selected_accounts.append(fallback_pool[0])

        selected_slots = [
            str(account.runtime_slot or account.id.replace("codex_", "", 1))
            for account in selected_accounts
        ]
        fallback_slots = [slot for slot in selected_slots if slot not in normalized_requested]

        return {
            "requested_slots": normalized_requested,
            "selected_slots": selected_slots,
            "fallback_slots": fallback_slots,
            "unavailable_slots": unavailable_slots,
            "available_slots": [
                str(account.runtime_slot or account.id.replace("codex_", "", 1))
                for account in available_accounts
            ],
            "accounts": selected_accounts,
        }

    def get_status(self) -> Dict[str, Any]:
        status: dict[str, Any] = {}
        providers = sorted({account.provider for account in self.accounts.values()})

        for provider in providers:
            accounts = self.get_all_accounts(provider)
            active_account = self.get_active_account(provider)
            ready_accounts = [
                account
                for account in accounts
                if self._is_selectable(account)
            ]

            status[provider] = {
                "total": len(accounts),
                "active_account": active_account.id if active_account else None,
                "active_email": active_account.email if active_account else None,
                "ready_accounts": len(ready_accounts),
                "available_slots": [account.runtime_slot for account in ready_accounts if account.runtime_slot],
                "accounts": [
                    {
                        "id": account.id,
                        "email": account.email,
                        "status": self._effective_status(account),
                        "runtime_slot": account.runtime_slot,
                        "runtime_account_id": account.runtime_account_id,
                        "operator_id": account.operator_account_id or None,
                        "operator_label": account.operator_label or None,
                        "operator_role": account.operator_role or None,
                        "operator_status": account.operator_status or None,
                        "quota_estimate": account.operator_remaining_estimate,
                        "last_used": account.last_used,
                    }
                    for account in accounts
                ],
            }

        return status

    def get_credential(self, provider: str) -> Optional[str]:
        account = self.get_active_account(provider)
        if not account:
            return None
        if provider == "codex":
            return account.codex_home
        return account.auth_token

    def get_codex_home(self, account_id: Optional[str] = None) -> Optional[str]:
        if account_id:
            account = self.accounts.get(account_id)
        else:
            account = self.get_active_account("codex")
        return account.codex_home if account else None


_account_manager: Optional[AccountManager] = None


def get_account_manager() -> AccountManager:
    global _account_manager
    if _account_manager is None:
        _account_manager = AccountManager()
    return _account_manager
