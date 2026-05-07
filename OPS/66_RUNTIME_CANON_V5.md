# OPS/66_RUNTIME_CANON_V5

Tarih: 2026-04-04

## Canonical Runtime Story
- Canonical bridge runtime: `server/bridge.py`.
- Canonical web-only behavior: `server/bridge.py --web-only` via `server/runtime_config.py` CLI override.
- Canonical watchdog producer files: `server/data/bridge_heartbeat.json`, `server/data/bridge.lock`.
- Canonical queue health surface: `services/orchestrator/main.py` `/health` backed by `TaskQueue.snapshot()`.
- Controlled watchdog smoke now proves one live path: watchdog can observe bridge child death, clean old heartbeat/lock state, and respawn a new bridge process.

## Ownership Map
- `master_launcher.py` -> launcher narrative, still partial until wider runtime proof.
- `server/bridge.py` -> main runtime owner for dashboard/HTTP and optional Telegram.
- `server/runtime_config.py` -> runtime behavior switches, including `--web-only`.
- `server/watchdog.py` -> consumer of bridge heartbeat/lock state; forced-restart path is now live-proven and old-PID cleanup is exercised on restart.
- `services/orchestrator/task_queue.py` -> queue state, ordering, persistence, snapshot truth.
- `services/orchestrator/main.py` -> API exposure and health semantics.
- `openclaw.cmd` / `openclaw_web_only.cmd` -> delegating wrappers, not canonical runtime owners.
- `install_openclaw_startup.cmd` -> operator-sensitive autostart helper; treat conservatively.

## Known Canon Gaps
- OpenClaw main/dev profile selection remains unresolved.
- Telegram direct send and agent send remain unverified in this sprint.
- Watchdog full shutdown cleanup under external supervisor exit remains narrower than restart-path proof.
- Aggregate suite is currently green: `python -m unittest discover -s tests -p "test_*.py"` now reports `200 tests OK`.
- Test output is still noisy because deprecation warnings and pattern-analysis errors remain even though the suite is green.
