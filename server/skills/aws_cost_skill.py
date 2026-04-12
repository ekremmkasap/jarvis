from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

try:
    from .aws_common import aws_client, log_cloud_operation, sanitize_text, utcnow
except ImportError:  # pragma: no cover - used by standalone smoke imports
    from aws_common import aws_client, log_cloud_operation, sanitize_text, utcnow  # type: ignore


ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT_DIR / "state"
COST_ALERTS_PATH = STATE_DIR / "cost_alerts.json"


def get_monthly_cost() -> dict[str, Any]:
    start_date = _first_day_of_month(date.today())
    end_date = date.today() + timedelta(days=1)

    try:
        client = aws_client("ce", region_name="us-east-1")
        response = client.get_cost_and_usage(
            TimePeriod={"Start": start_date.isoformat(), "End": end_date.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        )
        payload = _parse_monthly_cost_response(response, start_date=start_date, end_date=end_date)
        log_cloud_operation("cost", "get_monthly_cost", payload)
        return payload
    except Exception as exc:
        mock_payload = _mock_monthly_cost(start_date=start_date, end_date=end_date, error=exc)
        log_cloud_operation("cost", "get_monthly_cost_mock", mock_payload)
        return mock_payload


def get_cost_trend(months: int = 3) -> list[dict[str, Any]]:
    periods = max(int(months or 0), 1)
    start_date = _shift_month(_first_day_of_month(date.today()), -(periods - 1))
    end_date = _shift_month(_first_day_of_month(date.today()), 1)

    try:
        client = aws_client("ce", region_name="us-east-1")
        response = client.get_cost_and_usage(
            TimePeriod={"Start": start_date.isoformat(), "End": end_date.isoformat()},
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        trend = []
        for item in response.get("ResultsByTime", [])[:periods]:
            amount = float((((item.get("Total") or {}).get("UnblendedCost") or {}).get("Amount")) or 0.0)
            trend.append({"month": str(item.get("TimePeriod", {}).get("Start") or ""), "total_usd": round(amount, 2)})
        log_cloud_operation("cost", "get_cost_trend", {"months": periods, "count": len(trend)})
        return trend
    except Exception as exc:
        fallback = _mock_cost_trend(periods, error=exc)
        log_cloud_operation("cost", "get_cost_trend_mock", {"months": periods, "count": len(fallback)})
        return fallback


def get_budget_alerts() -> list[dict[str, Any]]:
    alerts = _saved_threshold_alerts()
    try:
        client = aws_client("budgets", region_name="us-east-1")
        account = str(os.getenv("AWS_ACCOUNT_ID", "") or "").strip()
        if not account:
            return alerts
        response = client.describe_budgets(AccountId=account)
        remote_alerts = []
        for budget in response.get("Budgets", []):
            name = str(budget.get("BudgetName") or "budget")
            limit_usd = float((((budget.get("BudgetLimit") or {}).get("Amount")) or 0.0))
            current_usd = float(
                ((((budget.get("CalculatedSpend") or {}).get("ActualSpend") or {}).get("Amount")) or 0.0)
            )
            pct_used = round((current_usd / limit_usd) * 100, 2) if limit_usd else 0.0
            remote_alerts.append(
                {
                    "name": name,
                    "limit_usd": round(limit_usd, 2),
                    "current_usd": round(current_usd, 2),
                    "pct_used": pct_used,
                }
            )
        if remote_alerts:
            log_cloud_operation("cost", "get_budget_alerts", {"count": len(remote_alerts)})
            return remote_alerts
        return alerts
    except Exception:
        return alerts


def save_alert_threshold(service: str, usd_limit: float) -> dict[str, Any]:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        existing = _load_saved_thresholds()
        saved_entry = {
            "service": str(service or "").strip(),
            "usd_limit": float(usd_limit),
            "updated_at": utcnow().isoformat(),
        }
        remaining = [item for item in existing if item.get("service") != saved_entry["service"]]
        remaining.append(saved_entry)
        COST_ALERTS_PATH.write_text(json.dumps({"thresholds": remaining}, ensure_ascii=True, indent=2), encoding="utf-8")
        result = {"ok": True, "saved": saved_entry}
        log_cloud_operation("cost", "save_alert_threshold", result)
        return result
    except Exception as exc:
        error = sanitize_text(exc)
        log_cloud_operation("cost", "save_alert_threshold_failed", {"service": service, "error": error})
        return {"ok": False, "error": error}


def _parse_monthly_cost_response(response: dict[str, Any], *, start_date: date, end_date: date) -> dict[str, Any]:
    results = response.get("ResultsByTime", [])
    first = results[0] if results else {}
    groups = first.get("Groups", []) if isinstance(first, dict) else []
    by_service: dict[str, float] = {}
    for group in groups:
        keys = group.get("Keys") or []
        service = str(keys[0] if keys else "Other")
        amount = float((((group.get("Metrics") or {}).get("UnblendedCost") or {}).get("Amount")) or 0.0)
        by_service[service] = round(amount, 2)
    total = float((((first.get("Total") or {}).get("UnblendedCost") or {}).get("Amount")) or sum(by_service.values()))
    return {
        "total_usd": round(total, 2),
        "by_service": by_service,
        "period": f"{start_date.isoformat()}:{end_date.isoformat()}",
        "currency": "USD",
    }


def _saved_threshold_alerts() -> list[dict[str, Any]]:
    thresholds = _load_saved_thresholds()
    if not thresholds:
        return []
    current_cost = get_monthly_cost()
    by_service = current_cost.get("by_service", {}) if isinstance(current_cost, dict) else {}
    alerts = []
    for item in thresholds:
        name = str(item.get("service") or "service")
        limit_usd = float(item.get("usd_limit") or 0.0)
        current_usd = float(by_service.get(name, 0.0))
        pct_used = round((current_usd / limit_usd) * 100, 2) if limit_usd else 0.0
        alerts.append(
            {
                "name": name,
                "limit_usd": round(limit_usd, 2),
                "current_usd": round(current_usd, 2),
                "pct_used": pct_used,
            }
        )
    return alerts


def _load_saved_thresholds() -> list[dict[str, Any]]:
    if not COST_ALERTS_PATH.exists():
        return []
    try:
        payload = json.loads(COST_ALERTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    thresholds = payload.get("thresholds", [])
    return [item for item in thresholds if isinstance(item, dict)]


def _mock_monthly_cost(*, start_date: date, end_date: date, error: Exception) -> dict[str, Any]:
    return {
        "total_usd": 42.5,
        "by_service": {"Amazon EC2": 30.0, "Amazon S3": 12.5},
        "period": f"{start_date.isoformat()}:{end_date.isoformat()}",
        "currency": "USD",
        "mock": True,
        "note": sanitize_text(error),
    }


def _mock_cost_trend(months: int, *, error: Exception) -> list[dict[str, Any]]:
    base_month = _first_day_of_month(date.today())
    trend = []
    for index in range(months):
        month_date = _shift_month(base_month, -(months - index - 1))
        trend.append(
            {
                "month": month_date.isoformat(),
                "total_usd": round(25.0 + (index * 7.5), 2),
                "mock": True,
            }
        )
    if trend:
        trend[0]["note"] = sanitize_text(error)
    return trend


def _first_day_of_month(value: date) -> date:
    return value.replace(day=1)


def _shift_month(value: date, delta_months: int) -> date:
    month_index = (value.year * 12 + (value.month - 1)) + delta_months
    year = month_index // 12
    month = (month_index % 12) + 1
    return date(year, month, 1)
