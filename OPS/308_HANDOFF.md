# 308 Handoff

Date: 2026-04-13
Scope: AGENTS.md 9-agent canonical implementation handoff for Tab-3 Codex sprint.

## Canonical Agents

1. `planner`
   - File: `server/agents/canonical/planner.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
2. `repo_analyst`
   - File: `server/agents/canonical/repo_analyst.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
3. `developer`
   - File: `server/agents/canonical/developer.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
4. `reviewer`
   - File: `server/agents/canonical/reviewer.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
5. `debug`
   - File: `server/agents/canonical/debug_agent.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
6. `release`
   - File: `server/agents/canonical/release_agent.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
7. `docs`
   - File: `server/agents/canonical/docs_agent.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
8. `voice_narrator`
   - File: `server/agents/canonical/voice_narrator.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`
9. `mission_control`
   - File: `server/agents/canonical/mission_control.py`
   - Signature: `async def run(task: str, context: dict | None = None) -> dict`

Registry:
- `server/agents/canonical/__init__.py`

Shared helpers:
- `server/agents/canonical/base.py`
- `server/agents/canonical/constants.py`
- `server/agents/canonical/runtime.py`

## Bridge `/agent` Endpoint

Location:
- `server/bridge.py`

Request:
```json
{
  "agent": "planner",
  "task": "Jarvis durumunu raporla",
  "context": {}
}
```

Response:
- HTTP `200` with canonical agent result dict on success
- HTTP `400` if `agent`, `task`, or `context` shape is invalid
- HTTP `404` if agent id is unknown

Handler path:
- `POST /agent` -> `server.agents.canonical.runtime.handle_agent_request(...)`

## Telegram Keyword Routing

Natural-language keyword map:
- `planner`: `plan yap`, `hedef`, `gorev olustur`, `ne yapayim`
- `repo_analyst`: `repo analiz`, `saglik raporu`, `git durum`, `kod durumu`
- `developer`: `kod yaz`, `implement`, `feature ekle`, `degistir`
- `reviewer`: `review`, `incele`, `pr kontrol`, `kod incele`
- `debug`: `hata`, `debug`, `neden calismiyor`, `fix`
- `release`: `release`, `changelog`, `versiyon`, `ne degisti`
- `docs`: `dokumantasyon`, `readme guncelle`, `acikla`
- `mission_control`: `sistem durumu`, `agent saglik`, `ne calisiyor`
- `voice_narrator`: internal only

Bridge flow:
- non-command Telegram text enters `process_message(...)`
- active `/agent` mode and team mode still preserve precedence
- canonical keyword dispatch runs before generic LLM route fallback

## Voice Hook

Location:
- `hey_jarvis.py`

Added functions:
- `async def speak_agent_result(raw_output: str, *, track_response: bool = False) -> str`
- `def narrate_agent_result(raw_output: str, *, track_response: bool = False) -> str`

Runtime behavior:
- narrator summary comes from `VoiceNarratorAgent`
- if narrator fails, fallback is local sanitized text under 200 chars
- `handle(...)` now uses `narrate_agent_result(...)` for final spoken output

How to test:
1. Run `python -m pytest tests/test_hey_jarvis_live_mode.py -v --tb=short`
2. Import `hey_jarvis` and call `narrate_agent_result("raw output")`
3. In live runtime, speak any normal command response and verify condensed TTS

## Validation Performed

Pytest:
- `python -m pytest tests/test_canonical_batch1.py tests/test_canonical_batch2.py tests/test_canonical_batch3.py tests/test_canonical_batch4.py tests/test_hey_jarvis_live_mode.py -q`
- Result: `22 passed`

Canonical import smoke:
- verified 9 registered agents
- verified `planner.run(...)`
- verified `voice_narrator.run(...)`
- verified `mission_control.run(...)`

Bridge handler smoke:
- verified `server.agents.canonical.runtime.handle_agent_request(...)` returns `200` for a valid request

## Adding a New Canonical Agent

1. Add the new id to `server/agents/canonical/constants.py`
2. Implement the agent under `server/agents/canonical/`
3. Export it in `server/agents/canonical/__init__.py`
4. Add keyword routing only if natural-language dispatch is desired
5. Add focused pytest coverage
6. Update `AGENTS.md`, `CLAUDE.md`, and this handoff if the registry changes

## Known Limitations

- The live bridge instance already running on `127.0.0.1:8081` returned `404` for `POST /agent` during verification. This indicates the current running process predates the new code and needs a restart to expose the new endpoint.
- Canonical agents intentionally fall back deterministically when the preferred model is unavailable; they do not block the flow waiting on long fallback chains.
- `VoiceNarratorAgent` defaults to deterministic compression unless `context["prefer_llm"]` is explicitly enabled.
