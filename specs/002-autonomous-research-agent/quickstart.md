# Quickstart: Autonomous Research Agent

**Branch**: `002-autonomous-research-agent`

---

## Gereksinimler

```bash
pip install feedparser instaloader apscheduler beautifulsoup4
```

`requirements.txt`'e eklenecekler:
```
feedparser>=6.0
instaloader>=4.10
APScheduler>=3.10
beautifulsoup4>=4.12
```

---

## Yapılandırma

### .env (opsiyonel overrides)
```env
RESEARCH_BRIEF_HOUR=8          # Sabah brief saati (varsayılan: 8)
RESEARCH_BRIEF_MINUTE=0        # Dakika (varsayılan: 0)
GITHUB_TOKEN=                  # Opsiyonel: 5000 req/h için
REDDIT_CLIENT_ID=              # Opsiyonel: PRAW için
NITTER_BASE_URL=https://nitter.net  # X/Twitter mirror
```

### config/external_agents.yml (yeni dosya — implement sırasında oluşturulur)
```yaml
frameworks:
  crewai:
    repo_path: external-repos/crewAI
    install_check: crewai
    bridge_command: /crewai
  openhands:
    repo_path: external-repos/OpenHands
    install_check: openhands
    bridge_command: /openhands
```

---

## Çalıştırma

Jarvis normal başlatıldığında scheduler otomatik başlar:
```bash
JARVIS_BASLAT.bat
# veya
python master_launcher.py
```

Manuel brief testi (Telegram):
```
/sabah-brief
```

Instagram takip testi:
```
/instagram takip @fatihmakes
/instagram liste
```

---

## Test

```bash
python -m pytest tests/test_research_scheduler.py tests/test_instagram_skill.py tests/test_external_agent_skill.py -v --tb=short
```

---

## State Dosyaları

```
state/research/
├── watch_list.json          ← Instagram takip listesi
└── daily_brief_history.json ← Son 30 günlük brief geçmişi
```

`.gitignore`'a eklenecek: `state/research/daily_brief_history.json`
