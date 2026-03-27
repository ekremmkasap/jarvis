# Jarvis Mission Control - Recovery Handoff

Bu dosya, silinen sistem dosyalarini tekrar toplamak icin Claude ve Antigravity'e verilecek toplu handoff ozetidir.

## Ana Hedef

Jarvis'i su vizyona goturuyorduk:

- tek bot degil, `private AI operating system`
- `Jarvis + OpenCode + Claude + Research + Guard + Ollama + Telegram Bot`
- `single roof AI router`
- `desktop hologram assistant`
- `Claw3D/OpenClaw` gorsel kontrol merkezi
- `video understanding + feature extraction + memory + trend + task generation`
- `ID-only mode + recovery/resume + security hardening`

## Ana Projeler / Bilesenler

- Ana repo: `C:\Users\sergen\Desktop\jarvis-mission-control`
- Ana backend: `server/bridge.py`
- Voice runtime: `services/voice/voice_service.py`
- Legacy voice/text: `hey_jarvis.py`
- Tray: `jarvis_tray.py`
- Desktop hologram: `apps/desktop-hologram/`
- Claw3D repo: `C:\Users\sergen\Desktop\Claw3D`
- OpenClaw ayarlari: `C:\Users\sergen\.openclaw\`

## Ne Kurulmustu

### 1. Telegram + Bridge

- `server/bridge.py` ana runtime olarak kullaniliyordu
- Telegram bot aktifti
- `/status`, `/roof`, `/board`, `/security-board`, `/resume`, `/replay` gibi komutlar vardi
- Mesaj akisi `bridge.py` uzerinden ilerliyordu

### 2. Single Roof AI Router

Hedeflenen mantik:

- local modeller (`qwen`, `deepseek`, `ollama`)
- free/cloud fallback (`Google AI Studio Gemini`)
- OpenRouter/OpenAI opsiyonel destek
- tum provider health tek yerden gorunsun

Eklenen/yapilan mantik:

- `/roof` komutu ile sistemin tek cati router durumu gosteriliyordu
- provider health:
  - `ollama`
  - `openrouter`
  - `openai`
  - `google_ai_studio`

### 3. Desktop Hologram

Olusturulan klasor/dosyalar:

- `apps/desktop-hologram/package.json`
- `apps/desktop-hologram/index.html`
- `apps/desktop-hologram/main.js`
- `apps/desktop-hologram/preload.js`
- `apps/desktop-hologram/renderer.js`
- `apps/desktop-hologram/styles.css`
- `apps/desktop-hologram/README.md`
- `start_desktop_hologram.bat`
- `JARVIS_HOLOGRAM_SES.bat`

Ozellikler:

- Electron tabanli, transparent, frameless, always-on-top overlay
- `Jarvis` / `OpenCode` / diger agent kimliklerini gosteren panel
- state fazlari:
  - `idle`
  - `listening`
  - `thinking`
  - `speaking`
  - `offline`
- speech bubble / preview / skills / abilities / activity meter
- `Hey Jarvis` tetiklenince overlay one gelmeye basliyordu

Kullandigi endpointler:

- `http://127.0.0.1:8081/api/office/presence`
- `http://127.0.0.1:8081/api/desktop-assistant`

### 4. Voice Runtime

Ana hedef:

- `Hey Jarvis` dediginde canlanan masaustu asistan
- Turkce dinleme ve Turkce cevap

Voice tarafinda yapilanlar:

- ana ses runtime `services/voice/voice_service.py` olacak sekilde yon degistirildi
- `faster-whisper` / `whisper` STT
- `edge-tts` / `pyttsx3` TTS
- `.env` yukleyen yapi
- backend'e varsayilan baglanti:
  - `JARVIS_BACKEND_URL=http://127.0.0.1:8081`
- wake word geldiginde desktop assistant state dosyasina yaziyordu:
  - `server/logs/desktop_assistant.json`

Ozel dosya ve komutlar:

- `JARVIS_HOLOGRAM_SES.bat`
  - bridge + hologram + voice service birlikte acilsin diye eklendi

### 5. Claw3D / OpenClaw

Durum:

