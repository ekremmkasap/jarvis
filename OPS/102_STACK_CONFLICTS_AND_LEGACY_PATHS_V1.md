# Stack Conflicts and Legacy Paths V1

## Cleanest ownership path for voice-first use

Use:

- `server/bridge.py`
- `hey_jarvis.py`

Optional umbrella launcher:

- `JARVIS_BASLAT.bat` -> `master_launcher.py`

Evidence:

- `JARVIS_BASLAT.bat:11-15`
- `master_launcher.py:3-8`
- `master_launcher.py:270-300`

## Launchers that exist but should not all be used together

### `JARVIS_BASLAT.bat`

- Points to `master_launcher.py`
- Treat as a convenience umbrella launcher for the bridge stack
- Not wrong, but broader than needed for a first clean bring-up

### `master_launcher.py`

- Correctly treats bridge + voice as one stack
- Also carries optional hologram logic
- Waits on gateway port `8082` without starting a gateway in the same file at `master_launcher.py:293-294`

Status: useful but slightly misleading / broader than necessary

### `server/start_jarvis.bat`

- Starts only `bridge.py`
- Good for backend-only bring-up
- Not sufficient by itself for a speaking assistant

Status: partial launcher

### `server/start_voice.bat`

- Starts only `hey_jarvis.py`
- Assumes bridge backend already exists on `8081`

Status: partial launcher

## Stacks that should stay off in the same pass

### FastAPI orchestrator (`8091`)

- Different ownership model
- Queue/task runtime, not the direct speech loop
- Starting it alongside the bridge adds "which backend owns Jarvis?" confusion

### Orchestrator UI stacks (`5001`, `5002`, `3000`)

- Separate operator interfaces
- Not required for the user's immediate goal of a working speaking assistant
- Adds more endpoints and more ownership ambiguity

### OpenClaw paths

- `server/openclaw_bridge.py` is helper-only by its own docstring
- `server/skills/openclaw_skill.py` is a wrapper skill layer
- Booting or prioritizing OpenClaw here would widen scope and duplicate command ownership

## Practical duplicate-ownership risks

- two "Jarvis" HTTP surfaces at once
- voice launcher pointing at one backend while operator thinks another backend is primary
- umbrella launcher vs direct launcher disagreement
- stale UI stack being mistaken for the assistant itself

