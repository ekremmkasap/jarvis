"""
Jarvis E-Ticaret Fırsat Tarayıcısı
Günlük otomatik: eBay + Trendyol'dan karlı ürün fırsatları
APScheduler ile her gün 09:30'da çalışır.
"""

import os
import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

OPPORTUNITY_HISTORY_PATH = Path("state/research/opportunity_history.json")
SCAN_HOUR = int(os.getenv("OPPORTUNITY_SCAN_HOUR", "9"))
SCAN_MINUTE = int(os.getenv("OPPORTUNITY_SCAN_MINUTE", "30"))

_scheduler = None

# Taranan kategoriler (eBay için İngilizce, Trendyol için Türkçe)
EBAY_SCAN_QUERIES = [
    "phone accessories",
    "led lights",
    "fitness equipment",
    "home organizer",
    "pet supplies",
]
TRENDYOL_SCAN_QUERIES = [
    "telefon kılıfı",
    "spor ekipmanı",
    "ev düzenleyici",
    "şarj aleti",
    "kulaklık",
]


def _fetch_trendyol_opportunity(query: str) -> Optional[dict]:
    """Trendyol'dan bir kategori için fırsat verisi çek."""
    try:
        import sys, os

        sys.path.insert(0, os.path.dirname(__file__))
        from trendyol_skill import search_trendyol, analyze_trendyol_results

        raw = search_trendyol(query)
        data = analyze_trendyol_results(raw, query)
        if "error" in data or not data.get("products"):
            return None
        # En çok yorum alan ürünü fırsat olarak işaretle
        top = sorted(data["products"], key=lambda p: p.get("reviews", 0), reverse=True)
        best = top[0] if top else {}
        return {
            "platform": "trendyol",
            "query": query,
            "best_product": best.get("name", "")[:60],
            "avg_price_try": data.get("avg_price", 0),
            "min_price_try": data.get("min_price", 0),
            "max_price_try": data.get("max_price", 0),
            "count": data.get("count", 0),
        }
    except Exception as e:
        logger.warning(f"Trendyol fırsat hatası ({query}): {e}")
        return None


def _fetch_ebay_opportunity(query: str) -> Optional[dict]:
    """eBay'den bir kategori için gerçek satış fiyatı çek."""
    try:
        import sys, os

        sys.path.insert(0, os.path.dirname(__file__))
        from ebay_research import fetch_ebay_sold_prices

        pd = fetch_ebay_sold_prices(query, max_items=15)
        if "error" in pd:
            return None
        return {
            "platform": "ebay",
            "query": query,
            "avg_price_usd": pd["avg_price"],
            "min_price_usd": pd["min_price"],
            "max_price_usd": pd["max_price"],
            "sold_count": pd["count"],
        }
    except Exception as e:
        logger.warning(f"eBay fırsat hatası ({query}): {e}")
        return None


def scan_opportunities(platforms: list = None) -> list:
    """
    Tüm platformlarda fırsat taraması yapar.
    Returns list of opportunity dicts.
    """
    if platforms is None:
        platforms = ["ebay", "trendyol"]

    results = []
    if "trendyol" in platforms:
        for q in TRENDYOL_SCAN_QUERIES[:3]:  # İlk 3 kategori
            opp = _fetch_trendyol_opportunity(q)
            if opp:
                results.append(opp)

    if "ebay" in platforms:
        for q in EBAY_SCAN_QUERIES[:3]:
            opp = _fetch_ebay_opportunity(q)
            if opp:
                results.append(opp)

    return results


