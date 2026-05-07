# Jarvis — Mimari Genel Bakış

## Katmanlar

```
Voice Layer (Hey Jarvis)
    │
    ▼
Orchestrator (FastAPI :8091)
    │ WebSocket
    ▼
Dashboard (Next.js :3000)
    │
    ▼
Task Queue ──► Agent Runner ──► Model Router
                    │               │
              ┌─────┴──────┐    ┌───┴───────────────┐
              │            │    │                   │
         Agents...    Safety   Claude/OpenRouter  Ollama
                      Policy
```

## Ana Bileşenler

- **bridge.py** — Ana beyin (~1370 satır), Telegram komutlarını işler
- **Orchestrator** — FastAPI :8091, agent koordinasyonu
- **Dashboard** — Next.js :3000, web UI
- **Model Router** — Claude/OpenRouter + Ollama fallback

## Platform
- Pinokio: `C:/pinokio/api/ekrem/app/`
- Web UI: `http://127.0.0.1:8081`
- Ollama: `http://127.0.0.1:11434`

## İlgili Sayfalar
- [[ajanlar]]
- [[model-routing]]
- [[telegram-komutlari]]
- [[saas-vizyon]]
