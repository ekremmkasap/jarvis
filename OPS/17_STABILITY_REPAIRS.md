# OPS 17 - Stability Repairs

Durum: active
Amac: bu sprintte uygulanan ve acik kalan stabilite onarimlarini tek yerde tutmak.

## Uygulanan Onarimlar

### 1. Orchestrator confirm davranisi

Dosyalar:
- `services/orchestrator/task_queue.py`
- `services/orchestrator/main.py`
- `tests/test_task_queue.py`

Sorun:
- awaiting-confirmation olmayan task icin sahte basari ve `task_confirmed` sinyali uretilebiliyordu.

Uygulanan fix:
- queue tarafinda `ValueError("task_not_awaiting_confirmation")`
- API tarafinda `409`
- negatif test eklendi

Kanıt:
- `python -m unittest tests.test_task_queue tests.test_memory_skill tests.test_self_healer`
- sonuc: `9/9 OK`

### 2. Voice wake method mismatch

Dosya:
- `services/voice/voice_service.py`

Sorun:
- `_check_energy_wake` diye olmayan bir method cagriliyordu.

Uygulanan fix:
- `_check_wake(frame)` kullanildi

Durum:
- compile temiz
- runtime smoke henuz yapilmadi

### 3. Fresh-clone Telegram default drift

Dosyalar:
- `.env.example`
- `README.md`

Sorun:
- Telegram default acikti
- token/chat blank idi
- bu durum yanlis guven olusturuyordu

Uygulanan fix:
- `JARVIS_ENABLE_TELEGRAM=0`
- README uyarisi eklendi

### 4. OpenClaw helper drift

Dosya:
- `server/openclaw_bridge.py`

Sorunlar:
- hardcoded chat id
- default `--dev`
- broken helper cagrisi
- Windows CLI yolunda zayif varsayim

Uygulanan fix:
- helper yeniden yazildi
- default profile env kontrollu oldu
- default command `openclaw.cmd`
- broken call kaldirildi

### 5. Wrapper drift

Dosyalar:
- `openclaw.cmd`
- `openclaw_web_only.cmd`
- `install_openclaw_startup.cmd`
- `JARVIS_BASLAT_README.txt`

Sorun:
- olmayan pathler
- eski sahiplik anlatisi

Uygulanan fix:
- canonical bridge wrapper mantigina cekildi
- `openclaw_web_only.cmd` bridge `--web-only` wrapperi olarak dogrulandi
- launcher note runtime gercegine gore yeniden yazildi

### 6. Secret redaction

Dosya:
- `WEEK3_CALEB4_COMPLETION.md`

Sorun:
- canlı gorunumlu Gemini key metin icinde duruyordu

Uygulanan fix:
- redaction yapildi

Kalan is:
- gercek key rotasyonu operator tarafinda ayrica yapilmali

### 7. Watchdog producer contract

Dosyalar:
- `server/bridge.py`
- `server/watchdog.py`

Sorun:
- watchdog `server/data/bridge_heartbeat.json` ve `server/data/bridge.lock` bekliyordu
- bridge tarafinda bu artefaktlari ureten net bir writer yoktu

Uygulanan fix:
- bridge boot sirasinda lock dosyasi yaziliyor
- bridge runtime boyunca heartbeat guncelleniyor
- duzenli cikista heartbeat/lock temizleniyor

Kanit:
- `python -m py_compile server/bridge.py master_launcher.py server/watchdog.py`
- sonuc: `OK`

Kalan is:
- live watchdog smoke ve restart semantigi bu checkpointte tekrar kosulmadi

## Acik Kalan Stabilite Borclari

### A. Full-suite test toplami

Kanit:
- `python -m unittest tests.test_dashboard`
- sonuc: `16 test, OK`
- `python -m unittest tests.test_task_queue tests.test_memory_skill tests.test_self_healer`
- sonuc: `9 test, OK`

Durum:
- dashboard failure current checkpointte yeniden uretilemedi
- ama exact `117/117` toplam claimi hala full rerun ile yeniden kanitlanmis degil

### B. Watchdog live smoke / restart semantics

Kanit:
- writer path artik `server/bridge.py` icinde mevcut
- live restart dongusu current checkpointte yeniden yurutulmedi

Durum:
- acik

### C. Gateway/account contract kirmalari

Kanıt:
- alt ajan backend lane bulgulari
- `server/orchestrator_gateway.py`
- `server/account_manager.py`

Durum:
- acik
- bu sprintte en dusuk-risk setin disinda tutuldu

### D. OpenClaw live send / live reply proof

Durum:
- acik
- hard-blocked by proof gap

## Bu Dosyanin Kurali

- bir sey duzeltildiyse burada kanit komutuyla yazilir
- bir sey aciksa burada blocker olarak kalir
- sahte yesil durum yazilmaz
