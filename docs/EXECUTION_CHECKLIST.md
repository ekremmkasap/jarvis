# Jarvis Execution Checklist

**Status:** Active baseline
**Date:** 2026-04-10
**Purpose:** Convert agreed architecture decisions into a phase-based, file-based execution plan.

---

## Locked Decisions

1. Root web route stays marketing-first. `/` continues to redirect to `/landing` until there is an explicit product decision to replace it.
2. Live operational UI belongs under `/ops`; control, customer, and operator actions belong under `/admin`.
3. Primary hologram runtime is `apps/desktop-hologram`, launched by `master_launcher.py`. Any future Python/server-side hologram UI is fallback or diagnostic only.
4. Codex account ownership stays split by responsibility:
   - execution truth: `state/codex-accounts/`
   - metadata and status truth: `config/account_registry.json`
5. Do not introduce a third account config or registry file.
6. Delivery moves in phase-based commits, not micro-commits.

---

## Phase 1 - Surface Ownership Lock

**Goal:** Freeze route, launcher, and account ownership before feature expansion.

**Primary files**
- `apps/web-ui/src/app/page.tsx`
- `apps/web-ui/src/app/landing/page.tsx`
- `apps/web-ui/src/app/ops/page.tsx`
- `apps/web-ui/src/app/admin/page.tsx`
- `master_launcher.py`
- `server/SOURCE_OF_TRUTH.md`
- `docs/CODEX_ACCOUNTS.md`

**Checklist**
- [ ] Keep `/` as redirect-only entrypoint.
- [ ] Treat `/landing` as marketing or public narrative surface.
- [ ] Put live telemetry, queues, health, and runtime widgets under `/ops`.
- [ ] Put operator controls, customer state, account status, and admin actions under `/admin`.
- [ ] Treat `apps/desktop-hologram` as the only primary hologram runtime.
- [ ] Mark any new `server/ui/*hologram*` implementation as non-primary fallback or diagnostic.
- [ ] Keep Codex execution data in `state/codex-accounts/`.
- [ ] Keep Codex status metadata in `config/account_registry.json`.
- [ ] Reject any proposal that adds another registry such as `config/account_registry_v2.json` or `state/codex_registry.json`.

**Validation**
- [ ] `apps/web-ui/src/app/page.tsx` still contains only the root redirect behavior.
- [ ] `master_launcher.py` still starts the hologram from `apps/desktop-hologram`.
- [ ] `server/account_manager.py` still loads Codex account execution state from `state/codex-accounts/`.
- [ ] `server/skills/account_monitor.py` still owns `config/account_registry.json`.

**Suggested commit**
- `docs: lock route, hologram, and account source-of-truth rules`

---

## Phase 2 - Router And Model Health

**Goal:** Make routing and model health observable from one contract.

**Primary files**
- `server/model_router.py`
- `config/model_router.yml`
- `server/orchestrator_gateway.py`
- `apps/web-ui/src/app/api/admin/health/route.ts`
- `apps/web-ui/src/lib/adminData.ts`

**Checklist**
- [ ] Define one health payload for router status, fallback state, and degraded mode.
- [ ] Remove duplicate or conflicting health interpretation logic across bridge, gateway, and UI adapters.
- [ ] Surface active model, fallback chain, and failure reason in a UI-safe shape.
- [ ] Keep `/ops` and `/admin` reading the same health truth, not parallel reconstructions.

**Validation**
- [ ] Admin health route reports router state without inventing separate status semantics.
- [ ] `/ops` and `/admin` show the same degraded or healthy state for the same backend condition.

**Suggested commit**
- `router: unify model health and fallback reporting`

---

## Phase 3 - Vision And PC Control

**Goal:** Stabilize device perception and desktop control without leaking ownership into unrelated layers.

**Primary files**
- `server/agents/vision_analyzer.py`
- `server/skills/computer_control_skill.py`
- `server/skills/computer_agent_skill.py`
- `tests/test_vision_analyzer.py`

**Checklist**
- [ ] Keep screenshot and perception logic inside vision or computer-control lanes.
- [ ] Keep action execution behind explicit tool boundaries.
- [ ] Do not route desktop-control state through landing, admin, or marketing pages.
- [ ] Emit operator-safe status that can later be shown in `/ops`.

**Validation**
- [ ] Vision tests still pass.
- [ ] No desktop-control side effects are wired directly into public web routes.

**Suggested commit**
- `vision: stabilize perception and pc control lane`

---

## Phase 4 - Voice Runtime And Hologram Integration

**Goal:** Keep voice and hologram in one runtime story instead of creating parallel UIs.

**Primary files**
- `hey_jarvis.py`
- `services/voice/voice_service.py`
- `server/voice_jarvis.py`
- `server/voice_integration.py`
- `apps/desktop-hologram/main.js`
- `apps/desktop-hologram/preload.js`
- `apps/desktop-hologram/renderer.js`

**Checklist**
- [ ] Treat `hey_jarvis.py` plus voice service as the runtime source for wake, listen, and reply state.
- [ ] Feed voice or status updates into the Electron hologram instead of building a second primary client.
- [ ] Keep Electron assets and renderer changes inside `apps/desktop-hologram`.
- [ ] If a diagnostic hologram view is added elsewhere, document it as fallback-only.