- Claw3D remote office, Jarvis presence feed'den veri aliyordu
- `OpenClaw gateway` icin local token ve `ws://localhost:18789` kullaniliyordu

Onemli ayarlar:

- presence feed:
  - `http://127.0.0.1:8081/api/office/presence`
  - Tailscale varken: `http://100.x.x.x:8081/api/office/presence`
- OpenClaw gateway:
  - `ws://localhost:18789`
- Desktop hologram ile Claw3D ayni `speechText/latestPreview` mantigini kullaniyordu

### 6. Video Understanding Pipeline

Bu en cok gelistirilen kisimlardan biri.

Olusturulan/duzenlenen temel dosya:

- `server/agents/video_link_agent.py`

Yapilanlar:

- `yt-dlp` ile YouTube / Instagram public link analizi
- metadata cekme
- subtitle / automatic captions ozetleme
- thumbnail vision analizi
- frame extraction
- frame vision analizi
- timeline cikarma

Komutlar:

- `/video-analiz [link]`
- `/video-pack [link]`
- `/video-features [link]`
- `/video-timeline [link]`
- `/video-intel [link]`
- `/video-hafiza`
- `/video-karsilastir`
- `/video-trend`
- `/trend-oneri`

### 7. Source Ingestion Layer

`bridge.py` icinde kaynak tipi otomatik ayriliyordu:

- `instagram_reel`
- `instagram_post`
- `instagram_profile`
- `youtube_video`
- `generic_url`

Mantik:

- link gelince dogru analyzer pipe secilsin
- manuel komut secme ihtiyaci azalsin

### 8. Canonical Video Intelligence Schema

Olusan canonical veri modeli su alanlara dayaniyordu:

- `source_url`
- `video_summary`
  - platform
  - title
  - uploader
  - duration
- `transcript_summary`
- `vision_summary`
- `frame_summaries`
- `timeline`
- `features`

`/video-intel` bu raporu derli toplu veriyordu.

### 9. Feature Extraction / Memory / Trend / Task

Jarvis sadece videoyu analiz etmiyor, urun feature'i de cikariyordu.

Feature tipleri / clusterlari:

- `Multi-Agent Workspace` -> `agents`
- `Video Understanding` -> `media`
- `Single Roof Gateway` -> `router`
- `Recovery Resume` -> `recovery`
- `ID-Only Private Mode` -> `identity`

Memory dosyalari:

- `server/logs/feature_memory.json`
- `server/logs/preference_memory.json`
- `server/logs/video_intelligence_memory.json`

Komutlar:

- `/board`
- `/uygula-oneri`
- `/backlog`
- `/gorev-uret [team|opencode]`
- `/cluster-gorev [cluster] [team|opencode]`
- `/oncelik`
- `/like [feature adı]`
- `/dislike [feature adı]`

Bu sistem ne yapiyordu:

1. kaynak al
2. feature cikar
3. memory'ye yaz
4. board yap
5. implementasyon onerisi ver
6. backlog cikar
7. task uret
8. explicit feedback ile scoring'i ogren
9. cluster bazli strateji kur

### 10. Adaptive Scoring / Trend-Driven Recommendation

Scoring boyutlari:

- `impact`
- `effort`
- `fit`
- `cluster_boost`
- `total`

Trend odakli komutlar:

- `/video-trend`
- `/trend-oneri`

Yani sistem sadece analiz degil, urun yonu de oneriyordu.

### 11. ID-Only Mode

Eklenen env alanlari:

- `JARVIS_ALLOWED_CHAT_IDS=`
- `JARVIS_LOCAL_ONLY_MODE=0/1`
- `JARVIS_ALLOWED_TAILSCALE_IPS=`

Yapilanlar:

- Telegram chat allowlist
- local/tailscale request guard
- sadece izinli chat id ve istemciler calissin mantigi

### 12. Recovery / Resume / Replay

Checkpoint mantigi vardi:

- `task_checkpoint_<chatid>.json`
- `opencode_checkpoint_<chatid>.json`

Komutlar:

- `/resume`
- `/replay`
- `/replay team`
- `/replay opencode`

