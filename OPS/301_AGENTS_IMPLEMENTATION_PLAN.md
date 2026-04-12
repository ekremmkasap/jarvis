# 301 Agents Implementation Plan

Date: 2026-04-13

## Package Layout

Create `server/agents/canonical/` with:
- `__init__.py`
- `base.py`
- `planner.py`
- `repo_analyst.py`
- `developer.py`
- `reviewer.py`
- `debug_agent.py`
- `release_agent.py`
- `docs_agent.py`
- `voice_narrator.py`
- `mission_control.py`

## Base Class Design

Class: `CanonicalAgent`

Responsibilities:
- normalize async `run(task, context)` envelope
- call `server.model_router.build_model_router(...)`
- centralize timestamping and JSONL logging
- sanitize sensitive fields before logging

Proposed fields:
- `agent_id: str`
- `name: str`
- `role: str`
- `model_chain: str`
- `model_preference: str`

Proposed base helpers:
- `async run(task: str, context: dict | None = None) -> dict`
- `_execute(task: str, context: dict) -> dict` implemented by subclasses
- `_call_llm(prompt: str, system: str | None, max_tokens: int = 800) -> str`
- `_router_chat(messages: list[dict], system: str | None, max_tokens: int, num_ctx: int) -> tuple[str, dict]`
- `_log_result(result: dict) -> None`
- `_sanitize_context(context: dict) -> dict`
- `_result(status: str, **payload) -> dict`

Logging target:
- `server/logs/canonical_agents.jsonl`

Sensitive-field scrub list:
- keys containing `key`, `token`, `secret`, `password`, `authorization`, `cookie`

LLM behavior:
- all LLM attempts route through `server.model_router.ModelRouter.chat`
- if routing fails, subclasses may use deterministic fallback builders, but only after router attempt

## Per-Agent Plan

### `server/agents/canonical/planner.py`
- Class: `PlannerAgent`
- `model_chain = "reasoning"`
- Output fields:
  - `goals`
  - `agents_needed`
  - `steps`
  - `estimated_complexity`
  - `priority`
  - `risk_score`
- Strategy:
  - ask for strict JSON
  - fallback heuristic based on task keywords

### `server/agents/canonical/repo_analyst.py`
- Class: `RepoAnalystAgent`
- `model_chain = "code"`
- Read-only subprocess inputs:
  - `git log --oneline -5`
  - `git diff --stat --cached`
  - `git diff --stat`
  - optional `rg --files` sample counts
- Output fields:
  - `recent_commits`
  - `changed_files`
  - `health_score`
  - `warnings`
  - `recommendations`
  - `report_path`
- Also writes markdown report under `outputs/reports/`

### `server/agents/canonical/developer.py`
- Class: `DeveloperAgent`
- `model_chain = "code"`
- Safety:
  - requires `context["target_file"]` or `context["target_files"]`
  - only writes to explicitly declared targets
  - reject paths outside repo root
- Output fields:
  - `files_changed`
  - `description`
  - `status`
- Write strategy:
  - if `proposed_content` exists, write it directly
  - otherwise read target, ask LLM for full replacement content, then overwrite target only

### `server/agents/canonical/reviewer.py`
- Class: `ReviewerAgent`
- `model_chain = "code"`
- Read-only subprocess:
  - `git diff --cached`
  - fallback `git diff`
- Output fields:
  - `issues`
  - `suggestions`
  - `severity_counts`
  - `overall_verdict`
- LLM prompt asks for JSON review report; fallback scans diff for obvious risky patterns

### `server/agents/canonical/debug_agent.py`
- Class: `DebugAgent`
- `model_chain = "reasoning"`
- Input priority:
  - `context["stack_trace"]`
  - `context["error_message"]`
  - task text
- Output fields:
  - `error_type`
  - `likely_cause`
  - `affected_files`
  - `suggested_fix`
  - `confidence`

