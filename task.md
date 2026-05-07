# Claude -> Jarvis Resume Plan

Updated: 2026-04-16

Bu dosya Claude ile birlikte hazirlandi. Jarvis 30 dakika sonra veya daha sonra yeniden acildiginda ilk olarak bu dosyayi okusun ve buradaki sirayla devam etsin.

## Startup Handoff

Jarvis acildiginda uygulanacak ilk mesaj:

`Jarvis, once C:\Users\sergen\Desktop\jarvis-mission-control\task.md dosyasini oku. Bu plan Claude ile hazirlandi. Buradaki durum, bulgular ve siraya gore kaldigin yerden devam et.`

## Current Status

- JARVIS-Brain vault olusturma isi buyuk oranda tamamlandi.
- `C:\Users\sergen\Desktop\JARVIS-Brain` altinda 13 markdown dosyasi yazildi.
- `CLAUDE.md` icine JARVIS-Brain Vault blogu eklendi.
- `C:\Users\sergen\.claude.json` icindeki `jarvis-mission-control` proje bloguna `jarvis-brain` MCP server eklendi.
- Verification adimi yarida kaldi; rate limit ve session interruption yuzunden tamamlanmadi.
- Telegram davranis bozukluklari analiz edildi ve net bir duzeltme plani cikti.
- Jarvis su anda bridge/health acisindan cevrim disi gorunuyor:
  - `http://127.0.0.1:8081/health` -> timeout
  - `http://127.0.0.1:8081/api/status` -> timeout
- Buna ragmen sistemde bazi `python`, `node`, `electron` processleri hala ayakta. Yani tam kapanmis degil; muhtemelen parcalanmis / yarim ayakta bir runtime var.

## Resume Priority Order

1. Jarvis'in neden offline oldugunu netlestir.
2. JARVIS-Brain verification'i tamamla.
3. Bridge import/path sorununun kok nedenini kapat.
4. Telegram routing ve persona drift sorunlarini duzelt.
5. Voice / STT / media akisini tek hatta indir.
6. PC tarafindaki kasma ve gecikme sebeplerini azalt.

## Task 1 - Offline Recovery

Hedef: Jarvis'i tekrar saglikli sekilde ayağa kaldirmak.

### Bulgular

- Bridge health endpoint cevap vermiyor.
- Daha once bridge bootstrap sirasinda `services.orchestrator` import hatasi gorulmustu.
- Repo icinde hem kokte `services/` hem de `server/services/` var; import resolution karisiyor.
- Hologram/Electron tarafi ayakta olabilir ama bridge saglikli degilse sistem kullanici tarafinda "cevrim disi" gibi gorunur.

### Yapilacaklar

1. `python server\bridge.py --web-only` komutunu tek basina calistirip bootstrap hatasini tekrar uret.
2. `server/telegram_webhook.py` ve `server/bridge.py` icindeki `services.*` importlarini deterministic hale getir.
3. Kok paket ile `server/services` cakismasini bitir:
   - ya kok `services` paketini netlestir,
   - ya da `server.services` / `services` importlarini tutarli hale getir.
4. Bridge acildiktan sonra:
   - `GET /health`
   - `GET /api/status`
   - Telegram polling
   - voice runtime fallback durumu
   yeniden dogrulansin.

### Verification

- `python server\bridge.py --web-only`
- `curl` / Python ile `8081/health`
- `curl` / Python ile `8081/api/status`

## Task 2 - JARVIS-Brain Verification

Bu kisim yarida kaldi; once bunu bitir.

### Beklenen Durum

