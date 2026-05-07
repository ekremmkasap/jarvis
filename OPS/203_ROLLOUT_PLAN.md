# 203 Rollout Plan - Multi-Codex Control Plane

Date: 2026-04-13

## Phase 1 - Foundation Hardening

Goal:

- Make `account_manager` the only supported slot read path
- Add redaction and slot-level helpers
- Preserve existing two-truth ownership

Deliverables:

- slot merge API
- slot availability contract
- metadata quota estimate helper
- tests for slot merge and redaction

## Phase 2 - Scheduler + Queue + Role Affinity

Goal:

- Introduce a canonical queue and role-first dispatch selection

Deliverables:

- `codex_task_router` role affinity table
- `codex_job_manager` JSONL queue contract
- `codex_orchestrator` queue-first dispatch logic
- dispatcher retry / requeue behavior

## Phase 3 - Worktree Isolation + Failover + Cooldown

Goal:

- Make slot execution isolated and restart-safe

Deliverables:

- `codex_workspace.ensure_worktree()`
- per-slot git worktree ownership
- control-plane cooldown persistence
- mid-job failover handling
- dispatch audit log

## Phase 4 - Operator UI + Observability

Goal:

- Turn `/codex-accounts` into a live operator console

Deliverables:

- additive `/api/codex/*` bridge endpoints
- health/audit/queue/slots/contracts
- live queue + health + controls panels
- Telegram control-plane commands
- handoff documentation

## Slice Execution Order

1. Slice 1 - `account_manager`
2. Slice 2 - `codex_task_router`
3. Slice 3 - `codex_job_manager`
4. Slice 4 - `codex_orchestrator`
5. Slice 5 - `bridge.py` operator endpoints
6. Slice 6 - `/codex-accounts` UI
7. Slice 7 - `codex_workspace`
8. Slice 8 - Telegram `/codex-*`
9. Slice 9 - validation, handoff, final integration

## Validation Rule

After every slice:

- run the relevant pytest subset
- fix failures before moving forward
- update `CLAUDE.md`
- commit the feature slice
- commit the `CLAUDE.md` progress update separately