def build_opportunity_report(opportunities: list) -> str:
    """Telegram mesajı oluştur."""
    today = date.today().strftime("%d.%m.%Y")
    lines = [f"*Gunluk Firsat Raporu — {today}*\n"]

    trendyol = [o for o in opportunities if o["platform"] == "trendyol"]
    ebay = [o for o in opportunities if o["platform"] == "ebay"]

    if trendyol:
        lines.append("*Trendyol TR Firsatlari*")
        for o in trendyol:
            lines.append(
                f"- {o['query']}: {o['min_price_try']}₺ — {o['max_price_try']}₺ "
                f"(ort. {o['avg_price_try']}₺, {o['count']} urun)"
            )
            if o.get("best_product"):
                lines.append(f"  En iyi: {o['best_product']}")

    if ebay:
        lines.append("\n*eBay Canli Fiyatlar*")
        for o in ebay:
            lines.append(
                f"- {o['query']}: ${o['min_price_usd']} — ${o['max_price_usd']} "
                f"(ort. ${o['avg_price_usd']}, {o['sold_count']} satis)"
            )

    if not opportunities:
        lines.append("Bugun veri cekemedim. Yarin tekrar deniyorum.")

    lines.append("\n/ebay-canli veya /trendyol ile detay alabilirsin.")
    return "\n".join(lines)[:3800]


def save_scan_result(opportunities: list) -> None:
    """Tarama sonucunu geçmişe kaydet (max 30 gün)."""
    OPPORTUNITY_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        history = []
        if OPPORTUNITY_HISTORY_PATH.exists():
            history = json.loads(OPPORTUNITY_HISTORY_PATH.read_text(encoding="utf-8"))
        today = date.today().isoformat()
        history = [h for h in history if h.get("date") != today]
        history.append(
            {
                "date": today,
                "opportunities": opportunities,
                "scanned_at": datetime.utcnow().isoformat(),
            }
        )
        history = sorted(history, key=lambda h: h.get("date", ""))[-30:]
        OPPORTUNITY_HISTORY_PATH.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Kayıt hatası: {e}")


def load_last_scan() -> Optional[dict]:
    """Son tarama kaydını döndür."""
    try:
        if not OPPORTUNITY_HISTORY_PATH.exists():
            return None
        history = json.loads(OPPORTUNITY_HISTORY_PATH.read_text(encoding="utf-8"))
        return history[-1] if history else None
    except Exception:
        return None


def run_opportunity_scan(telegram_send_fn: Callable) -> dict:
    """Tarama yap, rapor oluştur, Telegram'a gönder."""
    try:
        opportunities = scan_opportunities()
        message = build_opportunity_report(opportunities)
        send_status = "failed"
        try:
            telegram_send_fn(message)
            send_status = "sent"
        except Exception as te:
            logger.error(f"Telegram gönderi hatası: {te}")
        save_scan_result(opportunities)
        return {
            "ok": send_status == "sent",
            "count": len(opportunities),
            "send_status": send_status,
        }
    except Exception as e:
        logger.error(f"run_opportunity_scan hatası: {e}")
        return {"ok": False, "count": 0, "send_status": "failed", "error": str(e)}


def start_opportunity_scheduler(telegram_send_fn: Callable) -> bool:
    """APScheduler ile günlük fırsat taraması başlat."""
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        if _scheduler and _scheduler.running:
            return True

        _scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
        _scheduler.add_job(
            func=lambda: run_opportunity_scan(telegram_send_fn),
            trigger=CronTrigger(hour=SCAN_HOUR, minute=SCAN_MINUTE),
            id="opportunity_scan",
            name="Gunluk Firsat Taramasi",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(
            f"Opportunity scheduler basladi: her gun {SCAN_HOUR:02d}:{SCAN_MINUTE:02d}"
        )
        return True
    except ModuleNotFoundError as e:
        logger.warning(f"Scheduler dependency eksik, scheduler devre disi: {e}")
        return False
    except Exception as e:
        logger.error(f"Scheduler baslatma hatasi: {e}")
        return False


def get_scheduler_status() -> dict:
    """Scheduler durumunu döndür."""
    global _scheduler
    if not _scheduler:
        return {"running": False, "next_run": None, "jobs": []}
    jobs = [
        {
            "id": j.id,
            "name": j.name,
            "next_run": str(j.next_run_time) if j.next_run_time else None,
        }
        for j in _scheduler.get_jobs()
    ]
    next_run = jobs[0]["next_run"] if jobs else None
    return {"running": _scheduler.running, "next_run": next_run, "jobs": jobs}
