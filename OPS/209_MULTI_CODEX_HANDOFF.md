# Multi-Codex Control Plane Handoff

Date: 2026-04-13
Scope: Tab-2 Slice 9 final handoff
Status: Complete

## 5-Slot Architecture Summary

The control plane is built around five canonical Codex slots. `server/account_manager.py`
is the single read surface for slot/account truth, `server/codex_job_manager.py`
owns the persistent queue contract, `server/codex_orchestrator.py` owns dispatch
plus cooldown/failover, and `server/bridge.py` exposes the operator APIs and
Telegram command surface.

| Slot | Primary role | Routing intent | Fallback notes |
| --- | --- | --- | --- |
| `atlas` | Manager / core | planning, architecture, coordination | default fallback for uncategorized work |
| `forge` | Backend ops | bridge, server, API, Telegram, skill implementation | first backend affinity target |
| `nexus` | Overflow / reserve | overflow, backup, failover execution | shared fallback when a primary slot is unavailable |
| `shield` | Security / audit | security review, secret handling, policy, audit | first security affinity target |
| `spark` | Voice + hologram / frontend | voice, video, hologram, dashboard, landing | first voice/video affinity target |

## Telegram Commands

| Command | Purpose | Handler |
| --- | --- | --- |
| `/codex [slot|auto] [gorev]` | dispatch a Codex job | `_handle_codex_command()` |
| `/codex-swarm [gorev]` | multi-slot dispatch | `_handle_codex_command(..., swarm=True)` |
| `/codex-durum` | slot summary | `_handle_codex_slots_command()` |
| `/codex-kuyruk` | queued job summary | `_handle_codex_queue_command()` |
| `/codex-saglik` | health summary | `_handle_codex_health_command()` |
| `/codex-baslat [role] [gorev]` | operator dispatch with explicit role | `_handle_codex_start_command()` |
| `/codex-durdur` | cancel all active Codex jobs | `_handle_codex_stop_command()` |
| `/codex-cooldown-temizle` | clear all cooldown records | `_handle_codex_clear_cooldowns_command()` |
| `/codex-status` | legacy runtime summary alias | `COMMAND_REGISTRY -> codex_status_handler` |
| `/codex-sonuc [job_id]` | fetch single job result summary | `_handle_codex_result_command()` |

## `/api/codex/*` Endpoints

| Method | Endpoint | Purpose | Notes |
| --- | --- | --- | --- |
| `GET` | `/api/codex/slots` | slot/operator summary | redacted through `account_manager` |
| `GET` | `/api/codex/jobs` | filtered job list | supports queue/runtime views |
| `GET` | `/api/codex/queue` | pending queue snapshot | operator-friendly queue contract |
| `GET` | `/api/codex/health` | slot health and stuck jobs | cooldown-aware |
| `GET` | `/api/codex/audit` | dispatch audit tail | reads JSONL dispatch log |
| `GET` | `/api/codex/result?job_id=...` | single job result | returns summary/result payload |
| `GET` | `/api/codex/status` | legacy combined status payload | queue + runtime slot summary |
| `POST` | `/api/codex/dispatch` | enqueue and dispatch a job | body: `task_description`, optional `role`, optional `priority` |
| `POST` | `/api/codex/control` | operator control actions | actions: `drain`, `pause`, `disable`, `retry`, `cancel`, `clear_cooldowns`, `stop_all` |

## How To Add A New Skill

1. Put the behavior in a focused handler, usually in `server/bridge.py` or a dedicated module under `server/skills/`.
2. Register the Telegram or bridge command with `SkillEntry` in the right registry file under [`server/skills/registry_entries`](C:\Users\sergen\Desktop\jarvis-mission-control\server\skills\registry_entries).
3. Wire that registry into `COMMAND_REGISTRY` in [`server/bridge.py`](C:\Users\sergen\Desktop\jarvis-mission-control\server\bridge.py) if it belongs on the shared command surface.
4. If the command needs special parsing or operator-only side effects, add a narrow explicit branch in `_handle_command_with_sprint_extensions()`.
5. Add or extend pytest coverage for routing, payload shape, and failure cases before exposing it to Telegram or the operator UI.

## Validation

- `python -m pytest tests/test_account_manager.py tests/test_codex_task_router.py tests/test_codex_job_manager.py tests/test_codex_orchestrator.py tests/test_codex_management.py tests/test_codex_workspace.py -v --tb=short`
- Result: `47 passed`
