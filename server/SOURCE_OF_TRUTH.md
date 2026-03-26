# Jarvis Source of Truth

Bu dokuman aktif standalone runtime'i ve legacy dosyalari ayirir.

## Canonical Runtime

- Backend gateway: `server/bridge.py`
- Agent runtime: `server/agent_os/runtime.py`
- Team orchestration: `server/core/team_orchestrator.py`
- Tenant config schema: `server/tenants/*/config.json`
- Operational notes: `server/ARCHITECTURE.md`, `server/DEVLOG.md`, `server/ROADMAP.md`

## Legacy / Reference Only

- `server/bridge_server.py`
- `src/runtime/dev/bridge.py`
- root `bridge_*.py`
- root `telegram_gateway_v2.py`
- Pinokio donor source: `C:\pinokio\api\ekrem\app`

## Rules

1. Production-facing runtime changes go to `server/bridge.py`.
2. Legacy files are not a second source of truth.
3. Donor sources may contribute prompts or patterns only; do not copy runtime state, logs, secrets, or launcher logic.
