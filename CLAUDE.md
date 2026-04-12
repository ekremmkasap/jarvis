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
- Durum: BATCH 1 VALIDATED
- Tamamlanan: refreshed `OPS/300_AGENTS_AUDIT.md`, `OPS/301_AGENTS_IMPLEMENTATION_PLAN.md`, `OPS/302_AGENTS_ROLLOUT_PLAN.md`; canonical base package and Batch 1 foundation confirmed in repo: `planner`, `repo_analyst`, `developer`, `tests/test_canonical_batch1.py`; validation passed with `pytest tests/test_canonical_batch1.py` (`7 passed`)
- Kalan: `reviewer`, `debug`, `release`, `docs`, `voice_narrator`, `mission_control`, bridge `/agent` endpoint, Telegram keyword routing, `hey_jarvis.py` voice hook, final smoke + handoff
- Sonraki Adim: Batch 2 ajanlari (`reviewer`, `debug`) ve `tests/test_canonical_batch2.py`

### Multi-Codex Control Plane (Tab-2 Codex Sprint)
- Status: In Progress
- Completed:
  - OPS audit and rollout artifacts (`OPS/200-204`)
  - Slice 1 complete: `server/account_manager.py` hardened as the single slot read surface
  - Added slot APIs: `get_slot`, `list_slots`, `get_active_slot`, `set_slot_status`, `get_quota_estimate`, `is_slot_available`
  - Added recursive redaction for auth/token-like keys before operator reads
  - Expanded `tests/test_account_manager.py`
  - Slice 2 complete: `server/codex_task_router.py` now exposes role-affinity routing, fallback chains, `CodexTaskRouter`, and `SlotExhaustedError`
  - Added `tests/test_codex_task_router.py`
- Remaining:
  - Slice 3 persistent canonical job queue
  - Slice 4 quota-aware dispatch + cooldown + failover
  - Slice 5-8 bridge/API/UI/worktree/Telegram integration
  - Slice 9 handoff and final validation
- Next Step:
  - Replace legacy job payload storage with canonical JSONL queue semantics in `server/codex_job_manager.py`
<!-- MANUAL ADDITIONS END -->
