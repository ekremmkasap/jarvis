---
tags: [project, jarvis, core]
date: 2026-04-16
status: active
---

# Jarvis Mission Control

Self-hosted Türkçe AI asistan SaaS. Ekrem (ekremmkasap) tarafından geliştiriliyor.

## Repo
`C:/Users/sergen/Desktop/jarvis-mission-control/`

## Launcher Chain
```
SISTEM_J.bat (Desktop)
  └─► JARVIS_BASLAT.bat
        └─► master_launcher.py
              ├─► server/bridge.py --web-only   (HTTP, port 8081)
              ├─► hey_jarvis.py                 (STT Logitech G733 / TTS Piper tr_TR)
              └─► apps/desktop-hologram/        (Electron, 340x520 sağ alt köşe)
```

## Personalar (7)

| Persona | Alan | Codex Slot | Voice |
|---|---|---|---|
| Seda | Code / debug / PR | forge | AhmetNeural |
| Mert | Research / e-ticaret | nexus | AhmetNeural |
| Buse | Sosyal medya / marketing | spark | EmelNeural |
| Sabri | Reklam ajansı CEO | atlas | AhmetNeural |
| Eren | YouTube / data | spark | AhmetNeural |
| Luna | Siber güvenlik (lab-only) | shield | EmelNeural |
| Sabrican | Ops / automation / [[openclaw-integration\|OpenClaw]] | nexus | AhmetNeural |

## Cloud API'ler
- **Groq** ✅ — llama-3.1-8b-instant, llama-3.3-70b, llama-4-scout (0.58sn)
- **Gemini** ✅ — 2.5-flash, 2.5-pro (0.91sn, 1M context)
- **Cerebras** — API key bekleniyor

## Ollama (Lokal)
- `gemma4:e2b` (5.1B) — genel
- `deepseek-coder:latest` (1B) — hızlı kod

## SaaS Modeli
Starter ₺1500 / Pro ₺3500 / Agency ₺7500 · Hedef: 20 müşteri → ₺80.000/ay

## Aktif Branch
`008-swarm-skills-integration`

## Bağlantılar
- [[openclaw-integration]] — Sabrican'ın helper layer'ı
- [[cloud-manager-system]] — AWS yönetim planı
- [[06-Architecture/system-overview]] — port ve data flow tablosu
