"""Masaüstüne ULTRA-PROMPT #2 — 002-autonomous-research-agent implementation promptu yazar."""
import pathlib

DESKTOP = pathlib.Path(r"C:\Users\sergen\Desktop")

# Using list to avoid triple-quote conflicts with docstrings in the content
LINES = [
]

def build_content():
    return "\n".join(LINES)

CONTENT_RAW = r"""================================================================================
JARVIS ULTRA-PROMPT #2 — 002-AUTONOMOUS-RESEARCH-AGENT
FULL HARDCORE IMPLEMENTATION PROMPT
Repo: C:\Users\sergen\Desktop\jarvis-mission-control
Branch: 002-autonomous-research-agent
Mode: READ TASKS → IMPLEMENT SLICE BY SLICE → TEST → COMMIT → UPDATE CLAUDE.MD
================================================================================

YOU ARE: Elite Python Engineer + Jarvis Core Developer
LANGUAGE: Turkish for user output, English for code/paths/comments
REPO: C:\Users\sergen\Desktop\jarvis-mission-control
BRANCH: 002-autonomous-research-agent

================================================================================
ABSOLUTE RULES
================================================================================

1.  READ FIRST: Read specs/002-autonomous-research-agent/tasks.md before any code
2.  READ BEFORE WRITE: Read every file you will modify before touching it
3.  BACKWARD-SAFE: server/bridge.py — only add new elif branches, never remove existing
4.  NO CREDENTIALS IN LOGS: Instagram token, Telegram token, GitHub token NEVER printed
5.  MOCK IN TESTS: feedparser, requests, instaloader, subprocess — always mock in pytest
6.  NO REAL NETWORK: tests must never make real HTTP calls
7.  PYTEST BEFORE DONE: Every slice ends with passing pytest
8.  COMMIT AFTER EACH SLICE: Atomic commits per slice
9.  CLAUDE.MD UPDATE: After every slice, update CLAUDE.md section for this feature
10. NEVER PUSH TO MAIN
11. NEVER CLAIM SUCCESS WITHOUT PASSING TESTS
12. NEVER BREAK EXISTING BRIDGE.PY COMMANDS

================================================================================
MANDATORY READING LIST (BEFORE ANY CODE)
================================================================================

READ IN ORDER:
  1. specs/002-autonomous-research-agent/tasks.md          — 42 görev, faz faz
  2. specs/002-autonomous-research-agent/spec.md            — user stories + acceptance criteria
  3. specs/002-autonomous-research-agent/plan.md            — teknik context + slice planı
  4. specs/002-autonomous-research-agent/data-model.md      — JSON entity şemaları
  5. specs/002-autonomous-research-agent/contracts/telegram-commands.md
  6. server/bridge.py                                       — mevcut routing, insertion point bul
  7. server/soul.md  (veya config/soul.md)                  — mevcut kişilik dosyası
  8. requirements.txt                                       — mevcut paketler

THEN CHECK:
  ls server/skills/ | grep -E "research|instagram|external_agent"
  ls state/research/ 2>/dev/null || echo "dir missing"
  ls config/external_agents.yml 2>/dev/null || echo "missing"

================================================================================
CLAUDE.MD UPDATE RULE
================================================================================

After every slice find or create section:
  ### Autonomous Research Agent (002 — Branch aktif)

Update with:
  - Durum: [IN_PROGRESS / TAMAMLANDI]
  - Tamamlanan: [slice listesi]
  - Son commit: [hash]
  - Sonraki: [next slice]
  - Test sonucu: [N passed]

Commit separately: "chore: update CLAUDE.md — research-agent slice N"

================================================================================
PHASE 1 — SETUP (T001-T004)
================================================================================

--- T001: state/research/ dizini + watch_list.json ---

  Create directory state/research/ if not exists.
  Create state/research/watch_list.json:
    []

  This is the WatchedAccount array. Must be valid JSON array.
  Never overwrite if already exists (check first).

--- T002: state/research/daily_brief_history.json ---

  Create state/research/daily_brief_history.json:
    []

  This stores DailyBrief records, max 30 entries.
  Never overwrite if already exists.

--- T003: config/external_agents.yml ---

  Create config/external_agents.yml:

    agents:
      - name: crewai
        repo_path: external-repos/crewAI
        entry_command: ["python", "-m", "crewai", "run"]
        install_check: crewai
        bridge_command: /crewai
        description: "CrewAI multi-agent framework"

      - name: openhands
        repo_path: external-repos/OpenHands
        entry_command: ["python", "-m", "openhands.core.main"]
        install_check: openhands
        bridge_command: /openhands
        description: "OpenHands AI software engineer"

  Never overwrite if already exists.

--- T004: requirements.txt güncellemesi ---

  Check if these packages exist in requirements.txt:
    feedparser
    instaloader
    apscheduler
    beautifulsoup4

  If any missing: append them. Do NOT remove existing packages.
  Do NOT change pinned versions of existing packages.

  Commit: "chore: setup state dirs + config + deps for research-agent"
  CLAUDE.MD update: Slice 1 (Setup) TAMAMLANDI

================================================================================
PHASE 2 — FOUNDATION SKELETONS (T005-T009)
================================================================================

--- T005: bridge.py okuma ---

  READ server/bridge.py FULLY.
  Find:
    1. Where Telegram command routing happens (large if/elif block or dict)
    2. The function/method that sends Telegram messages (note its name and signature)
    3. The startup section where skills are initialized
    4. Last elif branch before the "komut bulunamadı" / "unknown command" fallback

  Write these findings as a comment block at the TOP of your next bridge.py edit.
  DO NOT MODIFY bridge.py in this task — just read and plan.

--- T006: soul.md okuma ---

  Search for soul.md:
    find server/ config/ -name "soul.md" 2>/dev/null
    find . -name "soul.md" 2>/dev/null | head -5

  Read the file. Note:
    - Current file path (SOUL_MD_PATH)
    - Existing section headers
    - Tone/language (Türkçe mi?)
    - Does ## Araştırma Brief Prefix section exist?

  If soul.md doesn't exist: note path as server/soul.md (will be created in Phase 6)

--- T007: research_scheduler_skill.py skeleton ---

  Create server/skills/research_scheduler_skill.py:

    """
    Jarvis Autonomous Research Scheduler Skill
    Sabah briefingi: GitHub trending + Reddit + Nitter/Twitter RSS
    APScheduler ile arka planda çalışır, bridge.py döngüsünü bloklamaz.
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

  Commit: "feat: research_scheduler_skill skeleton"

