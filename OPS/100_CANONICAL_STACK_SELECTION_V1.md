# Canonical Stack Selection V1

Validated on 2026-04-10 from live runtime first, then code.

## Selected canonical stack

The canonical stack for a working voice assistant in this repo is:

1. `server/bridge.py` on `127.0.0.1:8081`
2. `hey_jarvis.py` as the voice client / speech loop
3. `ollama` on `127.0.0.1:11434` as the local model backend/fallback

This is stack family A: the legacy/main bridge stack.

## Why this is the correct choice

- `hey_jarvis.py` binds to `JARVIS_BACKEND_URL` and defaults to `http://127.0.0.1:8081` at `hey_jarvis.py:118`.
- `server/start_voice.bat` points voice to backend `8081` and launches `..\hey_jarvis.py` at `server/start_voice.bat:19-25`.
- `server/start_jarvis.bat` launches `bridge.py` directly at `server/start_jarvis.bat:22-26`.
- `master_launcher.py` explicitly declares itself the "Single entrypoint for the local voice stack" at `master_launcher.py:3-8`.
- `master_launcher.py` launches bridge first, then voice at `master_launcher.py:270-300`.
- `README.md` distinguishes the bridge from the FastAPI orchestrator and defines bridge as the standalone long-lived runtime at `README.md:3-8` and `README.md:33-39`.

## Why the other stacks are not canonical for voice-first bring-up

### FastAPI orchestrator stack

- `services/orchestrator/main.py` is a queued task API with `/task`, `/tasks`, `/agents`, `/voice`, and `/ws`; it is not the speech loop runtime.
- It owns port `8091` at `services/orchestrator/main.py:59-62` and `services/orchestrator/main.py:186-197`.
- Its job queue is persisted in `services/orchestrator/task_queue.py`, which is useful for task orchestration, not for the main speaking assistant loop.

Status: secondary

### Separate orchestrator UI stacks

- `server/orchestrator/ui/README.md` describes a separate web UI and a separate standalone agentic team UI at `server/orchestrator/ui/README.md:14-34`.
- `server/orchestrator/ui/app.py` is a Flask/SocketIO UI backend with `/health`, `/ready`, `/api/agents`, etc. at `server/orchestrator/ui/app.py:486-612`.
- `server/orchestrator/ui/agentic_app.py` is a separate agentic-team UI/backend at `server/orchestrator/ui/agentic_app.py:304-337`.

Status: secondary / operator UI, not primary voice runtime

### OpenClaw

- `server/openclaw_bridge.py` explicitly says it is "not the canonical runtime" and only provides optional helper calls when OpenClaw is available locally at `server/openclaw_bridge.py:3-6`.
- `server/skills/openclaw_skill.py` is a wrapper skill layer for Ollama/Claude/OpenClaw style commands, not the resident Jarvis assistant ownership path at `server/skills/openclaw_skill.py:3-5` and `server/skills/openclaw_skill.py:68-70`.

Status: helper-only / partial integration

## Live runtime evidence used

- `http://127.0.0.1:8081/health` returned healthy during this pass.
- `http://127.0.0.1:8081/api/status` returned online during this pass.
- `http://127.0.0.1:8091/health` returned no response during this pass.
- `http://127.0.0.1:3000` returned no response during this pass.
- `http://127.0.0.1:11434/api/tags` returned `200` during this pass.
- `netstat` showed `8081` owned by PID `3052` and `11434` owned by PID `18008`.
- `server/data/bridge_heartbeat.json` reported PID `3052` and current heartbeats on `8081`.

