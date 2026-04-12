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
  - Slot/operator metadata matching now tolerates blank `execution_slot` by using slot-role heuristics
  - Added stricter recursive redaction for auth/token/secret-like keys before operator reads
  - Expanded `tests/test_account_manager.py` to cover heuristic matching and nested redaction
- Remaining:
  - Slice 2 role-affinity router alignment to canonical slot roles
  - Slice 3 persistent canonical job queue validation and contract cleanup
  - Slice 4 quota-aware dispatch + cooldown + failover
  - Slice 5-8 bridge/API/UI/worktree/Telegram integration
  - Slice 9 handoff and final validation
- Next Step:
  - Align `server/codex_task_router.py` with canonical slot roles (`spark=voice`, `nexus=overflow`) and validate fallback routing

### CloudManagerSystem + Skill Registry (Tab-3 Codex)
- Durum: IN PROGRESS
- Completed:
  - Slice A1 complete: `server/skills/aws_common.py` and `server/skills/aws_ec2_skill.py`
  - Added `tests/test_aws_ec2_skill.py`
  - Validation passed with `pytest tests/test_aws_ec2_skill.py` (`4 passed`)
- Remaining:
  - Slice A2-A6 (`aws_s3_skill`, `aws_cost_skill`, bridge `/cloud-*`, `/api/cloud/*`, `/cloud` UI, Part A integration)
  - Slice B1-B5 (`server/skill_registry.py`, cloud registry entries, `/yardim`, incremental command migration, Part B integration)
  - Final handoff doc: `OPS/408_CLOUDMANAGER_HANDOFF.md`
- Next Step:
  - Slice A2: implement `server/skills/aws_s3_skill.py` and `tests/test_aws_s3_skill.py`
<!-- MANUAL ADDITIONS END -->