**Validation**
- [ ] `master_launcher.py` startup order remains bridge -> gateway -> voice -> hologram.
- [ ] Hologram package still boots with `electron .`.

**Suggested commit**
- `voice: wire runtime state into primary desktop hologram`

---

## Phase 5 - Task Bus, Swarm, And Codex Load Balancing

**Goal:** Route work across Codex accounts and swarm lanes without creating config drift.

**Primary files**
- `server/skills/task_bus_hooks.py`
- `server/skills/swarm_topology.py`
- `server/skills/swarm_skill.py`
- `server/codex_task_router.py`
- `server/codex_orchestrator.py`
- `server/account_manager.py`
- `server/skills/account_monitor.py`
- `state/codex-accounts/`
- `config/account_registry.json`

**Checklist**
- [ ] Select executable Codex accounts from `state/codex-accounts/`.
- [ ] Read account labels, quotas, notes, and operator status from `config/account_registry.json`.
- [ ] Keep execution routing and operator metadata separate in code and docs.
- [ ] If quota or failure data must flow back into the registry, write it through the account monitor path only.
- [ ] Do not add a third sync file, shadow cache, or alternate registry schema.

**Validation**
- [ ] Swarm or task-router code references the existing two ownership layers only.
- [ ] Account-facing UI can render metadata without depending on execution snapshots.

**Suggested commit**
- `swarm: add codex load-balancing on existing dual-source account model`

---

## Phase 6 - Bridge, Telegram, And WebSocket

**Goal:** Keep the live runtime centered on the canonical bridge and shared event flow.

**Primary files**
- `server/bridge.py`
- `server/telegram/telegram_intelligence.py`
- `server/telegram_webhook.py`
- `services/orchestrator/main.py`
- `services/orchestrator/task_queue.py`
- `apps/web-ui/src/components/MissionControlDashboard.tsx`

**Checklist**
- [ ] Treat `server/bridge.py` as the canonical operator-facing backend runtime.
- [ ] Keep WebSocket event naming aligned between backend and dashboard.
- [ ] Reuse bridge and orchestrator health data in Telegram notifications instead of inventing separate state stores.
- [ ] Avoid reviving legacy bridge clones as alternate runtime owners.

**Validation**
- [ ] Dashboard event stream matches backend event names.
- [ ] Telegram and UI describe the same task status for the same task.

**Suggested commit**
- `bridge: unify websocket and telegram runtime signaling`

---

## Phase 7 - Web UI Delivery

**Goal:** Expand the operator UI without changing the public landing contract.

**Primary files**
- `apps/web-ui/src/app/landing/page.tsx`
- `apps/web-ui/src/app/ops/page.tsx`
- `apps/web-ui/src/app/admin/page.tsx`
- `apps/web-ui/src/app/codex-accounts/page.tsx`
- `apps/web-ui/src/components/MissionControlDashboard.tsx`
- `apps/web-ui/src/components/AdminQuickActions.tsx`
- `apps/web-ui/src/lib/adminData.ts`

**Checklist**
- [ ] Keep landing isolated from live operator widgets.
- [ ] Put live task, queue, health, and telemetry widgets under `/ops`.
- [ ] Put account, customer, onboarding, and mutation-capable controls under `/admin`.
- [ ] If `codex-accounts` becomes user-visible, link it from `/admin` or `/ops`, not from `/`.
- [ ] Document any route contract changes before merging.

**Validation**
- [ ] `/landing`, `/ops`, and `/admin` each have a single clear purpose.
- [ ] Root redirect behavior remains unchanged unless there is an explicit product change request.

**Suggested commit**
- `web-ui: ship ops and admin surfaces without changing root landing behavior`

---

## Phase 8 - Docs, Tests, And Final Polish

**Goal:** Close the loop with evidence, not narrative.

**Primary files**
- `README.md`
- `AGENTS.md`
- `docs/ARCHITECTURE.md`
- `docs/CODEX_ACCOUNTS.md`
- `server/SOURCE_OF_TRUTH.md`
- `tests/`

**Checklist**
- [ ] Update docs only after runtime ownership is stable in code.
- [ ] Add or adjust tests around router health, dashboard contracts, task state, and account boundaries.
- [ ] Verify docs do not claim a second hologram runtime or a third account registry.
- [ ] Keep final polish inside the phase that owns the underlying runtime changes.

**Validation**
- [ ] Docs match current code paths and launchers.
- [ ] Tests cover the contracts changed in earlier phases.
- [ ] No split-brain source-of-truth remains in docs.

**Suggested commit**
- `docs: align architecture docs and tests with final runtime contracts`

---

## Commit Strategy

Target 6-8 commits total. Preferred sequence:

1. `docs: lock route, hologram, and account source-of-truth rules`
2. `router: unify model health and fallback reporting`
3. `vision: stabilize perception and pc control lane`
4. `voice: wire runtime state into primary desktop hologram`
5. `swarm: add codex load-balancing on existing dual-source account model`
6. `bridge: unify websocket and telegram runtime signaling`
7. `web-ui: ship ops and admin surfaces without changing root landing behavior`
8. `docs: align architecture docs and tests with final runtime contracts`

## Hard Stops

- Do not move the live dashboard onto `/` as a side effect of UI work.
- Do not create a second primary hologram runtime.
- Do not create a third Codex account registry.
- Do not mix public landing concerns with operator runtime state.
- Do not ship phase slices that leave route ownership ambiguous.
