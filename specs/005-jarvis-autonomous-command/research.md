# Research: MARK-XXXXVI — Jarvis Autonomous Command Layer

## Decision 1: Telegram Sesli Mesaj STT
- **Decision**: Groq Whisper API (`whisper-large-v3-turbo`) — HTTP multipart upload
- **Rationale**: `bridge.py:1767` zaten `_handle_whisper_command` ve `whisper_skill.transcribe_audio` var. Groq API key mevcut. Türkçe destekli. Ücretsiz tier yeterli.
- **Alternatives considered**: OpenAI Whisper local (ağır, ~1.5GB model), Azure STT (ücretli), Google STT (ücretli)
- **Gap**: Mevcut whisper handler dosya path'i bekliyor. Telegram `.ogg` dosyasını indirip path'e çeviren `telegram_voice_handler.py` eksik.

## Decision 2: Telegram TTS Yanıt
- **Decision**: `edge-tts` → `.mp3`/`.ogg` → `bot.send_voice()`
- **Rationale**: `bridge.py:4505` zaten `self.send_voice(chat_id, audio_path)` var. `hey_jarvis.py` zaten edge-tts kullanıyor. Altyapı hazır.
- **Gap**: Telegram voice reply için `audio_path` üretip `send_voice` çağıran wrapper yok.

## Decision 3: PC Kontrol Güvenlik Modeli
- **Decision**: `config/pc_control_whitelist.yaml` — komut → eylem mapping. Whitelist dışı hard-reject.
- **Rationale**: `server/skills/computer_control_skill.py` zaten var (pyautogui). `executor_agent.py:238` `pc_control: True` flag var. Whitelist katmanı eksik — her şeye izin veriyor.
- **Gap**: Whitelist dosyası yok. `/ekran-goruntusu`, `/pc-durum`, `/ac <app>` komutları bridge'de yok.

## Decision 4: Intent Classifier
- **Decision**: Mevcut `intent_skill.py` — `classify_intent()` + `handle_with_intent()` genişletilir
- **Rationale**: `bridge.py:866-875` zaten `intent_skill` import ediyor ve `classify_intent` + `handle_with_intent` çağırıyor (`bridge.py:4225`). Sıfırdan yazmaya gerek yok.
- **Gap**: Persona auto-switch intent type yok. `classify_intent` sonucu persona'ya bağlanmıyor.

## Decision 5: Obsidian Otomatik Yazım
- **Decision**: Araştırma/eylem sonuçları `persona_obsidian_skill.py::write_persona_note()` ile yazılır (004 feature'dan)
- **Rationale**: 004 spec ile zaten `server/skills/persona_obsidian_skill.py` planlandı. Bu feature sadece tetikleyici noktaları ekler.
- **Gap**: Auto-write hook — araştırma tamamlandığında, PC eylemi loglandığında otomatik tetikleyici yok.

## Decision 6: Wiki Entegrasyonu
- **Decision**: Mevcut `bridge.py:6668 _handle_wiki_command()` + `obsidian_sync_skill.run_wiki()` genişletilir
- **Rationale**: `/wiki` komutu zaten var. `wiki/index.md`, `wiki/log.md`, `wiki/hot.md` mevcut. Intent hook eklemek yeterli.
- **Gap**: "wiki'ye ekle" intent'i yok. `wiki/hot.md` otomatik güncellenmıyor.

## Decision 7: Codex Slot Binding
- **Decision**: `config/agents.yaml`'a `codex_slot` alanı + `bridge.py /codex-dispatch` güncelleme
- **Rationale**: `codex_orchestrator.py` ve slot sistemi zaten çalışıyor. Sadece persona → slot mapping eklenecek.
- **Gap**: `/codex-dispatch` şu an slot parametresi bekliyor, aktif personadan otomatik almıyor.

## Decision 8: Agent Memory API
- **Decision**: `GET /api/persona/<id>/memory` endpoint + `/hafiza` Telegram komutu
- **Rationale**: `state/agent_memory/<persona_id>/` dizin yapısı zaten var. JSONL okumak yeterli.
- **Gap**: HTTP endpoint yok. Telegram `/hafiza` komutu yok.

## Mevcut Altyapı Özeti

| Bileşen | Durum | Aksiyon |
|---------|-------|---------|
| Whisper STT | ✅ `whisper_skill.py` var | Telegram `.ogg` handler ekle |
| TTS send_voice | ✅ `bridge.py:4505` var | Voice reply wrapper ekle |
| PC control | ✅ `computer_control_skill.py` var | Whitelist katmanı ekle |
| Intent classifier | ✅ `intent_skill.py` var | Persona switch intent ekle |
| Obsidian yazım | ⚠️ 004'te planlandı | Auto-write hook ekle |
| Wiki komutları | ✅ `bridge.py:6668` var | Intent hook + hot.md auto |
| Codex dispatch | ✅ `codex_orchestrator.py` var | Persona → slot mapping ekle |
| Memory API | ❌ Yok | Endpoint + Telegram komutu ekle |
