---
tags: [project, openclaw, sabrican, helper-layer]
date: 2026-04-16
status: enabled
---

# OpenClaw Entegrasyonu

OpenClaw Jarvis'in **secondary helper layer**'ı — `bridge.py` ve `hey_jarvis.py`'i **değiştirmez**, yanına kurulur. Owner: **Sabrican** persona.

Port: **7090** (OpenClaw gateway)

## Dosyalar

| Dosya | Rol |
|---|---|
| `server/openclaw_bridge.py` | 7 dispatch/runner fonksiyonu |
| `server/skills/swarm_skill.py` | Sabrican routing (line 271-284) |
| `server/bridge.py` | 4 Telegram komutu (line 6755, 6789, 6813, 6829) |
| `config/agents.yaml` | activation_status: enabled (line 338) |
| `tests/test_openclaw_bridge.py` | ✅ geçiyor (50 satır) |

## Sub-agent'lar (4)

1. **openclaw_integrator** — genel task dispatcher
2. **gateway_health_watcher** — health monitoring
3. **channel_delivery_operator** — mesaj iletim
4. **auth_profile_sync** — profil senkronizasyon

## Dispatch Fonksiyonları (`server/openclaw_bridge.py`)

- `dispatch_research()` — async, kısa araştırma (line 347)
- `dispatch_code_task()` — async, kod üretimi (line 353)
- `run_gateway_health_watcher()` (line 364)
- `run_channel_delivery_operator()` (line 369)
- `run_auth_profile_sync()` (line 374)
- `run_openclaw_integrator()` (line 379)
- `run_agent_task()` — async helper (line 184)

## Telegram Komutları

| Komut | Ne Yapar |
|---|---|
| `/sabri-openclaw` | research / skill-pack / channel / agent / memory / all |
| `/sabrican-subagents` | Zincir sub-agent çalıştır |
| `/openclaw-health` | Gateway + CLI snapshot |
| `/openclaw-skill` | Skill catalog runner |

## Routing Örneği (swarm_skill.py:271-284)

```python
if personas and "sabrican" in [p.lower() for p in personas]:
    # logs "Sabrican → OpenClaw integrator"
    # routes goal to run_openclaw_integrator()
```

## TODO
- [ ] `config/agents.yaml` Sabrican-specific activation_status bloğu ekle
- [ ] Her sub-agent için ayrı test (şu an generic health test var)
