================================================================================
JARVIS MASTER LAUNCHER - CURRENT RUNTIME NOTES
================================================================================

AMAC:
  Windows tarafinda guncel launcher sahipligini tek yerde aciklamak.
  Bu belge eski "6 ayri servis garanti baslar" anlatimini tekrarlamaz.

GUNCEL DURUM:
  - Ana Windows runtime: `server/bridge.py`
  - Yardimci servisler: `services/voice/voice_service.py`, `apps/desktop-hologram`
  - `master_launcher.py` Bridge, Voice ve Hologram akisini yonetir.
  - Birincil Windows giris noktasi: `SISTEM_J.bat`
  - `JARVIS_BASLAT.bat` uyumluluk alias'i olarak `SISTEM_J.bat` dosyasina yonlenir.
  - Watchdog ayri yardimci surectir; canonical runtime'in zorunlu parcasi degildir.
  - Gateway / Team / OpenCode ownership'i repo genelinde hala drift uretmektedir.

NASIL KULLANILIR:

  1. Grafik arayuz:
     - `SISTEM_J.bat`
     - `JARVIS_BASLAT.bat`
     - `JARVIS_HEPSINI_BASLAT.bat`

  2. Komut satiri:
     cmd> SISTEM_J.bat
     cmd> JARVIS_BASLAT.bat
     cmd> JARVIS_HEPSINI_BASLAT.bat
     PowerShell> python master_launcher.py

STARTUP SIRASI:

  [1] Bridge
      - HTTP API
      - Telegram bot path
      - model routing
      - memory integrations

  [2] Voice
      - wake word / STT / TTS lane

  [3] Hologram
      - desktop UI lane

NOTLAR:
  - Legacy belgelerde gecen Watchdog -> Bridge -> Gateway -> Team zinciri
    bugunun canonical sahiplik modeli degildir.
  - `server/SOURCE_OF_TRUTH.md` ve `README.md` aktif kaynak kabul edilmelidir.
  - Launcher health check timeout verse bile surecler bir sure sonra ayaga kalkabilir.

KAPAMA:
  Ctrl+C ile launcher tarafindan baslatilan surecler kapatilmaya calisilir.
  Legacy Team/Gateway/Watchdog kapanis sirasi garanti edilmez.

HEALTH CHECK:
  - Bridge: `http://127.0.0.1:8081`
  - Orchestrator: `http://127.0.0.1:8091`
  - Dashboard varsa ayrica dogrulanir.

SORUN GIDERME:
  - `python` bulunamiyorsa PATH'i kontrol et.
  - Hologram baslamiyorsa `apps/desktop-hologram` altinda `npm install` gerekebilir.
  - Telegram etkinlestirilecekse `.env` icinde token/chat tanimlari zorunludur.
  - Bir port doluysa ilgili surecin gercek sahipligini `netstat` veya process list ile kontrol et.

ENVIRONMENT:
  - `PYTHONUNBUFFERED=1`
  - `JARVIS_VOICE_RUNTIME=mark_xxxv` varsayilan gelir.
  - `JARVIS_ENABLE_HOLOGRAM=1` varsayilan gelir.
  - `JARVIS_WAIT_FOR_GATEWAY=0` varsayilan gelir.
  - `ROOT=<repo-root>`
  - Bridge `.env` yukler.
  - `.env.example` varsayilan olarak Telegram'i kapali getirir.

LOGLAR:
  - `server/logs/`
  - `server/logs/claude_hooks/`

UYARI:
  Bu belge master launcher davranisini gercege yaklastirir; tam runtime canon icin
  `OPS/04_RUNTIME_CANON.md` ve `server/SOURCE_OF_TRUTH.md` izlenmelidir.

================================================================================
