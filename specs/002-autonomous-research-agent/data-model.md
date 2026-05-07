# Data Model: Jarvis Autonomous Research Agent

**Generated**: 2026-04-13

---

## Entities

### ResearchItem
Kaynak'tan çekilen tek bir içerik birimi.

```json
{
  "id": "string (sha256 of url)",
  "source": "github | reddit | twitter | instagram",
  "title": "string",
  "url": "string",
  "summary": "string (AI özet veya ilk 280 karakter)",
  "fetched_at": "ISO8601 datetime",
  "included_in_brief": "string (brief date YYYY-MM-DD) | null"
}
```

### DailyBrief
Günlük Telegram mesajı kaydı.

```json
{
  "date": "YYYY-MM-DD",
  "items": ["ResearchItem.id", "..."],
  "message_text": "string (Telegram'a gönderilen metin)",
  "sent_at": "ISO8601 datetime | null",
  "send_status": "sent | failed | skipped"
}
```
**State file**: `state/research/daily_brief_history.json` — son 30 gün saklanır, eskisi temizlenir.

### WatchedAccount
Instagram takip listesi girişi.

```json
{
  "platform": "instagram",
  "username": "string (@ olmadan)",
  "added_at": "ISO8601 datetime",
  "last_checked_at": "ISO8601 datetime | null",
  "last_post_id": "string | null",
  "active": "boolean"
}
```
**State file**: `state/research/watch_list.json` — array of WatchedAccount.

### AgentFramework
External agent framework tanımı (runtime config, code'a hardcode değil).

```json
{
  "name": "crewai | openhands",
  "repo_path": "external-repos/crewAI | external-repos/OpenHands",
  "entry_command": ["python", "-m", "crewai", "run"],
  "install_check": "crewai | openhands",
  "bridge_command": "/crewai | /openhands"
}
```
**Config**: `config/external_agents.yml` (yeni dosya).

---

## State Transitions

### WatchedAccount
```
(not in list) → added → active=true
active=true → last_checked_at güncellendi → new_post_detected → Telegram bildirim
active=true → deactivated → active=false
```

### DailyBrief
```
pending (yok) → items toplandı → message_text oluştu → sent → send_status=sent
                                                      → failed → send_status=failed (retry yok, ertesi gün tekrar)
```

---

## Validation Rules

- `WatchedAccount.username`: sadece alfanumerik + `_` + `.`, @ olmadan, max 30 karakter
- `ResearchItem.source`: enum `["github", "reddit", "twitter", "instagram"]`
- `DailyBrief.date`: unique (aynı günde 2 brief olamaz)
- `WatchedAccount` listesi max 50 hesap (rate limit koruması)
