# Jarvis — Entegrasyonlar

## Aktif Entegrasyonlar

### Gmail
- Dosya: `server/skills/gmail_skill.py`
- Komutlar: `liste`, `gonder [kime] | [konu] | [icerik]`
- Env: `GMAIL_CREDENTIALS_PATH`, `GOOGLE_CREDENTIALS_PATH`

### Google Calendar
- Dosya: `server/skills/gcalendar_skill.py`
- Komutlar: `liste`, `ekle baslik:... tarih:... saat:...`
- Env: `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_TOKEN_PATH`

### Notion
- Dosya: `server/skills/notion_skill.py`
- Komutlar: `liste`, `ara`, `ekle`
- Env: `NOTION_API_KEY`, `NOTION_DATABASE_ID`

### Stripe
- Dosya: `server/skills/stripe_webhook_skill.py`
- Durum: ⚠️ Yarım (Codex kotası bitti — 8 Nisan 2026 yenileniyor)
- Otomatik müşteri onboarding sistemi

### Telegram
- Bot token ve chat ID [[telegram-komutlari]] sayfasında

## Planlanan Entegrasyonlar

| Servis | Durum | Not |
|--------|-------|-----|
| eBay | Bekleniyor | API key bekleniyor |
| Trendyol | Aktif | Skill var |
| Shopify | Bekleniyor | OAuth token bekleniyor |
| Printify | Sorunlu | Token sorunu var |
| Etsy | Planlandı | — |
| AliExpress | Planlandı | — |

## TypeScript Bridge
- `src/runtime/skills/BridgeSkill.ts`
- `BRIDGE_URL` ve `BRIDGE_TIMEOUT_MS` env değişkenleri
- TS → Python bridge HTTP katmanı

## MCP Entegrasyonları
- Gmail MCP
- Google Calendar MCP
- Notion MCP
- Supabase MCP

## İlgili Sayfalar
- [[saas-vizyon]]
- [[mimari-genel-bakis]]