- `C:\Users\sergen\Desktop\JARVIS-Brain\` altinda:
  - `01-Daily-Notes`
  - `02-Projects`
  - `03-Knowledge`
  - `04-Dev-Log`
  - `05-Resources`
  - `06-Architecture`
  - `README.md`
- En az 13 `.md` dosyasi content ile dolu olmali.
- `C:\Users\sergen\.claude.json` icinde `jarvis-brain` MCP girisi gorunmeli.
- `CLAUDE.md` icinde JARVIS-Brain Vault blogu gorunmeli.

### Verification Checklist

1. Klasor yapisini listele.
2. Markdown dosya sayisini say.
3. Su dosyalari acip icerigi dogrula:
   - `03-Knowledge/graphify-token-optimization.md`
   - `04-Dev-Log/2026-04-16.md`
   - `05-Resources/instagram-sources.md`
4. `.claude.json` icin JSON parse dogrulamasi yap.
5. `CLAUDE.md` icindeki yeni blogu kontrol et.
6. Aşağıdaki regression komutlarini calistir:
   - `python -m py_compile server/bridge.py server/openclaw_bridge.py server/skills/swarm_skill.py`
   - `python -m pytest tests/test_openclaw_bridge.py -q`

## Task 3 - Telegram Issues Analysis Summary

16 gunluk transcript icin ana bulgular:

### 1. Persona Drift

- Telegram lane Jarvis olsa bile cevap icine farkli persona promptu sizabiliyor.
- `call_ollama` tarafinda aktif persona inject'i lane-aware degil.
- Dogal dil router otomatik persona switch yapiyor.
- Kullanici "Seda kaldirildi" dese de repo ustunde Seda kayitlari hala duruyor:
  - `config/agents.yaml`
  - `server/persona_manager.py`
  - `state/agent_world.json`

### 2. Basit Komutlarin Yanlis Hatta Dusmesi

- `sarki ac`, `instagram ac`, `youtube ac` gibi komutlar bazen dogrudan app-open hattina gitmek yerine `/yap` bilgisayar ajanina dusuyor.
- `/yap` ise screenshot + vision + LLM plan + pyautogui zinciri calistiriyor.
- Bu zincir basit app launch komutlari icin asiri agir ve kirilgan.

### 3. Telegram Voice Stack Cifte

- Legacy `voice_skill.py` tarzi eski handler mantigi hala iz birakiyor.
- Autonomous `telegram_voice_handler.py` de ayri bir akis kuruyor.
- Bu da transcriptte cift mesaj, tutarsiz hata ve farkli STT davranisina yol aciyor.

### 4. Media UX Eksik

- Photo var, voice var.
- Video icin net bir handler gorunmuyor.
- `/video_frames` transcriptte kullaniliyor ama kod tarafinda net bir akis olarak oturmamis.
- Cift monitor screenshot beklentisiyle mevcut tek ekran mantigi uyusmuyor.

### 5. Telegram Gurultusu

- Startup banner tekrar tekrar gonderiliyor.
- `Codex Health: FORGE sessiz` gibi operator uyarilari ayni chat'te gosteriliyor.
- `Isleniyor...` spam'i fazla.

## Task 4 - Telegram Stabilization Plan

### Phase A - Persona ve Routing Stabilizasyonu

1. Telegram lane icin varsayilan persona `jarvis` olmali.
2. Lane disi global persona inject kapatilacak veya lane-aware hale getirilecek.
3. Telegram'da explicit persona komutu yoksa auto-switch kapatilacak ya da daha sert confidence threshold konacak.
4. Kullaniciya gore kaldirildiysa Seda configten ve stale stateden temizlenecek.

### Phase B - Command Routing

1. `ac`, `baslat`, `oynat` ailesi icin whitelist tabanli hizli komut yolu oncelikli olacak.
2. `YouTube`, `Instagram`, `Spotify`, `Chrome`, `Explorer` icin acik intent map eklenecek.
3. Yazim hatasi normalize edilecek:
   - `inatagram` -> `instagram`
   - benzeri turkce/ascii varyasyonlar desteklenecek.
4. Basit uygulama acma istekleri `/yap` zincirine dusmeyecek.

### Phase C - Voice

1. Telegram voice hattinda tek resmi yol birak:
   - `telegram_voice_handler.py`
   - `whisper_skill.py`
   - `telegram_tts_reply.py`
2. Legacy Telegram voice akisi devreden cikartilacak.
3. STT hatalarini kullaniciya tek satir, sade dille ver; detay logda kalsin.
4. `NoneType.strip` benzeri hatalar icin empty transcript guard ekle.

### Phase D - Media

1. `video` / `video_note` icin handler ekle.
2. `/video_frames` gercekten implement edilsin.
3. Cift monitor screenshot secenekleri ekle:
   - `1. ekran`
   - `2. ekran`
   - `tum ekranlar`
4. Screenshot gonderiminde caption / aciklama opsiyonu olsun.

### Phase E - Noise Reduction

1. Startup banner rate-limit.
2. Codex health uyarilarini ayri admin hattina veya ozet rapora tasi.
3. `Isleniyor...` sadece uzun islerde bir kere gonderilsin.

## Task 5 - Performance / Kasma / Gecikme Planı

Bu kisim kullanici tarafinda "neden donma, gecikme, kasma oluyor" sorusuna cevap.

### Muhtemel Kok Nedenler

1. Bridge her Telegram update icin limitsiz thread aciyor.
2. Screenshot / vision / STT / ffmpeg / whisper gibi agir isler request yolunda senkron calisiyor.
3. Electron/hologram tarafinda yuksek polling var; onceki task'ta 900 ms polling'e inilmisti.
4. Ayni anda birden fazla `python`, `node`, `electron` processi acik.
5. `desktop` ustunde recursive file search gibi agir isler UI/voice deneyimini kitliyor.
6. Startup ve health watcher gurultusu kullanici akisina giriyor.

### Iyilestirme Planı

1. Telegram update handling icin thread-per-update yerine queue veya bounded executor kullan.
2. Agir isleri ana request path'inden ayir:
   - vision
   - whisper
   - ffmpeg
   - pyautogui / UI automation
3. Idle durumda hologram polling'i yukselt:
   - 900 ms yerine adaptif backoff
   - idle: 1500-2500 ms
   - aktif konusma: daha hizli
4. Bridge icin latency loglari ekle:
   - route
   - handler
   - latency_ms
   - timeout
5. Process duplication kontrolu yap:
   - duplicate electron
   - duplicate node
   - duplicate voice runtime
6. Recursive search ve benzeri agir tool'lara:
   - timeout
   - skip dirs (`node_modules`, `.git`, `external-repos`)
   - max depth / max result
   ekle.
7. Health notifier ve startup mesajlarini rate-limit et.

### Performance Verification

1. Telegram'da ard arda 10 basit mesaj at:
   - `naber`
   - `youtube ac`
   - `instagram ac`
   - `ekran goruntusu at`
2. Ortalama cevap suresi kaydet.
3. CPU / RAM / process sayisi karsilastir.
4. Hologram acikken ve kapaliyken farki olc.

## Task 6 - Mark-XXXV / Voice Blocking Note

Ek not: Voice tarafinda daha once su kritik bulgu cikti:

- `external-repos/Mark-XXXV/actions/file_controller.py`
- `find_files(name='jarvis mission kontrol wiki', path='desktop')`

Bu tarz cagrilar Desktop altinda recursive aramaya daldigi icin repo + `node_modules` + `external-repos` icine gomulup sistemi bekletebilir.

Bu da hem sesli akisi hem genel sistem responsiveness'ini bozabilir.

### Yapilacaklar

1. `find_files` icin timeout ekle.
2. `node_modules`, `.git`, `external-repos`, `__pycache__` skip et.
3. Path token match'i iyilestir.
4. Directory resultlerini de destekle.

## Suggested Execution Order For Jarvis

Jarvis acildiginda dogrudan bu sirayla git:

1. Offline recovery
2. JARVIS-Brain verification
3. Telegram persona drift fix
4. Telegram command routing fix
5. Voice stack simplification
6. Media/video support
7. Performance tuning

## Short Operator Note

Eger kullanici "kaldigimiz yerden devam et" derse, Jarvis bu dosyayi esas alsin. Bu plan Claude ile birlikte cikarildi; dolayisiyla buradaki maddeler onceki oturumun resmi handoff dokumani olarak kabul edilmeli.

---

# Task 7 - Persona Restructure Handoff

Updated: 2026-04-17

Bu ek plan Claude Code limitte kalinca eklendi. Kullanici yeni karar verdi: fonksiyonel ajanlardan domain/sektor bazli musteri-facing ajanlara gecilecek.

## Claude'un Biraktigi Yer

- Plan onaylandi.
- `config/agents.yaml` icindeki `personas:` blogu kismen/Buyuk oranda yeniden yazildi.
- Yeni hedef mimari:
  - 7 gorunur musteri-facing persona
  - 2 gizli ic ajan
- Claude limitte kaldigi icin uygulama yarida kesildi.

## Final Persona Karari

### Gorunur 7 Domain Persona

1. Sabri - Reklam Ajansi / AI creative director
2. Luna - Cyber / offensive + OSINT / lab-only
3. Buse - Sosyal medya / icerik fabrikasi
4. Deniz - E-ticaret / pazaryeri operasyonu
5. Eren - YouTube + video analytics
6. Mert - Derin arastirma / rakip analizi
7. Zeynep - Defensive guvenlik / KVKK / compliance audit

### Gizli Ic Ajanlar

1. Seda - dev_mode / kod-debug-PR / `JARVIS_DEV_MODE`
2. Sabrican - admin_mode / ops-deploy-OpenClaw / `JARVIS_ADMIN_MODE`

## Slot Dagilimi

- forge: Seda (gizli dev)
- nexus: Mert, Deniz, Sabrican (gizli ops)
- spark: Buse, Eren
- atlas: Sabri
- shield: Luna, Zeynep

## Kalan Implementasyon

1. `server/persona_manager.py`
   - `DEFAULT_PERSONAS` yeni 7 + 2 ic ajan yapisina guncellenecek.
   - `DEFAULT_CODEX_SLOT_MAP` yeni slot dagilimina guncellenecek.
   - `visibility: internal` ve `requires_flag` alanlari korunacak.
   - `list_personas()` musteri-facing listede internal ajanlari varsayilan olarak gizlemeli.
   - Explicit dev/admin flag varsa internal ajanlar gorunebilir.

2. `config/codex_slots.yaml`
   - persona-slot map yeni plana gore guncellenecek.

3. Hologram renkleri
   - Deniz: `#1abc9c`
   - Zeynep: `#34495e`
   - Gerekli dosya buyuk ihtimal `apps/desktop-hologram/renderer.js`.

