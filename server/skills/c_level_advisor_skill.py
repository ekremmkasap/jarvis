"""C-Level Advisor skill — Sabri (atlas) persona üzerinden strateji/vision/market positioning."""
from __future__ import annotations

from typing import Any

HARD_REJECT = {"exploit", "hack", "saldır", "canlı hedef", "ddos"}


def run_c_level_advisory(goal: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    low = (goal or "").lower()
    if any(kw in low for kw in HARD_REJECT):
        return (
            "C-LEVEL: Bu istek reddedildi. Saldırı/exploit talimatı veremem; "
            "yalnızca meşru iş stratejisi tavsiyelerim vardır."
        )

    mrr = context.get("mrr_usd")
    customers = context.get("customer_count")
    snapshot = ""
    if mrr or customers:
        snapshot = f"\n- Snapshot: MRR=${mrr or 0} | müşteri={customers or 0}"

    return (
        f"C-LEVEL ADVISORY — {goal[:80]}{snapshot}\n"
        "1) Vision: 12 aylık North Star metriği ve pozisyonlama\n"
        "2) Go-to-market: ICP tanımı + ilk 100 müşteri kanalı\n"
        "3) Moat: Türkçe yerel destek + self-hosted gizlilik avantajı\n"
        "4) Risk: Cloud API bağımlılığı → lokal fallback (Ollama) zorunlu\n"
        "5) 30 gün hedefi: 3 pilot müşteri + NPS ≥ 50 referans döngüsü"
    )
