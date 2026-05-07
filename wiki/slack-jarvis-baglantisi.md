# Slack - Jarvis Baglantisi

Durum: 2026-04-15 itibariyla lokal Slack bridge kodu hazir.

## Amac

Codex Slack plugin'i sadece Codex oturumuna baglidir. Jarvis runtime bu plugin'i otomatik kullanamaz. Jarvis'in Slack'ten mesaj alip cevap verebilmesi icin kendi Slack app tokenlariyla calisan ayri bir bridge gerekir.

## Eklenen Runtime

Dosya:

- `server/slack_bridge.py`

Launcher baglantisi:

- `master_launcher.py`, `JARVIS_ENABLE_SLACK=1` ise `SLACK` process'ini baslatir.
- Varsayilan kapali: `JARVIS_ENABLE_SLACK=0`.

Dependency:

- `slack-bolt`
- `slack-sdk`

Kurulum bu oturumda yapildi ve `requirements.txt` icine eklendi.

## Env Degiskenleri

`.env` veya launcher ortaminda:

```text
JARVIS_ENABLE_SLACK=1
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_SIGNING_SECRET=
SLACK_BOT_USER_ID=
JARVIS_SLACK_THREAD_REPLIES=1
BRIDGE_URL=http://127.0.0.1:8081
```

Secret degerleri wiki'ye yazilmaz.

## Slack App Ayarlari

Socket Mode onerilir; lokal Jarvis icin public HTTPS endpoint gerekmez.

Gerekli ana parcalar:

- Bot User OAuth Token: `SLACK_BOT_TOKEN`
- App-Level Token: `SLACK_APP_TOKEN`
- App-Level token scope: `connections:write`

Onerilen bot scopes:

- `app_mentions:read`
- `chat:write`
- `im:history`
- `im:read`
- `im:write`
- Kanalda kullanilacaksa `channels:history` ve `channels:read`

## Davranis

Bridge su mesajlari Jarvis'e aktarir:

- DM mesajlari.
- Kanalda bot mention mesajlari.
- Kanalda `jarvis`, `jarvis:`, `jarvis,`, `/jarvis` ile baslayan mesajlar.

Bridge su mesajlari yok sayar:

- Bot mesajlari.
- `message_changed`, `message_deleted` gibi subtype eventleri.
- Bos mesajlar.
- Botun kendi kullanicisindan gelen mesajlar.

Slack eventleri lokal bridge'e gider:

`POST http://127.0.0.1:8081/api/chat`

Payload icinde:

- `source=slack`
- `lane=slack`
- stable `chat_id`
- Slack team/channel/user/thread bilgisi

## Test Komutlari

```powershell
python server\slack_bridge.py --check
python -m py_compile server\slack_bridge.py master_launcher.py
python -m pytest tests\test_slack_bridge.py tests\test_master_launcher.py -q
```

Son bilinen sonuc:

- `slack_bolt_available=true`
- tokenlar henuz girilmedigi icin `ok=false`
- unit tests: `12 passed`

## Aktivasyon

Tokenlar girildikten sonra:

1. `JARVIS_ENABLE_SLACK=1` yap.
2. `JARVIS.bat` ile Jarvis'i yeniden baslat.
3. Slack app'i kanala davet et: `/invite @Jarvis`
4. DM veya kanalda `jarvis status` yaz.

## Guvenlik

- Slack'e mesaj gonderme bu bridge'in normal cevap davranisidir.
- Kritik aksiyonlar Jarvis tarafinda yine mevcut onay kurallarina bagli kalmalidir.
- Tokenlar loglara ve wiki'ye yazilmamalidir.

