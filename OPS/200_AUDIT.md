# 200 Audit - Multi-Codex Control Plane

Date: 2026-04-13
Repo: `C:\Users\sergen\Desktop\jarvis-mission-control`

## Scope Read

- `state/codex-accounts/`
- `config/account_registry.json`
- `server/account_manager.py`
- `server/codex_orchestrator.py`
- `server/codex_task_router.py`
- `server/codex_job_manager.py`
- `server/codex_quota_tracker.py`
- `server/codex_health.py`
- `server/codex_workspace.py`
- `server/bridge.py`
- `apps/web-ui/src/app/codex-accounts/page.tsx`
- `tools/codex_accounts.py`
- `codex-accounts.ps1`
- `docs/CODEX_ACCOUNTS.md`
- `server/SOURCE_OF_TRUTH.md`

## Slot Inventory

Execution truth under `state/codex-accounts/` currently includes the five required slots:

- `atlas`
- `forge`
- `nexus`
- `shield`
- `spark`

Observed runtime artifacts:

- Per-slot auth snapshots exist as `state/codex-accounts/{slot}.json`
- `state/codex-accounts/registry.json` maps slot -> `account_id`, `saved_at`, optional metadata
- `atlas/` and `nexus/` contain populated Codex home-style runtime trees (`.codex/`, `sessions/`, `skills/`, sqlite files)
- `forge/`, `shield/`, `spark/` currently appear lighter and are not normalized as worktrees
- Per-slot JSON snapshots contain raw token material and must never be returned directly by APIs or logs

## Slot Snapshot Schema

Observed top-level snapshot structure in slot files:

- `auth_mode`
- `OPENAI_API_KEY`
- `tokens`
- `last_refresh`

Observed nested sensitive token keys:

- `id_token`
- `access_token`
- `refresh_token`
- `account_id`

Conclusion:

- Direct reads from `state/codex-accounts/{slot}.json` are safe only for backend execution code
- Operator/API surfaces must go through a redaction layer

## Registry Field Map

`config/account_registry.json` currently stores operator-facing metadata in `accounts[]` records with fields such as:

- `id`
- `label`
- `provider`
- `role`
- `status`
- `execution_slot`
- `runtime_account_id`
- `daily_limit`
- `weekly_limit`
- `remaining_estimate`
- `last_seen`
- `notes`

## Consistency Check

### Execution truth parity

- `state/codex-accounts/registry.json` contains all 5 runtime slots
- Execution slot naming is correct and matches the required set

### Metadata truth parity

- `config/account_registry.json` does not currently provide a clean 1:1 slot metadata row for all five runtime slots
- Several records are generic agent/operator records with empty `execution_slot`
- One local record (`slot_forge`) exists but does not represent the full 5-slot plane

### Result

- Slot parity is incomplete across the execution and metadata layers
- The control plane must preserve the two existing truths but normalize them through `server/account_manager.py`
- No third registry is needed or allowed

## Real vs Stubbed Audit

### `server/account_manager.py`

Current state:

- Real merge logic already exists between runtime registry and operator metadata
- Tracks Codex slots as provider `codex`
- Supports active account selection, fallback ordering, and a unified `get_status()`

Gaps:

- No `get_slot()`, `list_slots()`, `get_active_slot()`, `set_slot_status()`, `get_quota_estimate()`, `is_slot_available()`, `_redact_sensitive()`
- Status logic is still account-centric instead of control-plane slot-centric

### `server/codex_orchestrator.py`

Current state:

- Real dispatch implementation exists
- Uses `account_manager.resolve_codex_accounts()`
- Uses `codex_quota_tracker`
- Spawns per-slot Codex CLI subprocesses with `CODEX_HOME`
- Persists legacy jobs through `codex_job_manager`

Gaps:

- No persistent priority queue semantics
- No cooldown persistence file
- No audit log for dispatch decisions
- No mid-job failover handling
- Uses immediate thread spawning instead of queue-first dispatch

### `server/codex_task_router.py`

Current state:

- Real keyword router exists
- Supports slot normalization and split-task fanout

Gaps:

- No role affinity table
- No fallback chain abstraction
- No availability check via `account_manager`
- No `SlotExhaustedError`

### `server/codex_job_manager.py`

Current state:

- Real JSON payload persistence exists at `state/codex-accounts/job_queue.json`
- Supports create/get/update/finalize/list result helpers

Gaps:

- Not append-friendly JSONL
- No explicit `enqueue/dequeue/retry/cancel/purge/find_stuck_jobs`
- Canonical job schema does not match the requested control-plane format

### `server/codex_quota_tracker.py`

Current state:

- Real per-slot quota storage and normalization exists
- Tracks `remaining_pct`, `cooldown_until`, `last_task_at`, usage counters

Gaps:

- No `has_quota(slot, estimated_tokens)` helper for dispatcher decisions
- Cooldown is quota-reset oriented, not scheduler-control-plane oriented

### `server/codex_health.py`

Current state:

- Real watcher exists
- Checks low quota, silent slot, stuck running jobs, exhausted fleet
- Sends sanitized Telegram notifications

Gaps:

- Not yet integrated with richer queue semantics or failover audit
- Health score contract for UI endpoints is missing

### `server/codex_workspace.py`

Current state:

- Real helper exists for status/init/clean command strings

Gaps:

- No `ensure_worktree()`
- No `list_worktrees()`
- No job cleanup path
- No branch/worktree isolation ownership

### `server/bridge.py`

Current state:

- Real Telegram commands: `/codex`, `/codex-swarm`, `/codex-durum`, `/codex-sonuc`, `/codex-workspace`
- Real API endpoints: `/api/codex/status`, `/api/codex/result`

Gaps:

- No `/api/codex/slots`
- No `/api/codex/jobs`
- No `/api/codex/queue`
- No `/api/codex/dispatch`
- No `/api/codex/control`
- No `/api/codex/health`
- No `/api/codex/audit`
- No Telegram command set for queue/health/control-plane operations

### `apps/web-ui/src/app/codex-accounts/page.tsx`

Current state:

- Real operator page exists
- Polls `/api/accounts`, `/api/dashboard-summary`, `/api/desktop-assistant`, `/api/codex/status`
- Shows codex runtime slots and recent jobs

Gaps:

- Still acts like a status dashboard, not a live control plane
- No dispatch form
- No queue panel tied to canonical queue
- No per-slot control actions
- No audit feed
- No exact typed contract for new control-plane APIs

## Summary

The repo already has the beginnings of a 5-slot Codex runtime:

- runtime selection
- quota tracking
- basic job persistence
- basic health watcher
- basic operator page

What it does not yet have is a coherent control plane:

- slot-first read API
- canonical job queue
- role affinity scheduler
- failover/cooldown audit
- operator control endpoints
- UI actions wired to real backend behavior
