# Research: Jarvis Autonomous Research & Personality Agent

**Generated**: 2026-04-13  
**Phase**: 0 — Tüm NEEDS CLARIFICATION çözüldü

---

## 1. GitHub Trending Veri Kaynağı

**Decision**: `https://github.com/trending` sayfasını `requests + BeautifulSoup4` ile parse et; veya `https://api.github.com/search/repositories?q=created:>YYYY-MM-DD&sort=stars` ile API kullan.  
**Rationale**: GitHub'ın resmi trending API'si yok. `gh-trending` PyPI paketi 2023'ten sonra güncellenmiyor. RSS endpoint `https://github.com/trending.atom` çalışıyor (public, token gerektirmez).  
**Alternatives considered**: PyGithub (API limit, trending endpoint yok), scraping (kırılgan HTML).  
**Seçim**: `https://github.com/trending.atom` — feedparser ile basit, kararlı.

---

## 2. Reddit Veri Kaynağı

**Decision**: Reddit JSON API (`https://www.reddit.com/r/programming/top.json?limit=5&t=day`) — token gerektirmez, User-Agent header yeterli.  
**Rationale**: PRAW daha güçlü ama yeni App kaydı gerektirir. JSON endpoint public, production-ready.  
**Alternatives considered**: PRAW (credential kompleksliği), RSS (daha az kontrol).  
**Seçim**: Direct JSON endpoint, `requests` ile, rotating subreddit listesi `config/research_sources.yml` içinde.

---

## 3. X/Twitter Veri Kaynağı

**Decision**: Ücretsiz tier kısıtlı (500 tweet/ay okuma). Başlangıçta **Nitter public instance** (`nitter.net`) veya `snscrape` kütüphanesi ile scraping.  
**Rationale**: Resmi API v2 ücretsiz = read-only, 500 tweet/ay. Jarvis için yeterli değil. Nitter: public mirror, login gerektirmez.  
**Alternatives considered**: Twitter API v2 Basic ($100/ay), snscrape (ban riski).  
**Risk**: Nitter instance'ları bazen kapanıyor. Fallback: "X içeriği geçici olarak alınamıyor" mesajı + sessiz fail.  
**Seçim**: Nitter RSS feed (`https://nitter.net/{username}/rss`) — feedparser ile aynı pattern.

---

## 4. Instagram Takip Mekanizması

**Decision**: `instaloader` kütüphanesi — public profiller için login gerektirmez, post metadata JSON olarak dönüyor.  
**Rationale**: Selenium/Playwright gibi browser automation'dan daha hafif. instaloader aktif geliştiriliyor (2025 güncel).  
**Alternatives considered**: instagram-scraper (bakımda değil), Apify (ücretli), Selenium (ağır).  
**Rate limit**: instaloader kendi bekleme mekanizmasını (`sleep_between_requests`) içeriyor — ayarlanabilir.  
**Login**: Public profiller için gerekmez. Private profil takibi = kullanıcı şifresi gerekir, bu özellik EXCLUDED (FR-003 kapsamı dışı).  
**Seçim**: `instaloader.Profile.from_username()` → son post ID karşılaştırma.

---

## 5. APScheduler Entegrasyonu (Windows 10)

**Decision**: `APScheduler 3.10.x` — `BackgroundScheduler` + `CronTrigger(hour=8, minute=0)`.  
**Rationale**: Windows'ta `cron` komutu yok. APScheduler process-içi çalışır, `bridge.py` başladığında otomatik scheduler başlar.  
**Alternatives considered**: Windows Task Scheduler (setup komplex), `schedule` kütüphanesi (basit ama thread-safe değil), Celery (Redis bağımlılığı aşırı).  
**Integration point**: `research_scheduler_skill.py` import edildiğinde scheduler otomatik başlar; `bridge.py`'a `import research_scheduler_skill` satırı yeterli.  
**Seçim**: APScheduler 3.x BackgroundScheduler.

---

## 6. CrewAI / OpenHands Subprocess Router

**Decision**: `external_agent_skill.py` — Python `subprocess.run()` ile `external-repos/crewAI/` veya `external-repos/OpenHands/` altında komut çalıştırır.  
**Rationale**: Her framework kendi venv'inde çalışabilir. Subprocess en az coupling sağlar.  
**Kurulum kontrolü**: `importlib.util.find_spec("crewai")` veya `external-repos/crewAI/pyproject.toml` varlığı kontrolü.  
**Seçim**: subprocess + kurulum kontrolü + kullanıcıya yönlendirici mesaj.

---

## 7. soul.md Günlük Brief Formatı

**Decision**: `soul.md` mevcut; brief formatını section olarak genişlet: `## Araştırma Briefingi` ve `## Kişilik Tonu`.  
**Rationale**: soul.md zaten bridge.py tarafından okunuyor. Yeni section bridge tarafından parse edilir, research brief'e enjekte edilir.  
**Seçim**: Minimal değişiklik — soul.md'ye 1 yeni section eklenir.

---

## 8. State Dosyaları Yeri

**Decision**: `state/research/watch_list.json` ve `state/research/daily_brief_history.json`.  
**Rationale**: `state/` mevcut Jarvis convention'ı (agent_memory, codex_cooldowns burada). JSON dosyaları restart-safe.  
**Seçim**: `state/research/` klasörü — gitignore'a daily_brief_history eklenir (kişisel veri).

---

## Bağımlılık Özeti

| Paket | Mevcut mu? | Aksiyon |
|-------|-----------|---------|
| requests | ✅ | - |
| feedparser | ❌ | `pip install feedparser` |
| beautifulsoup4 | ❓ | `pip install beautifulsoup4` (scraping fallback için) |
| instaloader | ❌ | `pip install instaloader` |
| APScheduler | ❓ | `pip install apscheduler` |
| snscrape | ❌ | Opsiyonel, Nitter yeterli ise gerekmez |

`requirements.txt` güncellenecek.
