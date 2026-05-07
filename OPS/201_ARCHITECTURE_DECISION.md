# 201 Architecture Decision - Multi-Codex Control Plane

Date: 2026-04-13

## Decision Summary

The control plane will be implemented on top of the existing two-truth model:

- Execution truth: `state/codex-accounts/`
- Metadata truth: `config/account_registry.json`

No third registry, shadow config, or replacement store will be introduced.

## Ownership Model

### Slot read owner

`server/account_manager.py`

Reason:

- It already merges runtime and metadata layers
- It is the correct place to centralize slot redaction and slot availability logic
- Every caller should depend on merged slot reads instead of ad hoc file access

### Queue owner

`server/codex_job_manager.py`

Reason:

- Scheduler and UI both need one canonical job representation
- Queue persistence must outlive bridge/orchestrator process restarts
- Existing legacy job payload can be preserved through compatibility helpers if needed

### Scheduling / dispatch owner

`server/codex_orchestrator.py`

Reason:

- It already owns Codex CLI process launch, slot selection, and result updates
- It is the right place to add quota checks, cooldown checks, failover, and dispatch audit logs

### Operator API owner

`server/bridge.py`

Reason:

- It is the canonical backend runtime from `AGENTS.md` and `SOURCE_OF_TRUTH.md`
- Existing operator surfaces already route through bridge

### Operator UI owner

`apps/web-ui/src/app/codex-accounts/page.tsx`

Reason:

- Existing `/codex-accounts` page is already the operator-facing Codex surface
- It should evolve from passive status into live control plane

## Scheduler Design

Adopt a queue-first model:

1. `bridge.py` receives dispatch requests
2. Request is normalized into canonical job schema
3. `codex_job_manager.enqueue()` persists the job
4. `codex_orchestrator.dispatch(job_id)` assigns a slot using:
   - role affinity
   - slot availability
   - cooldown state
   - quota state
5. On success:
   - job status becomes `running`
   - slot assignment is recorded
   - worktree is ensured
   - Codex subprocess starts
6. On no available slot:
   - job remains queued/pending
   - retry window and reason are stored

## Queue Persistence Decision

Primary queue persistence:

- `state/codex_jobs.jsonl`

Reason:

- append-friendly
- restart-safe
- easy to audit
- supports log-style storage without full-file rewrites per update

Compatibility:

- existing `state/codex-accounts/job_queue.json` may remain as compatibility output or be derived/mirrored if older tests still reference it

## Failover Policy

Failover rules:

- Role affinity chooses preferred slots
- If preferred slot is unavailable, walk the fallback chain
- `nexus` is the overflow slot for most roles
- If active slot fails mid-job, job records:
  - previous slot
  - failure reason
  - retry count increment
  - new selected slot if failover succeeds
- If no failover target is available:
  - job returns to queued/pending with cooldown delay

## Cooldown Strategy

Dedicated control-plane cooldown persistence:

- `state/codex_cooldowns.json`

Reason:

- Quota cooldown and operational cooldown are related but not identical
- Operational cooldown must support pause/drain/failure recovery independently of quota resets

## Worktree Isolation Strategy

Per-slot worktrees under repo root:

- `worktrees/atlas`
- `worktrees/forge`
- `worktrees/nexus`
- `worktrees/shield`
- `worktrees/spark`

Branch convention:

- `codex/atlas`
- `codex/forge`
- `codex/nexus`
- `codex/shield`
- `codex/spark`

Runtime contract:

- `ensure_worktree(slot_id)` is called before execution
- subprocess environment sets:
  - `CODEX_HOME`
  - `GIT_WORK_TREE`

## Security Decision

All slot/job/operator API responses must flow through redaction before serialization.

Sensitive keys to strip recursively:

- `auth_token`
- `password`
- `secret`
- `access_token`
- `refresh_token`
- `id_token`
- `OPENAI_API_KEY`
- bearer-like headers or auth blobs

## Observability Decision

Dispatch decisions will be appended to:

- `server/logs/codex_dispatch_audit.jsonl`

Required fields:

- `ts`
- `job_id`
- `role`
- `affinity_chain`
- `selected_slot`
- `reason`
- `quota_before`
- `cooldown_state`

## Backward Compatibility

Preserve:

- existing `/api/codex/status`
- existing `/api/codex/result`
- existing `/codex`, `/codex-swarm`, `/codex-durum`, `/codex-sonuc`, `/codex-workspace`

Add:

- new `/api/codex/*` endpoints only as additive changes
- new Telegram commands only as additive changes