4. Dokumantasyon
   - `CLAUDE.md`
   - `.claude/CLAUDE.md`
   - Persona tablosu yeni 7 + 2 ic ajan modeline guncellenecek.

5. Testler
   - `tests/test_persona_manager.py`
   - `tests/test_codex_management.py`
   - Gerekirse internal visibility beklentileri eklenecek.

## Dogrulama

1. `python -m py_compile server/bridge.py server/persona_manager.py`
2. `python -m pytest tests/test_persona_manager.py tests/test_codex_management.py -q`
3. Bridge ayaktaysa:
   - `GET /api/personas` -> 7 gorunur persona
   - `Seda` ve `Sabrican` varsayilan public listede gorunmemeli
4. Telegram smoke:
   - `/sabri`
   - `/luna`
   - `/buse`
   - `/deniz`
   - `/eren`
   - `/mert`
   - `/zeynep`
5. Dev flag smoke:
   - `JARVIS_DEV_MODE=1` ile Seda gorunebilir/aktiflesebilir
   - flag yokken Seda musteri-facing listede gorunmemeli

## Risk Notlari

- `config/agents.yaml` su anda degismis durumda; geri alma yapma.
- Repo dirty; kullanici ve diger ajan degisikliklerine dokunma.
- Eski testler `seda` ve `sabrican` ID'lerine bagimli olabilir. Bu ID'ler silinmeyecek, internal yapilacak.
- Kodda "visible" yerine "visibility" veya "requires_flag" standardi secilmeli ve tutarli kullanilmali.