Bu sayede sistem cokse bile son isler gorulup yeniden baslatilabiliyordu.

### 13. Security Katmani

Olusan guvenlik omurgasi:

- `ID-only mode`
- `Secret Redaction`
- `Exec Hardening`
- `Security Audit Trail`
- `Security Board`

Eklenen dosyalar:

- `server/skills/redaction_skill.py`
- `server/skills/exec_hardening_skill.py`

Yapilanlar:

- secret pattern masking (`sk-`, `AIza`, `Bearer`, vs.)
- hassas metni `safe_text(...)` ile redakte etme
- tehlikeli komut/path/pattern bloklama
- blocked exec/path olaylarini audit'e yazma:
  - `server/logs/security_audit.jsonl`

Komut:

- `/security-board`

## Free-First Mimari Karari

Parali Google Cloud servisleri yerine `free/local-first` yapi secildi.

Oncelik:

- `Google AI Studio / Gemini free tier`
- `local temp media`
- `faster-whisper`
- `Edge TTS`
- `local background workers`
- `.env + local keyring`

Bu karar sayesinde `Vertex/Cloud Run/Storage` gibi billing riski olan seyler ana yol olmadi.

## Kilo Gateway / Moonshot Vizyonu

Arastirma sonucu cikan mimari gorus:

- Kilo Gateway hemen replace etmeyecek
- ilk asama:
  - `compat layer`
  - `pass-through`
  - `shadow mode`
- sonra:
  - `policy`
  - `fallback`
  - `provider decision`

Yani Kilo, `single roof router`i bir anda degistirmeyecek; once uyum katmani olarak eklenecek.

## Onemli Environment / Tool Notlari

Muhtemel gerekli kurulumlar:

```powershell
pip install yt-dlp
pip install faster-whisper
pip install edge-tts
```

Olası ekler:

```powershell
ollama pull moondream:latest
```

`.env` tarafinda kritik alanlar:

```env
JARVIS_BACKEND_URL=http://127.0.0.1:8081
VOICE_LANGUAGE=tr
VOICE_TTS_VOICE=tr-TR-AhmetNeural
JARVIS_RESPONSE_LANGUAGE=turkish
GOOGLE_API_KEY=
JARVIS_ALLOWED_CHAT_IDS=
JARVIS_LOCAL_ONLY_MODE=0
JARVIS_ALLOWED_TAILSCALE_IPS=
```

## Son Gelinen Seviye

Jarvis Mission Control artik su kabiliyetlere dogru evrilmisti:

- `private AI operating system`
- `multi-agent workspace`
- `video understanding + intelligence`
- `learning memory`
- `task generation`
- `adaptive prioritization`
- `security hardening`
- `resume/replay`
- `single roof AI router`
- `desktop hologram assistant`

## Yeniden Kurulum / Kurtarma Icin Once Yapilacaklar

1. `server/bridge.py` ana omurgayi tekrar kur
2. `server/agents/video_link_agent.py` geri getir
3. `server/skills/redaction_skill.py` ve `server/skills/exec_hardening_skill.py` geri getir
4. `services/voice/voice_service.py` Turkce + desktop state destekli hale getir
5. `apps/desktop-hologram/` Electron overlay dosyalarini geri getir
6. `Claw3D/OpenClaw` baglantilarini tekrar kur
7. `logs/*.json/jsonl` memory dosyalarini tekrar olustur

## Claude / Antigravity'den Beklenenler

Claude veya Antigravity bu dosyayi okuyup su yaklasimla devam etmeli:

- once `bridge.py` + `video intelligence` + `security` omurgasini geri kursun
- sonra `desktop hologram` ve `voice runtime`
- sonra `memory/trend/task` zincirini geri baglasin
- en son `Kilo compat layer` ve `Moonshot-benzeri scene understanding`e gecsin

## Ozet Cekirdek Yol Haritasi

1. `bridge + router + providers`
2. `voice + hologram`
3. `video understanding canonical schema`
4. `feature memory + board + backlog + task`
5. `ID-only + resume/replay`
6. `redaction + hardening + audit`
7. `Kilo compat layer`
8. `advanced multimodal scene-by-scene understanding`
