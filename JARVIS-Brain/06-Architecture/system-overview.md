---
tags: [architecture, overview, system]
date: 2026-04-16
---

# Sistem Mimarisi — Genel Bakış

## Launcher Zinciri

```
SISTEM_J.bat (Desktop)
  └─► JARVIS_BASLAT.bat
        └─► master_launcher.py
              ├─► server/bridge.py --web-only   (HTTP 8081)
              ├─► hey_jarvis.py                 (STT G733 / TTS Piper tr_TR)
              └─► apps/desktop-hologram/        (Electron 340x520)
```

## Port Tablosu

| Port | Servis | Not |
|---|---|---|
| 8081 | `server/bridge.py` | Ana HTTP command router — Telegram/voice/web tek giriş |
| 11434 | Ollama | Lokal modeller (gemma4:e2b, deepseek-coder) |
| 7090 | OpenClaw gateway | Helper layer, Sabrican owner |

## Personalar (7)

Lazy singleton — aktive edilmeden proses oluşmaz.

| Persona | Alan | Voice |
|---|---|---|
| Seda | Code/debug/PR | AhmetNeural |
| Mert | Research/e-ticaret | AhmetNeural |
| Buse | Marketing | EmelNeural |
| Sabri | Ad agency CEO | AhmetNeural |
| Eren | YouTube/data | AhmetNeural |
| Luna | Cybersec (lab-only) | EmelNeural |
| Sabrican | Ops + [[02-Projects/openclaw-integration\|OpenClaw]] owner | AhmetNeural |

## OpenClaw Entegrasyonu (Aktif — 16 Nisan 2026)

**Owner:** Sabrican · **Port:** 7090 · **Helper layer — bridge.py/hey_jarvis.py'i değiştirmez**

### 4 Sub-agent
1. **openclaw_integrator** — genel task dispatcher
2. **gateway_health_watcher** — health monitoring
3. **channel_delivery_operator** — mesaj iletim
4. **auth_profile_sync** — profil senkronizasyon

### Telegram Komutları
- `/openclaw-health` — gateway snapshot
- `/openclaw-skill` — skill catalog runner
- `/sabri-openclaw` — Sabrican master komut
- `/sabrican-subagents` — sub-agent zinciri

Detay: [[02-Projects/openclaw-integration]]

## State Dosyaları (runtime, commit edilmez)

```
state/active_agent.json       — aktif persona
state/agent_memory/<id>/      — per-persona conversation history
state/codex_cooldowns.json    — Codex slot cooldowns
```

## Model Routing
`config/model_router.yml` — provider priority chain:
- **Cloud:** Groq → Gemini
- **Lokal:** Ollama (fallback)

Detay: [[03-Knowledge/opus-4-7-release]]

## MCP Servers
- `jarvis-brain` — @bitbonsai/mcpvault — bu vault
- Gmail, Google Calendar, Notion, Stripe, Supabase, Context7 — global MCP

## İlgili
- [[02-Projects/jarvis-mission-control]]
- [[02-Projects/openclaw-integration]]
- [[02-Projects/cloud-manager-system]]