## 2026-04-17 Codex Devam Durumu

Codex bu handoff uzerinden Task 7'nin ana uygulamasini tamamladi.

### Guncellenen Dosyalar

1. `server/persona_manager.py`
   - DEFAULT_PERSONAS yeni 7 gorunur + 2 internal ajan modeline cekildi.
   - DEFAULT_CODEX_SLOT_MAP yeni slot dagilimina cekildi.
   - `visibility: internal` ve `requires_flag` runtime payload'inda korunuyor.
   - `list_personas()` varsayilan olarak sadece gorunur ajanlari donduruyor.
   - `JARVIS_DEV_MODE=1` ile Seda gorunebilir; `JARVIS_ADMIN_MODE=1` ile Sabrican gorunebilir.
   - Flag yokken Seda/Sabrican switch engelleniyor.

2. `config/codex_slots.yaml`
   - forge: Seda
   - nexus: Mert, Deniz, Sabrican
   - spark: Buse, Eren
   - atlas: Sabri
   - shield: Luna, Zeynep

3. `apps/desktop-hologram/renderer.js`
   - AGENTS fallback listesi yeni domain rollerine gore guncellendi.
   - Deniz ve Zeynep eklendi.
   - speakerNames mapping'i yeni persona setiyle senkronlandi.

4. `CLAUDE.md`
   - Persona tablosu yeni 7 + 2 internal modele guncellendi.

