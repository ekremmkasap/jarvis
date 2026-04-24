# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Commands

```bash
# Run all tests
python -m pytest tests/ -q

# Run a single test file
python -m pytest tests/test_persona_manager.py -q

# Run a single test by name
python -m pytest tests/test_persona_manager.py::test_switch_persona -q

# Syntax check
python -m py_compile server/bridge.py

# Lint
ruff check server/

# TypeScript check (web-ui)
cd apps/web-ui && node_modules/.bin/tsc.cmd --noEmit
```

---

## Architecture

### Launcher Chain
```
JARVIS_BASLAT.bat
  └─► master_launcher.py
        ├─► server/bridge.py --web-only  (HTTP, port 8081)
        ├─► hey_jarvis.py                (STT: Logitech G733, TTS: Piper tr_TR / edge-tts)
        └─► apps/desktop-hologram/       (Electron, npm start)
```

### Core Components

| File | Role |
|------|------|
| `server/bridge.py` | Central HTTP command router — all Telegram, voice, web commands land here. **Backward-safe: never break existing routes.** |
| `hey_jarvis.py` | Voice loop — STT → LLM → TTS. Reads active persona voice from `state/active_agent.json`. |
| `master_launcher.py` | Process orchestrator with canonical boot order. |
| `apps/desktop-hologram/renderer.js` | Electron UI — polls `/api/persona/active` and `/api/swarm-status` for color and activity state. |
| `server/persona_manager.py` | Persona switching runtime. Writes `state/active_agent.json` and `state/agent_world.json`. |
| `config/agents.yaml` | Single source of truth for persona definitions (canonical `personas:` block). |

### Persona System

7 customer-facing personas, plus 2 internal-only operators:

| Persona | Domain | Codex Slot | Voice |
|---------|--------|------------|-------|
| Sabri | Reklam ajansi / AI creative director | atlas | AhmetNeural |
| Luna | Cyber / OSINT / offensive lab-only | shield | EmelNeural |
| Buse | Sosyal medya / icerik fabrikasi | spark | EmelNeural |
| Deniz | E-ticaret / pazaryeri operasyonu | nexus | AhmetNeural |
| Eren | YouTube / video analytics | spark | AhmetNeural |
| Mert | Derin arastirma / rakip analizi | nexus | AhmetNeural |
| Zeynep | Defensive security / KVKK / audit | shield | EmelNeural |
| Seda | Internal dev/code operator (`JARVIS_DEV_MODE`) | forge | AhmetNeural |
| Sabrican | Internal ops/OpenClaw operator (`JARVIS_ADMIN_MODE`) | nexus | AhmetNeural |

Switch flow: `Buse ile konus` → `detect_switch_from_text` → `persona_manager.switch_persona()` → `state/active_agent.json` → hologram polling.

Handoff canon: Jarvis says `Buse'ye baglaniyorum.` → persona replies in its own role and voice.

Persona full specs (system prompts, sub-agents, handoff dialogs):
`config/agents.yaml`

### Model Routing

`config/model_router.yml` — provider priority chain. Active: Groq, Gemini, Ollama, GLM, OpenRouter.

### Skills

`server/skills/` — Python skill files, self-contained. Register new skills in `server/bridge.py`.

### State Files (runtime, not committed)

```
state/active_agent.json       — active persona
state/agent_memory/<id>/      — per-persona conversation history
state/codex_cooldowns.json    — Codex slot cooldowns
```

### Codex Control Plane

`account_manager` → `codex_task_router` → `codex_orchestrator` → `codex_job_manager`

5 slots: `atlas`, `forge`, `nexus`, `shield`, `spark`. Bridge endpoints: `/api/codex/slots`, `/api/codex/jobs`, `/api/codex/queue`, `/api/codex/health`, `/api/codex/audit`, `/api/codex/result`, `/api/codex/status`.

Telegram commands: `/codex`, `/codex-swarm`, `/codex-durum`, `/codex-kuyruk`, `/codex-saglik`, `/codex-sonuc`.

### OpenClaw

Research result: secondary/helper layer, owned by Sabrican. Does not replace `bridge.py` or `hey_jarvis.py`.

### JARVIS-Brain Vault (2026-04-16)

Obsidian vault: `C:/Users/sergen/Desktop/JARVIS-Brain/`
- MCP server: `jarvis-brain` (@bitbonsai/mcpvault) — kayıtlı: `~/.claude.json` proje bloğu
- Yapı: `01-Daily-Notes/` · `02-Projects/` · `03-Knowledge/` · `04-Dev-Log/` · `05-Resources/` · `06-Architecture/`
- Amaç: günlük dev log, Instagram/GitHub kaynak arşivi, mimari kararlar, Jarvis kalıcı hafızası

---

## Critical Rules

- **`server/bridge.py`** — ask before changing. Commands must be additive, never break existing routes.
- **`master_launcher.py`** — ask before changing. Process lifecycle is fragile.
- **`.env`** — credentials never log to UI or console.
- **`config/agents.yaml`** — only the canonical `personas:` block is authoritative.
- **`Luna`** — hard-reject live targets, unauthorized exploits, active attacks.
- **Secrets** — redact before any log write or UI payload (`account_manager.py` has the helper).

---

## Spec Workflow

For changes touching more than one file or layer:
```
/speckit.specify → /speckit.plan → /speckit.tasks → /speckit.implement
```
Artifacts live under `specs/`. Active implementation notes may also be mirrored in `task.md`.

---

## Active Plans

| Feature | Plan File |
|---------|-----------|
| 7 Persona Swarm | `task.md` |
| CloudManagerSystem (AWS) | `JARVIS-Brain/02-Projects/cloud-manager-system.md` |
| Mark-XXXXX Browser Upgrade | `task.md` |
| Sabrican + OpenClaw Codex | `task.md` |

---

## Persona Handoff Canon (2026-04-14)

Jarvis acts as operator. When user addresses a specialist:
1. Jarvis confirms the handoff.
2. Persona takes over with its own role and domain tone.

Triggers: `Buse ile konus`, `Mert'i cagir`, `Luna'ya gec`, `Jarvis`.

Each persona redirects out-of-domain requests to the correct expert. Luna hard-rejects unauthorized attack requests.
