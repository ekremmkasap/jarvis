# Implementation Plan: 006 - Jarvis Second Brain

Date: 2026-04-14
Branch: `006-jarvis-second-brain`

## Summary

006'nin amaci, 004-005 ustune daha buyuk bir omurga koymak:

- Jarvis'in ikinci beyin olarak Obsidian'a baglanmasi
- Masaustu otomasyonunun gercekten kullanilir hale gelmesi
- Coklu monitor, browser, WhatsApp ve Telegram voice yuzeylerinin tek bir yetenek katmaninda birlesmesi
- Hologram/copilot deneyiminin tek merkezli ve durum odakli hale gelmesi
- Jarvis'in kendi repo ve dis repo bilgisini analiz edip geri oneri uretebilmesi

Bu turdaki ilk implementasyon hedefi `Desktop I/O` entegrasyonudur. Cunku skill dosyasi ve testleri mevcut, fakat bridge akisi bu yuzeyi tam kullanmiyor.

## Current Repo Reality

Mevcut ve yeniden kullanilacak yuzeyler:

- `server/skills/desktop_io_skill.py`
- `tests/test_desktop_io_skill.py`
- `server/skills/playwright_browser_skill.py`
- `server/skills/whatsapp_skill.py`
- `server/whatsapp/wa_bridge.js`
- `server/skills/dual_monitor_vision_skill.py`
- `server/agents/vision_analyzer.py`
- `server/skills/persona_obsidian_skill.py`
- `server/skills/obsidian_auto_writer.py`
- `server/skills/wiki_auto_writer.py`
- `server/skills/agent_memory_skill.py`
- `server/skills/telegram_voice_handler.py`
- `server/skills/telegram_tts_reply.py`
- `apps/desktop-hologram/`

Append-only entegrasyon merkezi:

- `server/bridge.py`

## Delivery Order

### Phase 1 - Desktop I/O Stabilization

Hedef:
- "not defteri ac"
- "bunu yaz"
- "masaustunde txt olustur"

Yapilacaklar:
- `desktop_io_skill` komutlarini bridge'e APPEND-ONLY bagla
- dogal dil intentini `process_message` akisina ekle
- odakli pytest ile dogrula

### Phase 2 - Second Brain Backbone

Hedef:
- bridge -> Obsidian conversation log
- wiki + obsidian ortak kayit
- self-analysis ve repo summary akislarinin kalici kaydi

### Phase 3 - Extended Desktop + Browser

Hedef:
- WhatsApp otomasyonu
- Google/web arama ve ozet
- coklu monitor vision
- Telegram voice loop tamamlama

### Phase 4 - Copilot / Hologram Shell

Hedef:
- tek merkezli hologram panel
- wake/toggle davranisi
- particle swarm state machine

## Constraints

- `server/bridge.py` append-only
- Windows-first
- mevcut skillleri tekrar yazma, once reuse et
- her faz sonunda odakli smoke calistir

## Verification Strategy

Phase 1:

```powershell
python -m pytest tests/test_desktop_io_skill.py -q
```

Phase 2-4:
- ilgili skill testleri + hedefli smoke
- UI degisikligi varsa dar kapsamli build/typecheck