5. `.claude/CLAUDE.md`
   - Persona Sistemi (2026-04-17) bolumu eklendi.

6. `tests/test_persona_manager.py`
   - Yeni 7 gorunur persona beklentisi eklendi.
   - Internal persona flag testleri eklendi.

### Dogrulama Sonuclari

- `python -m pytest tests\test_persona_manager.py -q` -> 10 passed
- `python -m pytest tests\test_codex_management.py -q` -> 18 passed
- `python -m py_compile server\bridge.py server\persona_manager.py` -> OK
- `node --check apps\desktop-hologram\renderer.js` -> OK
- `config/agents.yaml` ve `config/codex_slots.yaml` YAML parse -> OK
- Runtime Python smoke:
  - flag yokken `list_personas()` -> `sabri,luna,buse,deniz,eren,mert,zeynep`
  - `JARVIS_DEV_MODE=1` ile `list_personas()` -> gorunur 7 + `seda`
  - flag yokken `switch_persona('seda')` -> false

### Panel / State Debug Bulgusu

- Bridge su anda calisiyor, `/health` cevap veriyor ama status `degraded`.
- `/api/persona/active` su anda `jarvis` donduruyor.
- `state/active_agent.json` icinde default, web, voice, telegram lane'leri `jarvis`.
- Hologram WebSocket kullanmiyor; `apps/desktop-hologram/renderer.js` icerisinde `/api/persona/active` endpoint'ini polling ile okuyor.
- Bu yuzden "Seda'ya switch yaptim ama panelde gorunmedi" sorununun ilk nedeni panel degil:
  1. switch state'e yazilmamis olabilir,
  2. calisan bridge eski `persona_manager.py` kodunu kullaniyor olabilir,
  3. Seda artik internal oldugu icin `JARVIS_DEV_MODE=1` olmadan switch engellenir,
  4. Electron renderer restart edilmeden yeni fallback persona listesi yuklenmez.

### Kalan Runtime Adimi

Yeni kodun canli sistemde yuklenmesi icin canonical restart gerekiyor:

1. Bridge + hologram + voice stack'i temiz kapat.
2. `JARVIS_DEV_MODE=1` sadece dev oturumunda gerekiyorsa set et.
3. `JARVIS_BASLAT.bat` veya canonical launcher ile yeniden baslat.
4. Telegram smoke:
   - `/sabri`
   - `/luna`
   - `/buse`
   - `/deniz`
   - `/eren`
   - `/mert`
   - `/zeynep`
5. Panel smoke:
   - switch sonrasi `state/active_agent.json` ilgili lane'i degisiyor mu?
   - `GET /api/persona/active?lane=telegram` yeni persona donduruyor mu?
   - hologram 1-3 saniye icinde renk/isim degistiriyor mu?

Not: `/api/personas` endpoint'i su an bridge'de yok ve 404 donuyor. Dogrulamada bu endpoint istenecekse bridge'e additive bir endpoint eklenmeli.