### `server/agents/canonical/release_agent.py`
- Class: `ReleaseAgent`
- `model_chain = "default"`
- Read-only subprocess:
  - `git log --oneline -20`
- Output fields:
  - `changelog_entries`
  - `suggested_version`
  - `breaking_changes`
  - `highlights`
- Semver heuristic:
  - `feat!` or `BREAKING CHANGE` => major
  - `feat` => minor
  - else => patch

### `server/agents/canonical/docs_agent.py`
- Class: `DocsAgent`
- `model_chain = "default"`
- Output fields:
  - `doc_type`
  - `content`
  - `target_file_suggestion`
- Fallback builds markdown from description/code/command context

### `server/agents/canonical/voice_narrator.py`
- Class: `VoiceNarratorAgent`
- `model_chain = "chat"`
- Output fields:
  - `tts_text`
  - `original_length`
  - `compressed_length`
- Rules:
  - Turkish only
  - 2-3 sentences
  - max 200 chars
  - no markdown/code/URLs
- Fallback: strip formatting and compress deterministically

### `server/agents/canonical/mission_control.py`
- Class: `MissionControlAgent`
- `model_chain = "reasoning"`
- Data source:
  - `server/logs/canonical_agents.jsonl`
- Output fields:
  - `agents`
  - `stuck_tasks`
  - `last_activity_per_agent`
  - `overall_health`
  - `recommendations`
- Detection rules:
  - no activity >10 min => stuck warning
  - 3+ consecutive errors => critical

## Bridge Routing Design

HTTP:
- Add `POST /agent`
- Body:
  - `agent: str`
  - `task: str`
  - `context: dict` optional
- Response:
  - canonical agent result dict

Telegram keyword map:
- `planner`: `["plan yap", "hedef", "gorev olustur", "ne yapayim"]`
- `repo_analyst`: `["repo analiz", "saglik raporu", "git durum", "kod durumu"]`
- `developer`: `["kod yaz", "implement", "feature ekle", "degistir"]`
- `reviewer`: `["review", "incele", "pr kontrol", "kod incele"]`
- `debug`: `["hata", "debug", "neden calismiyor", "fix"]`
- `release`: `["release", "changelog", "versiyon", "ne degisti"]`
- `docs`: `["dokumantasyon", "readme guncelle", "acikla"]`
- `mission_control`: `["sistem durumu", "agent saglik", "ne calisiyor"]`
- `voice_narrator`: `[]`

Insertion point:
- `process_message()` before generic `detect_route(text)`
- do not alter explicit slash-command behavior

Formatting for Telegram replies:
- summarize canonical result for chat-safe text
- keep `voice_narrator` internal by default

## Voice Hook Design

Target file:
- `hey_jarvis.py`

Existing speech function:
- `speak(text: str, track_response: bool = False)`

Plan:
- import `VoiceNarratorAgent` with guard
- add async wrapper:
  - `async def speak_agent_result(raw_output: str): ...`
- add sync helper:
  - `def narrate_agent_result(raw_output: str, track_response: bool = False): ...`
- on narrator failure:
  - fallback to sanitized `raw_output[:200]`

Minimal initial integration:
- use hook from command/result flow without altering speech engine internals

## Test Strategy

### Batch 1
- `tests/test_canonical_batch1.py`
- covers registry/base/planner/repo analyst/developer write guard

### Batch 2
- `tests/test_canonical_batch2.py`
- covers reviewer/debug response shape and diff/error parsing fallbacks

### Batch 3
- `tests/test_canonical_batch3.py`
- covers release semver heuristic, docs markdown generation, narrator length/format constraints

### Batch 4
- `tests/test_canonical_batch4.py`
- covers mission control log parsing and stuck/error detection

### Integration
- extend `tests/test_bridge_endpoints.py` with `POST /agent` endpoint coverage if needed
- add small `hey_jarvis` hook test only if import surface is safe; otherwise keep smoke/manual validation
