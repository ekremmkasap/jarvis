"""
Jarvis Multi-Tenant Manager.
Her musteri icin izole config + bellek + kisilik yonetimi.
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

REPO_BASE_DIR = Path(__file__).resolve().parents[1]


class TenantManager:
    BASE_DIR = REPO_BASE_DIR / "data" / "customers"
    SOUL_TEMPLATE = REPO_BASE_DIR / "config" / "soul_template.md"

    def __init__(self, base_dir: Path | None = None, soul_template: Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir is not None else self.BASE_DIR
        self.soul_template = Path(soul_template) if soul_template is not None else self.SOUL_TEMPLATE

    def _normalize_email(self, email: str) -> str:
        return str(email or "").strip().lower()

    def _tenant_slug(self, email: str) -> str:
        normalized_email = self._normalize_email(email)
        return re.sub(r"[^a-z0-9@._-]+", "-", normalized_email).strip("-")

    def _tenant_dir(self, email: str) -> Path:
        return self.base_dir / self._tenant_slug(email)

    def _config_path(self, email: str) -> Path:
        return self._tenant_dir(email) / "config.json"

    def _load_config(self, path: Path) -> dict | None:
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return data if isinstance(data, dict) else None

    def _render_soul(self, email: str, plan: str, created_at: str) -> str:
        if not self.soul_template.exists():
            return (
                "# Jarvis Musteri Soul\n"
                f"Musteri Profili: {email}\n"
                f"Plan: {plan}\n"
                f"Kurulum Tarihi: {created_at}\n"
            )

        template = self.soul_template.read_text(encoding="utf-8")
        return (
            template.replace("{CUSTOMER_EMAIL}", email)
            .replace("{CUSTOMER_NAME}", email)
            .replace("{PLAN}", plan)
            .replace("{CREATED_AT}", created_at)
        )

    def _iter_configs(self, *, include_inactive: bool) -> list[dict]:
        if not self.base_dir.exists():
            return []

        configs: list[dict] = []
        for entry in sorted(self.base_dir.iterdir()):
            if not entry.is_dir():
                continue
            config = self._load_config(entry / "config.json")
            if not config:
                continue
            if not include_inactive and config.get("status") != "active":
                continue
            configs.append(config)
        return configs

    def create_tenant(self, email: str, plan: str) -> dict:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            return {"ok": False, "error": "Email gerekli."}

        created_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        tenant_dir = self._tenant_dir(normalized_email)
        tenant_dir.mkdir(parents=True, exist_ok=True)

        config = {
            "email": normalized_email,
            "plan": str(plan or "starter"),
            "created_at": created_at,
            "status": "active",
            "bot_token": None,
        }
        (tenant_dir / "config.json").write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (tenant_dir / "soul.md").write_text(
            self._render_soul(normalized_email, config["plan"], created_at),
            encoding="utf-8",
        )
        sqlite3.connect(str(tenant_dir / "memory.db")).close()

        return {"ok": True, "tenant_dir": str(tenant_dir), "config": config}

    def get_tenant(self, email: str) -> dict | None:
        return self._load_config(self._config_path(email))

    def list_tenants(self) -> list[dict]:
        return self._iter_configs(include_inactive=False)

    def deactivate_tenant(self, email: str) -> bool:
        config_path = self._config_path(email)
        config = self._load_config(config_path)
        if not config:
            return False
        config["status"] = "inactive"
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True

    def get_tenant_stats(self) -> dict:
        all_tenants = self._iter_configs(include_inactive=True)
        plan_distribution: dict[str, int] = {}
        this_month = datetime.now(timezone.utc).strftime("%Y-%m")
        new_this_month = 0

        for tenant in all_tenants:
            plan = str(tenant.get("plan", "unknown")).lower()
            plan_distribution[plan] = plan_distribution.get(plan, 0) + 1
            if str(tenant.get("created_at", "")).startswith(this_month):
                new_this_month += 1

        return {
            "total_customers": len(all_tenants),
            "active_customers": sum(
                1 for tenant in all_tenants if tenant.get("status") == "active"
            ),
            "plan_distribution": plan_distribution,
            "new_this_month": new_this_month,
        }


_DEFAULT_MANAGER = TenantManager()


def create_tenant(email: str, plan: str) -> dict:
    return _DEFAULT_MANAGER.create_tenant(email, plan)


def get_tenant(email: str) -> dict | None:
    return _DEFAULT_MANAGER.get_tenant(email)


def list_tenants() -> list[dict]:
    return _DEFAULT_MANAGER.list_tenants()


def deactivate_tenant(email: str) -> bool:
    return _DEFAULT_MANAGER.deactivate_tenant(email)


def get_tenant_stats() -> dict:
    return _DEFAULT_MANAGER.get_tenant_stats()


def format_tenant_list() -> str:
    tenants = list_tenants()
    if not tenants:
        return "Henuz aktif musteri yok."
    lines = [f"*Musteriler ({len(tenants)} aktif)*"]
    for tenant in tenants:
        lines.append(
            f"- {tenant['email']} | {tenant.get('plan', '?')} | {tenant.get('created_at', '')[:10]}"
        )
    return "\n".join(lines)


def format_stats() -> str:
    stats = get_tenant_stats()
    lines = [
        "*Jarvis Admin Stats*",
        f"Toplam musteri: {stats['total_customers']}",
        f"Aktif musteri: {stats['active_customers']}",
        f"Bu ay eklenenler: {stats['new_this_month']}",
        "Plan dagilimi:",
    ]
    for plan, count in sorted(stats["plan_distribution"].items()):
        lines.append(f"- {plan}: {count}")
    return "\n".join(lines)
