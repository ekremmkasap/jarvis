# OPS/67_OPENCLAW_TELEGRAM_MODEL_STATE_V5

Tarih: 2026-04-04

## Current Narrow Truth
- `openclaw.cmd` and `openclaw.ps1` are installed on this machine and the CLI responds to read-only help/status commands.
- `openclaw.cmd status --all` shows the OpenClaw gateway target as `ws://127.0.0.1:18789`.
- Current OpenClaw gateway state is `unreachable` with `connect ECONNREFUSED 127.0.0.1:18789`.
- `openclaw.cmd gateway status` reports the Scheduled Task service as `missing` / `unknown`, with service config flagged as out of date or non-standard.
- Current OpenClaw state shows exactly one agent store: `main`.
- Current OpenClaw status does not show an active `dev` profile.
- Current OpenClaw status shows `Channels` as empty.
- Current OpenClaw status shows `Secrets` as `none`.
- Current OpenClaw status shows three stored sessions, including older Telegram-related session keys, but that is state evidence only, not current delivery proof.

## Repo vs Local State Split
- Repo-local `.openclaw` state is absent in the current worktree.
- Older OPS artifacts that referenced `.openclaw\\agents\\main\\agent\\auth-profiles.json` are not current repo-local proof.
- Current OpenClaw proof comes from the machine-level CLI state under `~\\.openclaw`, not from repo-local files.
- A direct `openclaw.cmd channels list` read hit `EPERM` on `C:\\Users\\sergen\\.openclaw\\agents\\main\\agent\\auth-profiles.json`, so machine-level auth/channel detail is only partially visible from the current sandbox.

## Telegram Surface Split
- Canonical bridge runtime uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` via `server/runtime_config.py`.
- `server/openclaw_bridge.py` uses `JARVIS_ALLOWED_CHAT_IDS` and optional `OPENCLAW_PROFILE`.
- `server/autonomous_loop.py` also uses `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- This means the repo currently has two Telegram/config surfaces:
  - bridge/autonomous direct token/chat-id surface
  - OpenClaw helper surface keyed off `JARVIS_ALLOWED_CHAT_IDS`

## What Is Actually Proven
- Bridge runtime can be configured with Telegram credentials from repo root `.env`.
- OpenClaw CLI exists locally and `main` is the only currently visible local profile/state.
- OpenClaw gateway is currently down.
- OpenClaw channel delivery is not currently proven because the gateway is unreachable and channel table is empty.
- OpenClaw machine-level service health is degraded enough that `health`, `gateway probe`, and `channels list` do not yield a green operator path.

## What Is Not Proven
- direct Telegram send through bridge in this sprint
- agent-generated Telegram delivery through OpenClaw in this sprint
- pairing completion for the currently intended Telegram channel
- allowlist completion inside the currently intended OpenClaw delivery path
- `dev` profile viability
- `OPENCLAW_PROFILE` override being used in the current operator workflow
- exact channel auth entries inside `~\\.openclaw` while sandboxed

## Operator Guidance
- Treat `main` as the only locally evidenced OpenClaw profile right now.
- Treat `dev` as unproven, not canonical.
- Do not declare OpenClaw Telegram delivery healthy while `openclaw.cmd health` fails and `status --all` shows no enabled channels.
- Treat current OpenClaw gateway/service state as a blocker before any agent-deliver claim.
- If the goal is reliable Telegram right now, the bridge runtime path and the OpenClaw delivery path must be treated as separate systems.
- Next live proof should answer one question at a time:
  1. can bridge direct Telegram delivery send successfully
  2. can OpenClaw gateway come up cleanly
  3. once gateway is up, does channel state show Telegram enabled
  4. only then test OpenClaw agent delivery

## Most Important Contradictions
- Historical `main/dev profile split` language is stronger than current local proof.
- OpenClaw session history exists, but current gateway health is red.
- Repo `.env` having Telegram credentials does not prove OpenClaw channel delivery.
- `server/openclaw_bridge.py` and `server/bridge.py` do not consume the same Telegram targeting variable.
