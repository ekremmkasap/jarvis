"""
Jarvis Instagram Takip Skill
Hesap takip listesi yonetimi + periyodik yeni icerik kontrolu
instaloader kullanir - public profiller icin login gerekmez
"""
import json
import logging
import re
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

logger = logging.getLogger(__name__)

WATCH_LIST_PATH = Path("state/research/watch_list.json")
MAX_WATCHED_ACCOUNTS = 50
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.]{1,30}$')

_instagram_scheduler = None


def _load_watch_list() -> list:
    try:
        if WATCH_LIST_PATH.exists():
            return json.loads(WATCH_LIST_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return []


def _save_watch_list(accounts: list) -> None:
    WATCH_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    WATCH_LIST_PATH.write_text(
        json.dumps(accounts, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def add_watched_account(username: str) -> dict:
    """
    Instagram hesabini takip listesine ekler.
    username: @ olmadan, sadece alfanumerik + _ + .
    Returns: {ok: bool, message: str}
    """
    username = username.lstrip("@").strip()

    if not USERNAME_PATTERN.match(username):
        return {"ok": False, "message": f"Gecersiz kullanici adi: @{username}"}

    accounts = _load_watch_list()
    active_count = sum(1 for a in accounts if a.get("active"))
    if active_count >= MAX_WATCHED_ACCOUNTS:
        return {"ok": False, "message": f"Maksimum {MAX_WATCHED_ACCOUNTS} hesap takip edilebilir"}

    for acc in accounts:
        if acc["username"] == username:
            if acc.get("active"):
                return {"ok": False, "message": f"@{username} zaten takip listesinde"}
            else:
                acc["active"] = True
                _save_watch_list(accounts)
                return {"ok": True, "message": f"@{username} tekrar aktif edildi"}

    accounts.append({
        "platform": "instagram",
        "username": username,
        "added_at": datetime.utcnow().isoformat(),
        "last_checked_at": None,
        "last_post_id": None,
        "active": True,
    })
    _save_watch_list(accounts)
    return {"ok": True, "message": f"@{username} takip listesine eklendi"}


def list_watched_accounts() -> list:
    """Aktif takip edilen hesaplari doner."""
    return [a for a in _load_watch_list() if a.get("active")]


def remove_watched_account(username: str) -> dict:
    """Hesabi takip listesinden cikarir (active=False)."""
    username = username.lstrip("@").strip()
    accounts = _load_watch_list()
    for acc in accounts:
        if acc["username"] == username and acc.get("active"):
            acc["active"] = False
            _save_watch_list(accounts)
            return {"ok": True, "message": f"@{username} takipten cikarildi"}
    return {"ok": False, "message": f"@{username} aktif takip listesinde bulunamadi"}


def check_account_new_posts(account: dict, telegram_send_fn: Callable) -> dict:
    """
    Tek bir hesabi kontrol eder. Yeni post varsa Telegram bildirim gonderir.
    Returns: {ok, new_post_found, notified}
    """
    try:
        import instaloader
    except ImportError:
        return {"ok": False, "new_post_found": False, "notified": False,
                "error": "instaloader yuklu degil: pip install instaloader"}

    username = account["username"]
    try:
        loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_comments=False,
            save_metadata=False,
            quiet=True,
        )
        profile = instaloader.Profile.from_username(loader.context, username)
        posts = list(profile.get_posts())
        if not posts:
            return {"ok": True, "new_post_found": False, "notified": False}

        latest = posts[0]
        latest_id = str(latest.shortcode)
        last_known_id = account.get("last_post_id")

        accounts = _load_watch_list()
        for acc in accounts:
            if acc["username"] == username:
                acc["last_checked_at"] = datetime.utcnow().isoformat()
                if last_known_id != latest_id:
                    acc["last_post_id"] = latest_id
                break
        _save_watch_list(accounts)

        if last_known_id is None:
            return {"ok": True, "new_post_found": False, "notified": False}

        if last_known_id != latest_id:
            msg = (
                f"@{username} yeni icerik paylasti!\n"
                f"https://www.instagram.com/p/{latest_id}/"
            )
            try:
                telegram_send_fn(msg)
                return {"ok": True, "new_post_found": True, "notified": True}
            except Exception as te:
                logger.error(f"Telegram bildirim hatasi (@{username}): {te}")
                return {"ok": True, "new_post_found": True, "notified": False}

        return {"ok": True, "new_post_found": False, "notified": False}

    except Exception as e:
        # instaloader specific exceptions
        err_str = str(e)
        if "ProfileNotExistsException" in type(e).__name__ or "does not exist" in err_str.lower():
            return {"ok": False, "new_post_found": False, "notified": False,
                    "error": f"@{username} bulunamadi veya hesap silinmis"}
        if "PrivateProfileNotFollowedException" in type(e).__name__ or "private" in err_str.lower():
            return {"ok": False, "new_post_found": False, "notified": False,
                    "error": f"@{username} gizli hesap"}
        logger.warning(f"Instagram check hatasi @{username}: {e}")
        return {"ok": False, "new_post_found": False, "notified": False, "error": str(e)[:100]}


def run_instagram_check_cycle(telegram_send_fn: Callable) -> dict:
    """Tum aktif hesaplari kontrol eder."""
    accounts = list_watched_accounts()
    checked = 0
    notified = 0
    for acc in accounts:
        result = check_account_new_posts(acc, telegram_send_fn)
        checked += 1
        if result.get("notified"):
            notified += 1
        time.sleep(2)
    return {"ok": True, "checked": checked, "notified": notified}


def start_instagram_scheduler(telegram_send_fn: Callable, interval_minutes: int = 30) -> bool:
    """Instagram periyodik kontrol schedulerini baslatir."""
    global _instagram_scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        if _instagram_scheduler and _instagram_scheduler.running:
            return True
        _instagram_scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
        _instagram_scheduler.add_job(
            func=lambda: run_instagram_check_cycle(telegram_send_fn),
            trigger="interval",
            minutes=interval_minutes,
            id="instagram_check",
            name="Instagram Hesap Kontrolu",
            replace_existing=True,
        )
        _instagram_scheduler.start()
        logger.info(f"Instagram scheduler basladi: her {interval_minutes} dakika")
        return True
    except ModuleNotFoundError as e:
        logger.warning(f"Scheduler dependency eksik, scheduler devre disi: {e}")
        return False
    except Exception as e:
        logger.error(f"Instagram scheduler hatasi: {e}")
        return False
