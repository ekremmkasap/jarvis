# Implementation Plan: Dijital Ajan Dünyası V2 — PersonaManager

**Branch**: `003-dijital-ajan-v2` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)

## Summary

3 katmanlı persona mimarisi: Persona Plane (kimlik/state) → Runtime Plane (tek bridge + TTS) → Execution Plane (Codex slot binding, sonraki faz). V2'de Faz 1-3 tamamlanır: persona switch, hologram renk geçişi, per-persona skill routing + hafıza.

## Technical Context

**Language/Version**: Python 3.11 (bridge + PersonaManager), TypeScript/Electron (hologram), JavaScript (renderer.js)  
**Primary Dependencies**: pyyaml (mevcut), edge-tts veya Piper (mevcut hey_jarvis.py TTS), APScheduler (mevcut)  
**Storage**:
- `state/active_agent.json` — aktif persona + switch timestamp
- `config/agents.yaml` — 7 persona profili (güncellenecek)
- `state/agent_memory/<persona>/` — per-persona kalıcı hafıza
- `state/agent_world.json` — aktivasyon geçmişi

**Constraints**: bridge.py backward-safe; hey_jarvis.py'e minimal hook (mevcut TTS akışı bozulmaz); hologram renderer.js yalnızca renk/animasyon değişir

## Project Structure

```
server/
├── persona_manager.py          # YENİ — 7 persona yönetimi
├── bridge.py                   # DEĞİŞİKLİK — +/persona/*, +/api/persona/active
└── skills/
    └── persona_skill.py        # YENİ — "kim aktif", "buse ile konuş" skill wrapper

config/
└── agents.yaml                 # DEĞİŞİKLİK — 7 persona tam profil (renk, ses, sistem prompt)

state/
├── active_agent.json           # YENİ — {id, name, color, voice, activated_at}
├── agent_world.json            # YENİ — aktivasyon log
└── agent_memory/               # YENİ — per-persona dizin

hey_jarvis.py                   # DEĞİŞİKLİK — aktif persona sesini TTS'e enjekte eder

apps/desktop-hologram/
├── renderer.js                 # DEĞİŞİKLİK — /api/persona/active polling + renk güncelleme
└── styles.css                  # DEĞİŞİKLİK — .persona-* renk sınıfları + fade animasyon
```

## Faz Sırası

**Faz 0** (BLOKER): bridge.py /health 200 dönmeli — zaten OK  
**Faz 1**: PersonaManager + persona switch + Telegram/ses komutları  
**Faz 2**: Hologram renk geçişi (renderer.js polling)  
**Faz 3**: Per-persona skill routing + sistem prompt injection  
**Faz 4**: Per-persona hafıza (state/agent_memory/)

## Constitution Check

| Prensip | Durum | Notlar |
|---------|-------|--------|
| I. Local-First | ✅ | Tüm state lokal dosyalar |
| II. Spec Before Impl | ✅ | specify→plan→tasks→implement |
| III. Security | ✅ | Persona config'de credential yok |
| IV. Read Before Write | ✅ | bridge.py, renderer.js okunacak |
| V. Verify | ⚠️ GATE | Smoke: "Buse ile konuş" → JSON state + TTS çıktısı |
