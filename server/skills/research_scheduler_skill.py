"""
Jarvis Autonomous Research Scheduler Skill
Sabah briefingi: GitHub trending + Reddit + Nitter/Twitter RSS
APScheduler ile arka planda calisir, bridge.py dongusunu bloklamaz.
"""
import os
import json
import hashlib
import logging
from pathlib import Path
from datetime import datetime, date
from typing import Optional, Callable

import feedparser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BRIEF_HISTORY_PATH = Path("state/research/daily_brief_history.json")
SOUL_MD_PATH = Path("server/soul.md")
MAX_HISTORY_DAYS = 30
BRIEF_HOUR = int(os.getenv("BRIEF_HOUR", "8"))
BRIEF_MINUTE = int(os.getenv("BRIEF_MINUTE", "0"))

_scheduler = None  # Module-level BackgroundScheduler instance


def fetch_github_trending(max_items: int = 5) -> list:
    """GitHub trending repo'larini ceker. Hata durumunda [] doner."""
    items = []
    try:
        resp = requests.get(
            "https://github.com/trending",
            headers={"User-Agent": "Jarvis-Research/1.0"},
            timeout=10
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        articles = soup.select("article.Box-row")[:max_items]
        for art in articles:
            h2 = art.select_one("h2 a")
            if not h2:
                continue
            repo_path = h2.get("href", "").strip("/")
            title = repo_path.replace("/", " / ")
            url = f"https://github.com/{repo_path}"
            desc_el = art.select_one("p")
            summary = desc_el.get_text(strip=True)[:280] if desc_el else ""
            item_id = hashlib.sha256(url.encode()).hexdigest()[:16]
            items.append({
                "id": item_id,
                "source": "github",
                "title": title,
                "url": url,
                "summary": summary,
                "fetched_at": datetime.utcnow().isoformat(),
                "included_in_brief": None,
            })
    except Exception as e:
        logger.warning(f"GitHub trending fetch failed: {e}")
    return items


def fetch_reddit_top(subreddits: list = None, max_items: int = 5) -> list:
    """Reddit gunluk top post'larini ceker. Hata -> []"""
    if subreddits is None:
        subreddits = ["programming", "MachineLearning", "artificial"]
    items = []
    for sub in subreddits:
        try:
            url = f"https://www.reddit.com/r/{sub}/top.json?limit={max_items}&t=day"
            resp = requests.get(
                url,
                headers={"User-Agent": "Jarvis-Research/1.0"},
                timeout=10
            )
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("children", [])[:max_items]
            for post in posts:
                p = post.get("data", {})
                title = p.get("title", "")
                post_url = p.get("url", "")
                item_id = hashlib.sha256(post_url.encode()).hexdigest()[:16]
                items.append({
                    "id": item_id,
                    "source": "reddit",
                    "title": f"r/{sub}: {title}",
                    "url": post_url,
                    "summary": p.get("selftext", "")[:280],
                    "fetched_at": datetime.utcnow().isoformat(),
                    "included_in_brief": None,
                })
        except Exception as e:
            logger.warning(f"Reddit r/{sub} fetch failed: {e}")
    return items[:max_items]


def fetch_twitter_nitter(query: str = "python AI 2026", max_items: int = 5) -> list:
    """Nitter RSS uzerinden Twitter/X arama sonuclari. Fail -> []"""
    items = []
    nitter_instances = [
        "https://nitter.poast.org",
        "https://nitter.privacydev.net",
    ]
    for base in nitter_instances:
        try:
            import urllib.parse
            rss_url = f"{base}/search/rss?q={urllib.parse.quote(query)}"
            feed = feedparser.parse(rss_url)
            if feed.bozo and not feed.entries:
                continue
            for entry in feed.entries[:max_items]:
                item_id = hashlib.sha256(entry.get("link", "").encode()).hexdigest()[:16]
                items.append({
                    "id": item_id,
                    "source": "twitter",
                    "title": entry.get("title", "")[:120],
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:280],
                    "fetched_at": datetime.utcnow().isoformat(),
                    "included_in_brief": None,
                })
            if items:
                break
        except Exception as e:
            logger.warning(f"Nitter {base} fetch failed: {e}")
    return items[:max_items]


def load_soul_context() -> dict:
    """
    soul.md'den Arastirma Brief Prefix bolumunu okur.
    Dosya yoksa veya bolum yoksa varsayilan doner.
    """
    default = {"prefix": "", "tone": "Turkce, samimi"}
    try:
        soul_path = SOUL_MD_PATH
        if not soul_path.exists():
            for candidate in [Path("config/soul.md"), Path("soul.md"), Path("server/soul.md")]:
                if candidate.exists():
                    soul_path = candidate
                    break
            else:
                return default

        content = soul_path.read_text(encoding="utf-8")
        prefix = ""
        in_section = False
        for line in content.splitlines():
            if line.strip() == "## Arastirma Brief Prefix":
                in_section = True
                continue
            if in_section:
                if line.startswith("## "):
                    break
                prefix += line + "\n"
        return {"prefix": prefix.strip(), "tone": "Turkce, samimi"}
    except Exception as e:
        logger.warning(f"soul.md okunamadi: {e}")
        return default


