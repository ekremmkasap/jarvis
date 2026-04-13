# 202 Gap Analysis - Multi-Codex Control Plane

Date: 2026-04-13

## Scheduler

Current:

- Immediate slot selection in `codex_orchestrator.dispatch_job()`
- Keyword routing only
- No queue-first dispatch contract

Gap:

- Missing role affinity scheduler
- Missing delayed requeue behavior
- Missing structured fallback chain

## Queue

Current:

- Legacy JSON payload in `state/codex-accounts/job_queue.json`
- Recent-job helpers exist

Gap:

- Missing canonical queue schema
- Missing JSONL persistence
- Missing dequeue and retry primitives
- Missing explicit cancel/purge/stuck detection primitives

## Routing

Current:

- `codex_task_router.route_keywords()` is keyword-to-slot

Gap:

- Missing role-based routing
- Missing account availability filtering
- Missing standard `route_task(task: dict)`

## Quota

Current:

- `codex_quota_tracker` tracks usage and exhaustion

Gap:

- Missing dispatcher-facing `has_quota()` contract
- Missing quota estimate alignment with operator metadata view
- Missing quota-aware UI health summaries

## Failover

Current:

- Best-effort slot fallback before start

Gap:

- No mid-job failover policy
- No failure reason journal in canonical job schema
- No control-plane cooldown persistence

## Worktree

Current:

- `codex_workspace` only reports paths and shell strings

Gap:

- No worktree creation/verification
- No branch convention enforcement
- No orchestrator integration

## Operator UI

Current:

- Status dashboard with codex runtime slots and recent jobs

Gap:

- No dispatch form
- No queue view
- No per-slot control actions
- No dispatch audit feed
- No exact per-slot health panel

## Observability

Current:

- `codex_health` watcher exists
- bridge status payload exists

Gap:

- No dispatch audit log endpoint
- No per-slot health score endpoint
- No queue-focused operator metrics

## Security

Current:

- Some surfaces already avoid token leakage

Gap:

- No shared recursive redaction helper at the slot/control-plane layer
- Execution truth snapshots contain live token material and remain easy to misuse if read directly

## Handoff / Resume

Current:

- No control-plane handoff doc for this sprint

Gap:

- Need `OPS/208_HANDOFF.md`
- Need `CLAUDE.md` sprint progress section updated after every slice

## Priority Order

1. Harden single slot source-of-truth API
2. Add role-aware routing and queue schema
3. Add quota/cooldown/failover-aware dispatch
4. Expose redacted operator endpoints
5. Wire live UI controls
6. Add worktree isolation
7. Add Telegram operator commands
8. Finalize handoff and smoke tests
