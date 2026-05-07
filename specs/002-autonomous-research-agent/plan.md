# Implementation Plan: Jarvis Autonomous Research & Personality Agent Sistemi

**Branch**: `002-autonomous-research-agent` | **Date**: 2026-04-13 | **Spec**: specs/002-autonomous-research-agent/spec.md

## Summary

Jarvis'e proaktif araştırma kabiliyeti ekleniyor: günlük sabah briefingi (GitHub/Reddit/X), Instagram hesap takibi,
external agent framework (CrewAI/OpenHands) routing ve soul.md tabanlı kişilik güçlendirmesi.
Tüm işlemler arka planda APScheduler ile çalışır; bridge.py ana döngüsü bloklanmaz.

## Technical Context

**Language/Version**: Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui — sadece mevcut UI, yeni sayfa opsiyonel)  
**Primary Dependencies**: APScheduler 3.x (scheduler), instaloader (Instagram), feedparser veya requests+bs4 (GitHub/Reddit RSS), tweepy veya snscrape (X/Twitter — scrape fallback), openai SDK (Groq/Gemini routing mevcut)  
**Storage**: JSON dosyaları (`state/research/` — watch list, daily briefs); mevcut SQLite varsa kullanılabilir  
**Testing**: pytest (`tests/test_research_scheduler.py`, `tests/test_instagram_skill.py`, `tests/test_external_agent_skill.py`)  
**Target Platform**: Windows 10, Python 3.11, mevcut Jarvis runtime  
**Project Type**: Python skill + bridge routing extension  
**Performance Goals**: Günlük brief <30sn; Instagram kontrol döngüsü ≤30dk; /crewai durum yanıtı <10sn  
**Constraints**: GitHub unauthenticated = 60 req/h; X/Twitter = scraping fallback; instaloader = rate limit farkındalığı; bridge.py backward-safe  
**Scale/Scope**: Tek kullanıcı (Ekrem), tek Telegram chat_id

## Constitution Check

| Prensip | Durum | Açıklama |
|---------|-------|----------|
| I. Local-First | ✅ PASS | APScheduler lokal; instaloader lokal; GitHub/Reddit public API |
| II. Spec Before Code | ✅ PASS | Bu plan uygulanmadan `speckit.tasks` çalıştırılmayacak |
| III. Security/Redaction | ✅ PASS | Instagram credentials, GitHub token, Telegram token log/UI'ya sızmaz; skill içinde redact |
| IV. Read Before Write | ✅ PASS | bridge.py okunacak, minimal extension; soul.md zaten var |
| V. Verify Before Done | ✅ PASS | Her slice sonunda pytest; bridge smoke testi |

**GATE: PASS** — Constitution ihlali yok.

## Project Structure

### Documentation (this feature)

```text
specs/002-autonomous-research-agent/
├── plan.md              ← Bu dosya
├── research.md          ← Phase 0 çıktısı
├── data-model.md        ← Phase 1 çıktısı
├── quickstart.md        ← Phase 1 çıktısı
├── contracts/           ← Phase 1 çıktısı
│   ├── telegram-commands.md
│   └── research-report-schema.json
└── tasks.md             ← /speckit.tasks çıktısı (henüz oluşturulmadı)
```

### Source Code (repository root)

```text
server/skills/
├── research_scheduler_skill.py   ← Yeni: APScheduler + kaynak toplayıcılar
├── instagram_skill.py            ← Yeni: instaloader tabanlı takip
└── external_agent_skill.py       ← Yeni: CrewAI / OpenHands router

state/research/
├── watch_list.json               ← Yeni: takip edilen Instagram hesapları
└── daily_brief_history.json      ← Yeni: son 7 günün briefleri

server/soul.md                    ← Mevcut, kişilik güçlendirmesi için güncelleme

tests/
├── test_research_scheduler.py    ← Yeni
├── test_instagram_skill.py       ← Yeni
└── test_external_agent_skill.py  ← Yeni
```

**Structure Decision**: Mevcut `server/skills/` pattern'i korunuyor. Yeni state dosyaları `state/research/` altında toplanıyor. bridge.py'a sadece yeni komut routing satırları ekleniyor (backward-safe).

## Complexity Tracking

> Constitution ihlali yok — bu bölüm geçerli değil.

## Slice Planı (Özet)

| Slice | Kapsam | Bağımlılık |
|-------|--------|-----------|
| A | `research_scheduler_skill.py` — GitHub trending + Reddit RSS toplayıcı + Telegram brief | - |
| B | `research_scheduler_skill.py` — APScheduler entegrasyonu + 08:00 cron + X/Twitter scraping fallback | Slice A |
| C | `instagram_skill.py` — hesap ekleme, watch_list.json, periyodik kontrol, Telegram bildirim | - |
| D | `external_agent_skill.py` — CrewAI/OpenHands kurulum kontrolü + subprocess router | - |
| E | `bridge.py` — 6 yeni komut ekleme (`/instagram takip`, `/instagram liste`, `/crewai`, `/openhands`, `/arastirma-durum`, `/sabah-brief`) | A-D |
| F | `soul.md` güncelleme + soul-aware brief formatting | E |
| G | Testler (`pytest`) + smoke + regresyon kontrolü | A-F |
