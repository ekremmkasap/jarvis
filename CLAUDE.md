# jarvis-mission-control Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-12

## Active Technologies

- Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui) + boto3 (AWS SDK), python-dotenv (hâlihazırda mevcut), requests (mevcut) (001-cloudmanagersystem-jarvis-entegreli)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui): Follow standard conventions

## Recent Changes

- 001-cloudmanagersystem-jarvis-entegreli: Added Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui) + boto3 (AWS SDK), python-dotenv (hâlihazırda mevcut), requests (mevcut)

<!-- MANUAL ADDITIONS START -->
### AGENTS.md 9-Agent Canonical (Tab-3 Codex Sprint)
- Durum: PLANLAMA TAMAMLANDI
- Tamamlanan: `OPS/300_AGENTS_AUDIT.md`, `OPS/301_AGENTS_IMPLEMENTATION_PLAN.md`, `OPS/302_AGENTS_ROLLOUT_PLAN.md`
- Kalan: canonical base package, 9 agent implementation, bridge `/agent` endpoint, Telegram keyword routing, `hey_jarvis.py` voice hook, pytest + smoke validation, handoff
- Sonraki Adim: `server/agents/canonical/` base package + Batch 1 ajanlari ve `tests/test_canonical_batch1.py`

### Multi-Codex Control Plane (Tab-2 Codex Sprint)
- Status: In Progress
- Completed:
  - OPS audit and rollout artifacts (`OPS/200-204`)
  - Slice 1 complete: `server/account_manager.py` hardened as the single slot read surface
  - Added slot APIs: `get_slot`, `list_slots`, `get_active_slot`, `set_slot_status`, `get_quota_estimate`, `is_slot_available`
  - Added recursive redaction for auth/token-like keys before operator reads
  - Expanded `tests/test_account_manager.py`
- Remaining:
  - Slice 2 role-affinity routing
  - Slice 3 persistent canonical job queue
  - Slice 4 quota-aware dispatch + cooldown + failover
  - Slice 5-8 bridge/API/UI/worktree/Telegram integration
  - Slice 9 handoff and final validation
- Next Step:
  - Implement role-affinity routing in `server/codex_task_router.py` and add `tests/test_codex_task_router.py`
<!-- MANUAL ADDITIONS END -->