--- T008: instagram_skill.py skeleton ---

  Create server/skills/instagram_skill.py:

    """
    Jarvis Instagram Takip Skill
    Hesap takip listesi yönetimi + periyodik yeni içerik kontrolü
    instaloader kullanır — public profiller için login gerekmez
    """
    import json
    import logging
    import re
    import time
    from pathlib import Path
    from datetime import datetime
    from typing import Optional, Callable

    import instaloader

    logger = logging.getLogger(__name__)

    WATCH_LIST_PATH = Path("state/research/watch_list.json")
    MAX_WATCHED_ACCOUNTS = 50
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.]{1,30}$')

    _instagram_scheduler = None

  Commit: "feat: instagram_skill skeleton"

--- T009: external_agent_skill.py skeleton ---

  Create server/skills/external_agent_skill.py:

    """
    Jarvis External Agent Framework Skill
    CrewAI ve OpenHands framework'lerini subprocess ile çalıştırır
    config/external_agents.yml'den konfigürasyon okur
    """
    import shutil
    import subprocess
    import logging
    from pathlib import Path
    from typing import Optional

    import yaml

    logger = logging.getLogger(__name__)

    AGENTS_CONFIG_PATH = Path("config/external_agents.yml")

  Commit: "feat: external_agent_skill skeleton"
  CLAUDE.MD update: Phase 2 (Foundation) TAMAMLANDI

================================================================================
PHASE 3 — USER STORY 1: SABAH ARAŞTIRMA BRİEFİNGİ (T010-T019)
================================================================================

GOAL: Her sabah 08:00'de GitHub + Reddit + Twitter özetini Telegram'a gönder.

