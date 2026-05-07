"""Financial Analyst skill — MRR trend, ARPU, LTV, basit DCF valuation."""
from __future__ import annotations

from typing import Any

try:
    from services.saas_db import SaasDB  # type: ignore
except Exception:
    from server.services.saas_db import SaasDB  # type: ignore


def _fmt(v: float) -> str:
    try:
        return f"{v:,.2f}"
    except Exception:
        return str(v)


def run_financial_analysis(goal: str = "", context: dict[str, Any] | None = None) -> str:
    context = context or {}
    db = SaasDB()
    current = db.get_current_mrr() or {}
    trend = db.get_mrr_trend(days=30)

    mrr = float(current.get("mrr_usd") or 0.0)
    customers = int(current.get("customer_count") or 0)
    churn = float(current.get("churn_rate") or 0.0)
    arpu = (mrr / customers) if customers > 0 else 0.0
    ltv = (arpu / churn) if churn > 0 else 0.0

    growth_30d = 0.0
    if len(trend) >= 2:
        first = float(trend[0].get("mrr_usd") or 0.0) or 1.0
        last = float(trend[-1].get("mrr_usd") or 0.0)
        growth_30d = (last - first) / first * 100.0

    discount = float(context.get("discount_rate", 0.12))
    growth_annual = float(context.get("annual_growth", max(0.0, growth_30d) / 100.0 * 12))
    terminal_growth = 0.03
    annual_mrr = mrr * 12.0
    dcf_value = 0.0
    if discount > terminal_growth:
        denom = discount - terminal_growth
        dcf_value = annual_mrr * (1 + growth_annual) / denom

    lines = [
        f"FINANSAL ANALIZ — {goal or 'SaaS snapshot'}",
        f"- MRR: ${_fmt(mrr)}  (müşteri: {customers})",
        f"- ARPU: ${_fmt(arpu)} | LTV: ${_fmt(ltv)} (churn={churn:.2%})",
        f"- 30g MRR trendi: {growth_30d:+.1f}% ({len(trend)} kayit)",
        f"- DCF fair value: ${_fmt(dcf_value)} (d={discount:.0%}, g={growth_annual:.0%})",
    ]
    return "\n".join(lines)
