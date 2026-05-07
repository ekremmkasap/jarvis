# Tasks: 006 - Jarvis Ikinci Beyin

Branch: `006-jarvis-second-brain`
Updated: 2026-04-14

## Phase 1 - Desktop I/O

- [x] `server/skills/desktop_io_skill.py` mevcut
- [x] `tests/test_desktop_io_skill.py` mevcut
- [ ] `server/bridge.py` append-only: `/notac`, `/notyaz`, `/dosyaolustur`, `/dosyaoku` komutlarini `desktop_io_skill` uzerinden expose et
- [ ] `server/bridge.py` append-only: dogal dilde "not defteri ac", "bunu yaz", "dosya olustur" intentini `handle_note_intent()` ile isle
- [ ] `python -m pytest tests/test_desktop_io_skill.py -q`

## Phase 2 - Dual Monitor Vision

- [x] `server/skills/dual_monitor_vision_skill.py` mevcut
- [x] `tests/test_dual_monitor_vision.py` mevcut
- [ ] `server/bridge.py` append-only: `/ekrantara` ve `/ekrananaliz` komutlarini expose et
- [ ] "ekrani analiz et" dogal dilini dual-monitor skill'e route et
- [ ] `python -m pytest tests/test_dual_monitor_vision.py -q`

## Phase 3 - Obsidian Second Brain

- [x] `server/skills/persona_obsidian_skill.py` mevcut
- [x] `server/skills/obsidian_auto_writer.py` mevcut
- [x] `server/skills/wiki_auto_writer.py` mevcut
- [x] `server/skills/agent_memory_skill.py` mevcut
- [ ] `obsidian_auto_writer` icine conversation log yuzeyi ekle
- [ ] `server/bridge.py` append-only: onemli yanitlari/persona akislarini Obsidian'a logla
- [ ] wiki + obsidian sicak ozet akisini birlestir

## Phase 4 - Browser / WhatsApp / Google

- [x] `server/skills/playwright_browser_skill.py` mevcut
- [x] `server/skills/whatsapp_skill.py` ve `server/whatsapp/wa_bridge.js` mevcut
- [ ] WhatsApp yuzeyinin mevcut calisma modelini netlestir ve Windows-first akisa indir
- [ ] Google/web arama komutlarini browser skill ile standartlastir
- [ ] bridge komutlari ve intentler ekle

## Phase 5 - Telegram Voice + Self Analysis

- [x] `server/skills/telegram_voice_handler.py` mevcut
- [x] `server/skills/telegram_tts_reply.py` mevcut
- [x] `server/skills/sub_agent_runner.py` mevcut
- [ ] voice -> intent -> reply -> tts loopunu ikinci beyin kaydiyla birlestir
- [ ] "kendi kodunu analiz et" akisini repo tarama + not dusme ile ekle

## Phase 6 - Hologram / Copilot Shell

- [x] `apps/desktop-hologram/main.js` mevcut
- [ ] tek merkezli panel davranisi
- [ ] wake/toggle mekanizmasi
- [ ] particle swarm state machine
- [ ] performance fallback profilleri