--- T010: fetch_github_trending ---

  Implement in server/skills/research_scheduler_skill.py:

    def fetch_github_trending(max_items: int = 5) -> list[dict]:
        """GitHub trending repo'larını çeker. Hata durumunda [] döner."""
        items = []
        try:
            # GitHub trending atom feed (unauthenticated, 60 req/h limit)
            feed_url = "https://github.com/trending"
            headers = {"Accept": "application/atom+xml"}
            resp = requests.get(
                f"https://github.com/trending",
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

  SECURITY: Never log GitHub token value if present in env.

--- T011: fetch_reddit_top ---

  Implement in server/skills/research_scheduler_skill.py:

    def fetch_reddit_top(
        subreddits: list[str] = None,
        max_items: int = 5
    ) -> list[dict]:
        """Reddit günlük top post'larını çeker. Hata → []"""
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

--- T012: fetch_twitter_nitter ---

  Implement in server/skills/research_scheduler_skill.py:

    def fetch_twitter_nitter(
        query: str = "python AI 2026",
        max_items: int = 5
    ) -> list[dict]:
        """Nitter RSS üzerinden Twitter/X arama sonuçları. Fail → []"""
        items = []
        nitter_instances = [
            "https://nitter.poast.org",
            "https://nitter.privacydev.net",
        ]
        for base in nitter_instances:
            try:
                rss_url = f"{base}/search/rss?q={requests.utils.quote(query)}"
                feed = feedparser.parse(rss_url)
                if feed.bozo and not feed.entries:
                    continue
                for entry in feed.entries[:max_items]:
                    item_id = hashlib.sha256(entry.get("link","").encode()).hexdigest()[:16]
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
                    break  # İlk çalışan instance yeterli
            except Exception as e:
                logger.warning(f"Nitter {base} fetch failed: {e}")
        return items[:max_items]

--- T013: build_brief_message ---

  Implement in server/skills/research_scheduler_skill.py:

    def build_brief_message(items: list[dict], soul_prefix: str = "") -> str:
        """
        Türkçe Telegram mesajı oluşturur.
        soul_prefix: soul.md'den gelen kişilik prefix'i
        Max 3000 karakter.
        """
        today = date.today().strftime("%d %B %Y")
        lines = []
        if soul_prefix:
            lines.append(soul_prefix)
        lines.append(f"🗓 *Sabah Briefingi — {today}*\n")

        by_source = {"github": [], "reddit": [], "twitter": []}
        for item in items:
            src = item.get("source", "other")
            if src in by_source:
                by_source[src].append(item)

        source_emojis = {"github": "🐙 GitHub", "reddit": "🔴 Reddit", "twitter": "🐦 X/Twitter"}
        for src, emoji_label in source_emojis.items():
            src_items = by_source[src]
            if not src_items:
                continue
            lines.append(f"\n*{emoji_label}*")
            for item in src_items[:3]:
                title = item.get("title", "")[:60]
                url = item.get("url", "")
                lines.append(f"• [{title}]({url})")

        if not any(by_source.values()):
            lines.append("⚠️ Bugün içerik çekemedim, yarın tekrar deniyorum.")

        msg = "\n".join(lines)
        return msg[:3000]

--- T014: save_daily_brief / load_today_brief ---

  Implement in server/skills/research_scheduler_skill.py:

    def save_daily_brief(brief: dict) -> None:
        """DailyBrief kaydını history dosyasına ekler. Max 30 gün saklar."""
        BRIEF_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            history = []
            if BRIEF_HISTORY_PATH.exists():
                history = json.loads(BRIEF_HISTORY_PATH.read_text(encoding="utf-8"))
            # Aynı gün brief varsa güncelle
            today = brief.get("date", date.today().isoformat())
            history = [b for b in history if b.get("date") != today]
            history.append(brief)
            # Max 30 gün
            history = sorted(history, key=lambda b: b.get("date", ""))[-MAX_HISTORY_DAYS:]
            BRIEF_HISTORY_PATH.write_text(
                json.dumps(history, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Brief kaydetme hatası: {e}")

    def load_today_brief() -> Optional[dict]:
        """Bugünün brief kaydını döner, yoksa None."""
        try:
            if not BRIEF_HISTORY_PATH.exists():
                return None
            history = json.loads(BRIEF_HISTORY_PATH.read_text(encoding="utf-8"))
            today = date.today().isoformat()
            for brief in reversed(history):
                if brief.get("date") == today:
                    return brief
        except Exception as e:
            logger.warning(f"Brief yükleme hatası: {e}")
        return None

--- T015: run_morning_brief ---

  Implement in server/skills/research_scheduler_skill.py:

    def run_morning_brief(telegram_send_fn: Callable[[str], None]) -> dict:
        """
        Tüm kaynakları toplar, brief oluşturur, Telegram'a gönderir.
        Hiçbir exception dışarıya sızmaz — hepsini yakalar.
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
                logger.error(f"Telegram gönderme hatası: {te}")

            brief = {
                "date": date.today().isoformat(),
                "items": [i["id"] for i in items],
                "message_text": message,
                "sent_at": datetime.utcnow().isoformat() if send_status == "sent" else None,
                "send_status": send_status,
            }
            save_daily_brief(brief)
            return {"ok": send_status == "sent", "items_count": len(items), "send_status": send_status}
        except Exception as e:
            logger.error(f"run_morning_brief hatası: {e}")
            return {"ok": False, "items_count": 0, "send_status": "failed", "error": str(e)}

--- T016: APScheduler entegrasyonu ---

  Implement in server/skills/research_scheduler_skill.py:

    def start_scheduler(telegram_send_fn: Callable[[str], None]) -> bool:
        """
        BackgroundScheduler başlatır. Her gün BRIEF_HOUR:BRIEF_MINUTE'de brief çalıştırır.
        Windows uyumlu (APScheduler 3.x BackgroundScheduler).
        Returns True if started successfully.
        """
        global _scheduler
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            from apscheduler.triggers.cron import CronTrigger

            if _scheduler and _scheduler.running:
                logger.info("Research scheduler zaten çalışıyor")
                return True

            _scheduler = BackgroundScheduler(timezone="Europe/Istanbul")
            _scheduler.add_job(
                func=lambda: run_morning_brief(telegram_send_fn),
                trigger=CronTrigger(hour=BRIEF_HOUR, minute=BRIEF_MINUTE),
                id="morning_brief",
                name="Sabah Araştırma Briefingi",
                replace_existing=True,
            )
            _scheduler.start()
            logger.info(f"Research scheduler başladı: her gün {BRIEF_HOUR:02d}:{BRIEF_MINUTE:02d}")
            return True
        except Exception as e:
            logger.error(f"Scheduler başlatma hatası: {e}")
            return False

    def get_scheduler_status() -> dict:
        """Scheduler durumunu döner."""
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

--- T017: bridge.py /sabah-brief komutu ---

  READ server/bridge.py before editing.
  Find the last elif branch for Telegram commands.
  APPEND (do not modify existing branches):

    elif text == "/sabah-brief":
        # 002: Anlık sabah briefingi tetikle
        try:
            from server.skills.research_scheduler_skill import run_morning_brief
            result = run_morning_brief(lambda msg: send_telegram_message(msg, chat_id))
            if result.get("ok"):
                response = f"✅ Brief gönderildi — {result['items_count']} kaynak tarandı"
            else:
                response = f"⚠️ Brief gönderilemedi: {result.get('error','bilinmiyor')}"
        except Exception as e:
            response = f"❌ Hata: {str(e)[:200]}"
        send_telegram_message(response, chat_id)

  IMPORTANT: Replace send_telegram_message / chat_id with the ACTUAL function name and
  chat_id variable you found when reading bridge.py in T005.
  DO NOT REMOVE OR MODIFY existing commands.

--- T018: bridge.py /arastirma-durum komutu ---

  APPEND to bridge.py:

    elif text == "/arastirma-durum":
        # 002: Scheduler durumu ve son brief bilgisi
        try:
            from server.skills.research_scheduler_skill import (
                get_scheduler_status, load_today_brief
            )
            status = get_scheduler_status()
            today_brief = load_today_brief()
            running = "✅ Çalışıyor" if status.get("running") else "❌ Durdurulmuş"
            next_run = status.get("jobs", [{}])[0].get("next_run", "bilinmiyor") if status.get("jobs") else "job yok"
            brief_info = "yok" if not today_brief else f"{today_brief['send_status']} ({today_brief['items_count'] if 'items_count' in today_brief else '?'} madde)"
            response = (
                f"📊 Araştırma Durumu\n"
                f"Scheduler: {running}\n"
                f"Sonraki brief: {next_run}\n"
                f"Bugünkü brief: {brief_info}"
            )[:400]
        except Exception as e:
            response = f"❌ Durum alınamadı: {str(e)[:150]}"
        send_telegram_message(response, chat_id)

  Commit: "feat: research_scheduler_skill — fetch + brief + scheduler + bridge commands"
  CLAUDE.MD update: Phase 3 US1 TAMAMLANDI

--- T019: tests/test_research_scheduler.py ---

  Create tests/test_research_scheduler.py:

    import json
    import pytest
    from pathlib import Path
    from unittest.mock import patch, MagicMock
    from datetime import date

    # Adjust sys.path if needed
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    @patch("server.skills.research_scheduler_skill.requests.get")
    def test_fetch_github_trending_returns_list(mock_get):
        from server.skills.research_scheduler_skill import fetch_github_trending
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html><body>
        <article class="Box-row">
          <h2><a href="/owner/repo">Owner / Repo</a></h2>
          <p>A test description</p>
        </article>
        </body></html>
        """
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        items = fetch_github_trending(max_items=3)
        assert isinstance(items, list)
        for item in items:
            assert "source" in item and item["source"] == "github"
            assert "url" in item
            assert "title" in item

    @patch("server.skills.research_scheduler_skill.requests.get")
    def test_fetch_github_trending_on_error_returns_empty(mock_get):
        from server.skills.research_scheduler_skill import fetch_github_trending
        mock_get.side_effect = Exception("network error")
        items = fetch_github_trending()
        assert items == []

    @patch("server.skills.research_scheduler_skill.requests.get")
    def test_fetch_reddit_top_returns_list(mock_get):
        from server.skills.research_scheduler_skill import fetch_reddit_top
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "children": [
                    {"data": {"title": "Test Post", "url": "https://example.com", "selftext": ""}}
                ]
            }
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        items = fetch_reddit_top(subreddits=["programming"], max_items=3)
        assert isinstance(items, list)
        if items:
            assert items[0]["source"] == "reddit"

    @patch("server.skills.research_scheduler_skill.feedparser.parse")
    def test_fetch_twitter_nitter_on_failure_returns_empty(mock_parse):
        from server.skills.research_scheduler_skill import fetch_twitter_nitter
        mock_parse.side_effect = Exception("nitter down")
        items = fetch_twitter_nitter()
        assert items == []

    def test_build_brief_message_empty_items():
        from server.skills.research_scheduler_skill import build_brief_message
        msg = build_brief_message([])
        assert "çekemedim" in msg or "Brief" in msg
        assert len(msg) <= 3000

    def test_build_brief_message_with_items():
        from server.skills.research_scheduler_skill import build_brief_message
        items = [
            {"source": "github", "title": "cool/repo", "url": "https://github.com/cool/repo",
             "summary": "desc", "fetched_at": "2026-04-13T08:00:00", "included_in_brief": None}
        ]
        msg = build_brief_message(items, soul_prefix="Günaydın kanka!")
        assert "Günaydın" in msg
        assert "GitHub" in msg or "github" in msg.lower()

    def test_save_and_load_today_brief(tmp_path, monkeypatch):
        from server.skills import research_scheduler_skill as rss
        monkeypatch.setattr(rss, "BRIEF_HISTORY_PATH", tmp_path / "daily_brief_history.json")
        today = date.today().isoformat()
        brief = {"date": today, "items": [], "message_text": "test", "sent_at": None, "send_status": "sent"}
        rss.save_daily_brief(brief)
        loaded = rss.load_today_brief()
        assert loaded is not None
        assert loaded["date"] == today
        assert loaded["send_status"] == "sent"

    def test_run_morning_brief_calls_send_fn():
        from server.skills.research_scheduler_skill import run_morning_brief
        sent_messages = []
        with patch("server.skills.research_scheduler_skill.fetch_github_trending", return_value=[]):
            with patch("server.skills.research_scheduler_skill.fetch_reddit_top", return_value=[]):
                with patch("server.skills.research_scheduler_skill.fetch_twitter_nitter", return_value=[]):
                    with patch("server.skills.research_scheduler_skill.load_soul_context", return_value={"prefix":""}):
                        with patch("server.skills.research_scheduler_skill.save_daily_brief"):
                            result = run_morning_brief(lambda msg: sent_messages.append(msg))
        assert "ok" in result
        assert len(sent_messages) == 1

  Run: python -m pytest tests/test_research_scheduler.py -v --tb=short
  Fix all failures before Phase 4.
  Commit: "test: test_research_scheduler — 7 tests passing"

================================================================================
PHASE 4 — USER STORY 2: INSTAGRAM HESAP TAKİBİ (T020-T027)
================================================================================

GOAL: /instagram takip @hesap → listeye ekle; yeni içerik → Telegram bildirim.

--- T020: add_watched_account ---

  Implement in server/skills/instagram_skill.py:

    def _load_watch_list() -> list[dict]:
        try:
            if WATCH_LIST_PATH.exists():
                return json.loads(WATCH_LIST_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return []

    def _save_watch_list(accounts: list[dict]) -> None:
        WATCH_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        WATCH_LIST_PATH.write_text(
            json.dumps(accounts, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def add_watched_account(username: str) -> dict:
        """
        Instagram hesabını takip listesine ekler.
        username: @ olmadan, sadece alfanumerik + _ + .
        Returns: {ok: bool, message: str}
        """
        # @ kaldır
        username = username.lstrip("@").strip()

        if not USERNAME_PATTERN.match(username):
            return {"ok": False, "message": f"Geçersiz kullanıcı adı: @{username}"}

        accounts = _load_watch_list()
        active_count = sum(1 for a in accounts if a.get("active"))
        if active_count >= MAX_WATCHED_ACCOUNTS:
            return {"ok": False, "message": f"Maksimum {MAX_WATCHED_ACCOUNTS} hesap takip edilebilir"}

        # Zaten var mı?
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
        return {"ok": True, "message": f"✅ @{username} takip listesine eklendi"}

--- T021: list_watched_accounts ---

  Implement in server/skills/instagram_skill.py:

    def list_watched_accounts() -> list[dict]:
        """Aktif takip edilen hesapları döner."""
        return [a for a in _load_watch_list() if a.get("active")]

--- T022: remove_watched_account ---

  Implement in server/skills/instagram_skill.py:

    def remove_watched_account(username: str) -> dict:
        """Hesabı takip listesinden çıkarır (active=False)."""
        username = username.lstrip("@").strip()
        accounts = _load_watch_list()
        for acc in accounts:
            if acc["username"] == username and acc.get("active"):
                acc["active"] = False
                _save_watch_list(accounts)
                return {"ok": True, "message": f"@{username} takipten çıkarıldı"}
        return {"ok": False, "message": f"@{username} aktif takip listesinde bulunamadı"}

--- T023: check_account_new_posts ---

  Implement in server/skills/instagram_skill.py:

    def check_account_new_posts(account: dict, telegram_send_fn: Callable) -> dict:
        """
        Tek bir hesabı kontrol eder. Yeni post varsa Telegram bildirim gönderir.
        Returns: {ok, new_post_found, notified}
        """
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
                # İlk kontrol — mevcut son postu kaydet, bildirim yok
                return {"ok": True, "new_post_found": False, "notified": False}

            if last_known_id != latest_id:
                msg = (
                    f"📸 *@{username}* yeni içerik paylaştı!\n"
                    f"https://www.instagram.com/p/{latest_id}/"
                )
                try:
                    telegram_send_fn(msg)
                    return {"ok": True, "new_post_found": True, "notified": True}
                except Exception as te:
                    logger.error(f"Telegram bildirim hatası (@{username}): {te}")
                    return {"ok": True, "new_post_found": True, "notified": False}

            return {"ok": True, "new_post_found": False, "notified": False}

        except instaloader.exceptions.ProfileNotExistsException:
            return {"ok": False, "new_post_found": False, "notified": False,
                    "error": f"@{username} bulunamadı veya hesap silinmiş"}
        except instaloader.exceptions.PrivateProfileNotFollowedException:
            return {"ok": False, "new_post_found": False, "notified": False,
                    "error": f"@{username} gizli hesap"}
        except Exception as e:
            logger.warning(f"Instagram check hatası @{username}: {e}")
            return {"ok": False, "new_post_found": False, "notified": False, "error": str(e)[:100]}

--- T024: run_instagram_check_cycle ---

  Implement in server/skills/instagram_skill.py:

    def run_instagram_check_cycle(telegram_send_fn: Callable) -> dict:
        """Tüm aktif hesapları kontrol eder."""
        accounts = list_watched_accounts()
        checked = 0
        notified = 0
        for acc in accounts:
            result = check_account_new_posts(acc, telegram_send_fn)
            checked += 1
            if result.get("notified"):
                notified += 1
            time.sleep(2)  # Rate limit koruması
        return {"ok": True, "checked": checked, "notified": notified}

--- T025: APScheduler (Instagram) ---

  Implement in server/skills/instagram_skill.py:

    def start_instagram_scheduler(
        telegram_send_fn: Callable,
        interval_minutes: int = 30
    ) -> bool:
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
                name="Instagram Hesap Kontrolü",
                replace_existing=True,
            )
            _instagram_scheduler.start()
            logger.info(f"Instagram scheduler başladı: her {interval_minutes} dakika")
            return True
        except Exception as e:
            logger.error(f"Instagram scheduler hatası: {e}")
            return False

--- T026: bridge.py Instagram komutları ---

  READ bridge.py (T005 notlarını kullan).
  APPEND (backward-safe):

    elif text.startswith("/instagram takip "):
        # 002: Instagram hesap takip et
        try:
            from server.skills.instagram_skill import add_watched_account
            handle = text.replace("/instagram takip ", "").strip()
            result = add_watched_account(handle)
            response = result["message"]
        except Exception as e:
            response = f"❌ Hata: {str(e)[:150]}"
        send_telegram_message(response, chat_id)

    elif text == "/instagram listele":
        # 002: Takip listesi
        try:
            from server.skills.instagram_skill import list_watched_accounts
            accounts = list_watched_accounts()
            if not accounts:
                response = "📋 Takip listesi boş. /instagram takip @hesap ile ekle."
            else:
                lines = ["📋 *Takip Listesi*"]
                for acc in accounts[:20]:
                    last = acc.get("last_checked_at", "hiç")[:10] if acc.get("last_checked_at") else "hiç"
                    lines.append(f"• @{acc['username']} (son kontrol: {last})")
                response = "\n".join(lines)[:400]
        except Exception as e:
            response = f"❌ Hata: {str(e)[:150]}"
        send_telegram_message(response, chat_id)

    elif text.startswith("/instagram cikar "):
        # 002: Takipten çıkar
        try:
            from server.skills.instagram_skill import remove_watched_account
            handle = text.replace("/instagram cikar ", "").strip()
            result = remove_watched_account(handle)
            response = result["message"]
        except Exception as e:
            response = f"❌ Hata: {str(e)[:150]}"
        send_telegram_message(response, chat_id)

  Commit: "feat: instagram_skill — add/list/remove/check/scheduler + bridge commands"
  CLAUDE.MD update: Phase 4 US2 TAMAMLANDI

--- T027: tests/test_instagram_skill.py ---

  Create tests/test_instagram_skill.py:

    import json
    import pytest
    from pathlib import Path
    from unittest.mock import patch, MagicMock
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    @pytest.fixture
    def tmp_watch_list(tmp_path, monkeypatch):
        """watch_list.json için geçici path."""
        from server.skills import instagram_skill as ig
        monkeypatch.setattr(ig, "WATCH_LIST_PATH", tmp_path / "watch_list.json")
        return tmp_path / "watch_list.json"

    def test_add_watched_account_success(tmp_watch_list):
        from server.skills.instagram_skill import add_watched_account
        result = add_watched_account("testuser")
        assert result["ok"] is True
        assert "testuser" in result["message"]

    def test_add_watched_account_strips_at(tmp_watch_list):
        from server.skills.instagram_skill import add_watched_account
        result = add_watched_account("@testuser")
        assert result["ok"] is True

    def test_add_watched_account_invalid_username(tmp_watch_list):
        from server.skills.instagram_skill import add_watched_account
        result = add_watched_account("invalid user!")
        assert result["ok"] is False

    def test_add_watched_account_duplicate(tmp_watch_list):
        from server.skills.instagram_skill import add_watched_account
        add_watched_account("dupuser")
        result = add_watched_account("dupuser")
        assert result["ok"] is False
        assert "zaten" in result["message"]

    def test_list_watched_accounts(tmp_watch_list):
        from server.skills.instagram_skill import add_watched_account, list_watched_accounts
        add_watched_account("user1")
        add_watched_account("user2")
        lst = list_watched_accounts()
        assert len(lst) == 2

    @patch("server.skills.instagram_skill.instaloader.Profile")
    @patch("server.skills.instagram_skill.instaloader.Instaloader")
    def test_check_account_new_post_sends_notification(mock_loader_cls, mock_profile_cls, tmp_watch_list):
        from server.skills.instagram_skill import add_watched_account, check_account_new_posts, _load_watch_list
        add_watched_account("testuser")
        # Simüle: mevcut hesapta bilinen post var
        accounts = _load_watch_list()
        accounts[0]["last_post_id"] = "oldpost123"
        from server.skills import instagram_skill as ig
        ig._save_watch_list(accounts)

        mock_loader = MagicMock()
        mock_loader_cls.return_value = mock_loader
        mock_post = MagicMock()
        mock_post.shortcode = "newpost456"
        mock_profile = MagicMock()
        mock_profile.get_posts.return_value = [mock_post]
        mock_profile_cls.from_username.return_value = mock_profile

        notifications = []
        account = _load_watch_list()[0]
        result = check_account_new_posts(account, lambda msg: notifications.append(msg))
        assert result["new_post_found"] is True
        assert len(notifications) == 1

    @patch("server.skills.instagram_skill.instaloader.Profile")
    @patch("server.skills.instagram_skill.instaloader.Instaloader")
    def test_check_private_profile_returns_error(mock_loader_cls, mock_profile_cls, tmp_watch_list):
        import instaloader
        from server.skills.instagram_skill import add_watched_account, check_account_new_posts, _load_watch_list
        add_watched_account("privateuser")
        mock_loader = MagicMock()
        mock_loader_cls.return_value = mock_loader
        mock_profile_cls.from_username.side_effect = instaloader.exceptions.PrivateProfileNotFollowedException()
        account = _load_watch_list()[0]
        result = check_account_new_posts(account, lambda msg: None)
        assert result["ok"] is False
        assert "gizli" in result.get("error", "")

  Run: python -m pytest tests/test_instagram_skill.py -v --tb=short
  Fix all failures.

================================================================================
PHASE 5 — USER STORY 3: EXTERNAL AGENT FRAMEWORK (T028-T033)
================================================================================

GOAL: /crewai ve /openhands komutları çalışsın; kurulu değilse Türkçe yönlendirme.

--- T028: load_agent_configs ---

  Implement in server/skills/external_agent_skill.py:

    def load_agent_configs() -> list[dict]:
        """config/external_agents.yml'den agent tanımlarını yükler."""
        try:
            cfg = yaml.safe_load(AGENTS_CONFIG_PATH.read_text(encoding="utf-8"))
            return cfg.get("agents", [])
        except Exception as e:
            logger.warning(f"Agent config yüklenemedi: {e}")
            return []

    def _get_agent_config(agent_name: str) -> Optional[dict]:
        for cfg in load_agent_configs():
            if cfg.get("name") == agent_name:
                return cfg
        return None

--- T029: check_framework_installed ---

  Implement in server/skills/external_agent_skill.py:

    def check_framework_installed(agent_name: str) -> dict:
        """
        Framework'ün CLI'ının yüklü olup olmadığını kontrol eder.
        shutil.which() kullanır — real subprocess değil.
        """
        cfg = _get_agent_config(agent_name)
        if not cfg:
            return {"installed": False, "message": f"{agent_name} konfigürasyonda bulunamadı"}
        install_check = cfg.get("install_check", agent_name)
        found = shutil.which(install_check)
        if found:
            return {"installed": True, "message": f"{agent_name} kurulu: {found}"}
        # Repo path kontrolü
        repo_path = Path(cfg.get("repo_path", ""))
        if repo_path.exists():
            return {
                "installed": True,
                "message": f"{agent_name} repo bulundu: {repo_path}",
                "via": "repo"
            }
        return {
            "installed": False,
            "message": (
                f"{agent_name} kurulu değil. Kurulum: "
                f"pip install {install_check} veya "
                f"git clone <repo> {cfg.get('repo_path','')}"
            )
        }

--- T030: run_agent_task ---

  Implement in server/skills/external_agent_skill.py:

    def run_agent_task(
        agent_name: str,
        task: str,
        timeout_seconds: int = 60
    ) -> dict:
        """
        Framework'ü subprocess ile çalıştırır.
        Kurulu değilse Türkçe kurulum mesajı döner.
        Hiçbir exception dışarıya sızmaz.
        """
        check = check_framework_installed(agent_name)
        if not check.get("installed"):
            return {"ok": False, "output": check["message"], "error": None}

        cfg = _get_agent_config(agent_name)
        if not cfg:
            return {"ok": False, "output": f"{agent_name} konfigürasyonu bulunamadı", "error": None}

        cmd = list(cfg.get("entry_command", [])) + [task]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            output = (result.stdout or result.stderr or "Çıktı yok")[:800]
            return {"ok": result.returncode == 0, "output": output, "error": None}
        except subprocess.TimeoutExpired:
            return {"ok": False, "output": f"Zaman aşımı ({timeout_seconds}s) — görev çok uzun sürdü", "error": "timeout"}
        except FileNotFoundError:
            return {"ok": False, "output": f"{agent_name} çalıştırılamadı — PATH'e ekli mi?", "error": "not_found"}
        except Exception as e:
            logger.error(f"run_agent_task hatası ({agent_name}): {e}")
            return {"ok": False, "output": str(e)[:200], "error": str(type(e).__name__)}

--- T031: get_agent_status ---

  Implement in server/skills/external_agent_skill.py:

    def get_agent_status(agent_name: str) -> dict:
        """Framework kurulum + repo durumu."""
        cfg = _get_agent_config(agent_name)
        if not cfg:
            return {"name": agent_name, "installed": False, "repo_path_exists": False,
                    "bridge_command": f"/{agent_name}", "error": "konfigürasyon yok"}
        check = check_framework_installed(agent_name)
        repo_exists = Path(cfg.get("repo_path", "")).exists()
        return {
            "name": agent_name,
            "installed": check["installed"],
            "repo_path_exists": repo_exists,
            "repo_path": cfg.get("repo_path"),
            "bridge_command": cfg.get("bridge_command"),
            "message": check["message"],
        }

--- T032: bridge.py CrewAI + OpenHands komutları ---

  APPEND to bridge.py (backward-safe):

    elif text.startswith("/crewai ") or text == "/crewai":
        # 002: CrewAI framework routing
        try:
            from server.skills.external_agent_skill import run_agent_task, get_agent_status
            task_text = text.replace("/crewai", "").strip()
            if not task_text or task_text == "durum":
                status = get_agent_status("crewai")
                installed = "✅ Kurulu" if status["installed"] else "❌ Kurulu değil"
                response = f"CrewAI Durumu\n{installed}\n{status.get('message','')}"[:400]
            else:
                result = run_agent_task("crewai", task_text, timeout_seconds=60)
                response = result["output"][:400]
        except Exception as e:
            response = f"❌ CrewAI hatası: {str(e)[:150]}"
        send_telegram_message(response, chat_id)

    elif text.startswith("/openhands ") or text == "/openhands":
        # 002: OpenHands framework routing
        try:
            from server.skills.external_agent_skill import run_agent_task, get_agent_status
            task_text = text.replace("/openhands", "").strip()
            if not task_text or task_text == "durum":
                status = get_agent_status("openhands")
                installed = "✅ Kurulu" if status["installed"] else "❌ Kurulu değil"
                response = f"OpenHands Durumu\n{installed}\n{status.get('message','')}"[:400]
            else:
                result = run_agent_task("openhands", task_text, timeout_seconds=60)
                response = result["output"][:400]
        except Exception as e:
            response = f"❌ OpenHands hatası: {str(e)[:150]}"
        send_telegram_message(response, chat_id)

  Commit: "feat: external_agent_skill — crewai/openhands check+run + bridge commands"
  CLAUDE.MD update: Phase 5 US3 TAMAMLANDI

--- T033: tests/test_external_agent_skill.py ---

  Create tests/test_external_agent_skill.py:

    import pytest
    from unittest.mock import patch, MagicMock
    from pathlib import Path
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    @patch("server.skills.external_agent_skill.shutil.which")
    def test_check_installed_found(mock_which):
        from server.skills.external_agent_skill import check_framework_installed
        mock_which.return_value = "/usr/bin/crewai"
        with patch("server.skills.external_agent_skill.load_agent_configs", return_value=[
            {"name": "crewai", "install_check": "crewai", "repo_path": "external-repos/crewAI",
             "entry_command": ["python", "-m", "crewai"], "bridge_command": "/crewai"}
        ]):
            result = check_framework_installed("crewai")
        assert result["installed"] is True

    @patch("server.skills.external_agent_skill.shutil.which")
    def test_check_not_installed_returns_install_msg(mock_which):
        from server.skills.external_agent_skill import check_framework_installed
        mock_which.return_value = None
        with patch("server.skills.external_agent_skill.load_agent_configs", return_value=[
            {"name": "crewai", "install_check": "crewai", "repo_path": "nonexistent/path",
             "entry_command": [], "bridge_command": "/crewai"}
        ]):
            result = check_framework_installed("crewai")
        assert result["installed"] is False
        assert "pip install" in result["message"] or "kurulu değil" in result["message"]

    @patch("server.skills.external_agent_skill.subprocess.run")
    @patch("server.skills.external_agent_skill.check_framework_installed")
    def test_run_agent_task_success(mock_check, mock_run):
        from server.skills.external_agent_skill import run_agent_task
        mock_check.return_value = {"installed": True, "message": "OK"}
        mock_run.return_value = MagicMock(returncode=0, stdout="Task completed", stderr="")
        with patch("server.skills.external_agent_skill._get_agent_config", return_value={
            "name": "crewai", "entry_command": ["python", "-m", "crewai"]
        }):
            result = run_agent_task("crewai", "test task")
        assert result["ok"] is True
        assert "completed" in result["output"]

    @patch("server.skills.external_agent_skill.check_framework_installed")
    def test_run_agent_task_not_installed_returns_message(mock_check):
        from server.skills.external_agent_skill import run_agent_task
        mock_check.return_value = {"installed": False, "message": "pip install crewai"}
        result = run_agent_task("crewai", "do something")
        assert result["ok"] is False
        assert "pip install" in result["output"] or "kurulu" in result["output"]

    @patch("server.skills.external_agent_skill.subprocess.run")
    @patch("server.skills.external_agent_skill.check_framework_installed")
    @patch("server.skills.external_agent_skill._get_agent_config")
    def test_run_agent_task_timeout_returns_error(mock_cfg, mock_check, mock_run):
        import subprocess
        from server.skills.external_agent_skill import run_agent_task
        mock_check.return_value = {"installed": True, "message": "OK"}
        mock_cfg.return_value = {"name": "crewai", "entry_command": ["python"]}
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=60)
        result = run_agent_task("crewai", "heavy task", timeout_seconds=60)
        assert result["ok"] is False
        assert "aşımı" in result["output"] or "timeout" in result["error"]

  Run: python -m pytest tests/test_external_agent_skill.py -v --tb=short

================================================================================
PHASE 6 — USER STORY 4: KİŞİLİK SİSTEMİ (T034-T037)
================================================================================

GOAL: soul.md'den kişilik okuyup briefingi kişiselleştir; /bugun-ne-var komutu.

--- T034: soul.md güncelleme ---

  Find soul.md path (T006'dan).
  READ current content first.
  ADD these sections IF NOT ALREADY PRESENT (never remove existing content):

    ## Araştırma Brief Prefix
    Günaydın kanka! ☀️ İşte bugünün önemli gelişmeleri:

    ## Sabah Selamlama Tonu
    Samimi, enerjik, Türkçe. "Kanka", "abi" tonu uygun.
    Teknik değil insan gibi konuş. Ekrem'in iş ortağısın.

    ## Günlük Agenda Formatı
    - Her madde bir bullet point
    - En önemli 3 gelişme önce
    - Sonunda "Bugün ne yapalım?" sorusu

  Commit: "feat: soul.md — sabah briefingi kişilik güncellendi"

--- T035 + T036: load_soul_context + build_brief_message entegrasyonu ---

  Add to server/skills/research_scheduler_skill.py:

    def load_soul_context() -> dict:
        """
        soul.md'den Araştırma Brief Prefix bölümünü okur.
        Dosya yoksa veya bölüm yoksa varsayılan döner.
        """
        default = {"prefix": "", "tone": "Türkçe, samimi"}
        try:
            soul_path = SOUL_MD_PATH
            if not soul_path.exists():
                # Farklı konumlara bak
                for candidate in [Path("config/soul.md"), Path("soul.md")]:
                    if candidate.exists():
                        soul_path = candidate
                        break
                else:
                    return default

            content = soul_path.read_text(encoding="utf-8")
            prefix = ""
            in_section = False
            for line in content.splitlines():
                if line.strip() == "## Araştırma Brief Prefix":
                    in_section = True
                    continue
                if in_section:
                    if line.startswith("## "):
                        break
                    prefix += line + "\n"
            return {"prefix": prefix.strip(), "tone": "Türkçe, samimi"}
        except Exception as e:
            logger.warning(f"soul.md okunamadı: {e}")
            return default

  (build_brief_message already updated in T013 to call load_soul_context)

--- T037: bridge.py /bugun-ne-var ---

  APPEND to bridge.py:

    elif text in ["/bugun-ne-var", "/bugun ne var"]:
        # 002: Bugünün araştırma özeti
        try:
            from server.skills.research_scheduler_skill import load_today_brief
            brief = load_today_brief()
            if brief:
                msg = brief.get("message_text", "")
                response = (msg[:350] + "...") if len(msg) > 350 else msg
            else:
                response = "📭 Bugün henüz brief yok. /sabah-brief ile şimdi oluştur."
        except Exception as e:
            response = f"❌ Hata: {str(e)[:150]}"
        send_telegram_message(response, chat_id)

  Commit: "feat: soul.md kişilik + load_soul_context + /bugun-ne-var bridge"
  CLAUDE.MD update: Phase 6 US4 TAMAMLANDI

================================================================================
PHASE 7 — STARTUP WIRING (T038-T040)
================================================================================

--- T038-T040: bridge.py startup ---

  READ bridge.py startup section (T005 notlarından).
  Find where to add scheduler initialization.
  APPEND in startup (after server init, before main loop, inside try/except):

    # 002: Autonomous Research Agent schedulers
    try:
        from server.skills.research_scheduler_skill import start_scheduler
        from server.skills.instagram_skill import start_instagram_scheduler

        def _telegram_send(msg):
            # bridge'deki mevcut Telegram send fonksiyonunu çağır
            # T005'te bulduğun fonksiyon adını ve chat_id'yi buraya koy
            send_telegram_message(msg, TELEGRAM_CHAT_ID)

        start_scheduler(_telegram_send)
        start_instagram_scheduler(_telegram_send, interval_minutes=30)
    except Exception as _sched_err:
        import logging
        logging.getLogger(__name__).warning(f"Research schedulers başlatılamadı: {_sched_err}")

  IMPORTANT: Use the actual function name and chat_id variable from bridge.py.
  If TELEGRAM_CHAT_ID is a different variable name, use that.
  If send_telegram_message has a different signature, match it exactly.

  Commit: "feat: bridge.py startup — research + instagram schedulers wired"
  CLAUDE.MD update: Phase 7 TAMAMLANDI

================================================================================
PHASE 8 — VALIDATION (T041-T042)
================================================================================

--- T041: Full test suite ---

  Run:
    python -m pytest tests/test_research_scheduler.py tests/test_instagram_skill.py \
      tests/test_external_agent_skill.py -v --tb=short

  Expected: ALL PASSED.
  Fix any failures before proceeding.
  Fix one test at a time — don't batch fix blindly.

--- T042: Smoke test ---

  Run:
    python -c "
    import sys
    sys.path.insert(0, '.')
    from server.skills.research_scheduler_skill import (
        fetch_github_trending, fetch_reddit_top, build_brief_message,
        save_daily_brief, load_today_brief, load_soul_context
    )
    from server.skills.instagram_skill import (
        add_watched_account, list_watched_accounts, remove_watched_account
    )
    from server.skills.external_agent_skill import (
        load_agent_configs, check_framework_installed, get_agent_status
    )
    print('Tüm importlar: OK')
    configs = load_agent_configs()
    print(f'Agent configs: {len(configs)} adet')
    soul = load_soul_context()
    print(f'Soul prefix: \"{soul[\"prefix\"][:40]}...\"')
    msg = build_brief_message([], soul_prefix='Test prefix')
    print(f'Brief message: {len(msg)} karakter')
    print('SMOKE TEST: PASSED')
    "

  If any import error: fix the import before claiming done.

  Final commit: "feat: 002-autonomous-research-agent complete — all slices done"

  CLAUDE.MD final update:
    ### Autonomous Research Agent (002)
    - Durum: TAMAMLANDI
    - Skills: server/skills/research_scheduler_skill.py, instagram_skill.py, external_agent_skill.py
    - State: state/research/watch_list.json, daily_brief_history.json
    - Config: config/external_agents.yml
    - Bridge: /sabah-brief /arastirma-durum /instagram-* /crewai /openhands /bugun-ne-var
    - Tests: pytest 19+ passed
    - Handoff: OPS/002_RESEARCH_AGENT_HANDOFF.md

================================================================================
HANDOFF DOCUMENT
================================================================================

Create OPS/002_RESEARCH_AGENT_HANDOFF.md:

    # 002 Autonomous Research Agent — Handoff

    ## Ne Çalışıyor
    - Her sabah 08:00 otomatik brief → Telegram
    - /sabah-brief → anlık brief tetikleme
    - /arastirma-durum → scheduler durumu
    - /bugun-ne-var → bugünkü brief özeti
    - /instagram takip/listele/cikar komutları
    - /crewai durum / /crewai <görev>
    - /openhands durum / /openhands <görev>

    ## Kaynaklar
    - GitHub: github.com/trending BeautifulSoup parse
    - Reddit: reddit.com JSON API (token gerektirmez)
    - X/Twitter: Nitter RSS fallback (nitter.poast.org)
    - Instagram: instaloader public profil scraping

    ## Konfigürasyon
    - BRIEF_HOUR / BRIEF_MINUTE: .env'de override edilebilir
    - Subreddits: research_scheduler_skill.py içinde hardcode, değiştirilebilir
    - External agents: config/external_agents.yml

    ## Limitler
    - GitHub: 60 req/saat (unauthenticated) — token ile artırılabilir
    - Instagram: Gizli hesaplar takip edilemez
    - X/Twitter: Nitter instance down olabilir — 2 instance deneniyor
    - CrewAI/OpenHands: Kurulum gerekmez check ediliyor, kurulu değilse Türkçe yönlendirme

    ## Yeni Kaynak Ekleme (3 adım)
    1. server/skills/research_scheduler_skill.py'e fetch_<kaynak>() ekle
    2. run_morning_brief() içinde çağır
    3. build_brief_message() by_source dict'ine ekle

================================================================================
ANTI-HALLUCINATION RULES
================================================================================

- NEVER print or log Telegram token, Instagram credentials, GitHub token
- NEVER make real HTTP requests in tests — always mock requests.get, feedparser.parse
- NEVER make real subprocess calls in tests — always mock subprocess.run
- NEVER remove existing bridge.py commands
- NEVER claim tests pass without running pytest
- NEVER hardcode credentials in code (always os.getenv())
- NEVER assume soul.md path — search for it first (T006)
- NEVER use blocking sleep() in production code — scheduler handles timing

================================================================================
GO. READ TASKS.MD. START T001. TEST. COMMIT. UPDATE CLAUDE.MD. HANDOFF.
================================================================================
"""

out = DESKTOP / "Ultra-Prompt-2 Research Agent Implementation.txt"
out.write_text(CONTENT, encoding="utf-8")
print(f"Written: {out}")
print(f"Lines: {len(CONTENT.splitlines())}")