def build_brief_message(items: list, soul_prefix: str = "") -> str:
    """
    Turkce Telegram mesaji olusturur.
    soul_prefix: soul.md'den gelen kisilik prefix'i
    Max 3000 karakter.
    """
    today = date.today().strftime("%d.%m.%Y")
    lines = []
    if soul_prefix:
        lines.append(soul_prefix)
    lines.append(f"*Sabah Briefingi — {today}*\n")

    by_source = {"github": [], "reddit": [], "twitter": []}
    for item in items:
        src = item.get("source", "other")
        if src in by_source:
            by_source[src].append(item)

    source_labels = {"github": "GitHub Trending", "reddit": "Reddit", "twitter": "X/Twitter"}
    for src, label in source_labels.items():
        src_items = by_source[src]
        if not src_items:
            continue
        lines.append(f"\n*{label}*")
        for item in src_items[:3]:
            title = item.get("title", "")[:60]
            url = item.get("url", "")
            lines.append(f"- {title}\n  {url}")

    if not any(by_source.values()):
        lines.append("Bugun icerik cekemedim, yarin tekrar deniyorum.")

    msg = "\n".join(lines)
    return msg[:3000]


def save_daily_brief(brief: dict) -> None:
    """DailyBrief kaydini history dosyasina ekler. Max 30 gun saklar."""
    BRIEF_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        history = []
        if BRIEF_HISTORY_PATH.exists():
            history = json.loads(BRIEF_HISTORY_PATH.read_text(encoding="utf-8"))
        today = brief.get("date", date.today().isoformat())
        history = [b for b in history if b.get("date") != today]
        history.append(brief)
        history = sorted(history, key=lambda b: b.get("date", ""))[-MAX_HISTORY_DAYS:]
        BRIEF_HISTORY_PATH.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Brief kaydetme hatasi: {e}")


def load_today_brief() -> Optional[dict]:
    """Bugünün brief kaydini doner, yoksa None."""
    try:
        if not BRIEF_HISTORY_PATH.exists():
            return None
        history = json.loads(BRIEF_HISTORY_PATH.read_text(encoding="utf-8"))
        today = date.today().isoformat()
        for brief in reversed(history):
            if brief.get("date") == today:
                return brief
    except Exception as e:
        logger.warning(f"Brief yukleme hatasi: {e}")
    return None


def run_morning_brief(telegram_send_fn: Callable) -> dict:
    """
    Tum kaynaklari toplar, brief olusturur, Telegram'a gonderir.
    Hicbir exception disariya sipmaz.
    Returns: {ok: bool, items_count: int, send_status: str}
    """
    try:
        soul_ctx = load_soul_context()
        items = []
        items.extend(fetch_github_trending(max_items=5))
        items.extend(fetch_reddit_top(max_items=5))
        items.extend(fetch_twitter_nitter(max_items=5))

        message = build_brief_message(items, soul_prefix=soul_ctx.get("prefix", ""))
        send_status = "failed"
        try:
            telegram_send_fn(message)
            send_status = "sent"
        except Exception as te:
            logger.error(f"Telegram gonderme hatasi: {te}")

        brief = {
            "date": date.today().isoformat(),
            "items": [i["id"] for i in items],
            "items_count": len(items),
            "message_text": message,
            "sent_at": datetime.utcnow().isoformat() if send_status == "sent" else None,
            "send_status": send_status,
        }
        save_daily_brief(brief)
        return {"ok": send_status == "sent", "items_count": len(items), "send_status": send_status}
    except Exception as e:
        logger.error(f"run_morning_brief hatasi: {e}")
        return {"ok": False, "items_count": 0, "send_status": "failed", "error": str(e)}


def start_scheduler(telegram_send_fn: Callable) -> bool:
    """
    BackgroundScheduler baslatir. Her gun BRIEF_HOUR:BRIEF_MINUTE'de brief calistirir.
    Windows uyumlu (APScheduler 3.x BackgroundScheduler).
    Returns True if started successfully.
    """
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        if _scheduler and _scheduler.running:
            logger.info("Research scheduler zaten calisiyor")
            return True

        _scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
        _scheduler.add_job(
            func=lambda: run_morning_brief(telegram_send_fn),
            trigger=CronTrigger(hour=BRIEF_HOUR, minute=BRIEF_MINUTE),
            id="morning_brief",
            name="Sabah Arastirma Briefingi",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(f"Research scheduler basladi: her gun {BRIEF_HOUR:02d}:{BRIEF_MINUTE:02d}")
        return True
    except Exception as e:
        logger.error(f"Scheduler baslatma hatasi: {e}")
        return False


def get_scheduler_status() -> dict:
    """Scheduler durumunu doner."""
    global _scheduler
    if not _scheduler:
        return {"running": False, "next_run": None, "jobs": []}
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
        })
    return {"running": _scheduler.running, "jobs": jobs}
