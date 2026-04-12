# 301 Agents Implementation Plan

Date: 2026-04-13

## Implementation Baseline

Existing canonical foundation already present:
- `server/agents/canonical/base.py`
- `server/agents/canonical/planner.py`
- `server/agents/canonical/repo_analyst.py`
- `server/agents/canonical/developer.py`
- `tests/test_canonical_batch1.py`

Execution plan is therefore:
1. keep the base contract stable
2. validate batch1
3. implement batches 2-4 on top of the current canonical package
4. integrate bridge routing and voice narration

## Base Class Design

Class: `CanonicalAgent`

Responsibilities:
- normalize async `run(task, context)` envelope
- call `server.model_router.build_model_router(...)`
- centralize timestamping and JSONL logging
- sanitize sensitive fields before logging

Current core helpers already exist:
- `async run(task: str, context: dict | None = None) -> dict`
- `_execute(task: str, context: dict) -> dict`
- `_call_llm(prompt: str, system: str | None, max_tokens: int = 800) -> str`
- `_log_result(result: dict) -> None`
- `_sanitize_context(context: dict) -> dict`
- `_result(status: str, timestamp: str, output: dict, **payload) -> dict`

Logging target:
- `server/logs/canonical_agents.jsonl`

Sensitive-field scrub list:
- keys containing `key`, `token`, `secret`, `password`, `authorization`, `cookie`

Rule:
- all LLM attempts must go through `server.model_router.ModelRouter.chat`
- deterministic fallbacks are allowed only after router attempt or when LLM output is empty

## Per-Agent Plan

### `server/agents/canonical/planner.py`
- Status: exists
- Keep current shape:
  - `goals`
  - `agents_needed`
  - `steps`
  - `estimated_complexity`
  - `priority`
  - `risk_score`
- Work: validate current behavior only

### `server/agents/canonical/repo_analyst.py`
- Status: exists
- Keep current shape:
  - `recent_commits`
  - `changed_files`
  - `health_score`
  - `warnings`
  - `recommendations`
  - `report_path`
- Work: validate current behavior only

### `server/agents/canonical/developer.py`
- Status: exists
- Keep current shape:
  - `files_changed`
  - `description`
  - `status`
- Work:
  - preserve explicit target-only writes
  - preserve repo-root guard

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
- Strategy:
  - ask LLM for strict JSON review report
  - fallback scans diff for obvious risky patterns

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
- Fallback:
  - build markdown from `description`, `code`, or `command` context

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
  - no markdown, code blocks, or URLs
- Fallback:
  - strip formatting and compress deterministically

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
  - no activity > 10 minutes => stuck warning
  - 3+ consecutive errors => critical

## Registry Plan

Update `server/agents/canonical/__init__.py` to export exactly 9 canonical agents:
- `planner`
- `repo_analyst`
- `developer`
- `reviewer`
- `debug`
- `release`
- `docs`
- `voice_narrator`
- `mission_control`

## Bridge Routing Design

### HTTP
- Add `POST /agent`
- Body:
  - `agent: str`
  - `task: str`
  - `context: dict` optional
- Response:
  - canonical agent result dict
- Constraint:
  - add a new endpoint only
  - do not alter response contract of `/api/chat` or `/command`

### Telegram keyword routing
- Add canonical keyword map for natural-language messages only
- Keep slash-command `/agent` behavior unchanged
- Insert routing before generic `detect_route(text)` fallback

Keyword map:
- `planner`: `["plan yap", "hedef", "gorev olustur", "ne yapayim"]`
- `repo_analyst`: `["repo analiz", "saglik raporu", "git durum", "kod durumu"]`
- `developer`: `["kod yaz", "implement", "feature ekle", "degistir"]`
- `reviewer`: `["review", "incele", "pr kontrol", "kod incele"]`
- `debug`: `["hata", "debug", "neden calismiyor", "fix"]`
- `release`: `["release", "changelog", "versiyon", "ne degisti"]`
- `docs`: `["dokumantasyon", "readme guncelle", "acikla"]`
- `mission_control`: `["sistem durumu", "agent saglik", "ne calisiyor"]`
- `voice_narrator`: `[]`

Formatting:
- summarize canonical result into compact operator-safe text
- keep `voice_narrator` internal unless explicitly addressed

## Voice Hook Design

Target file:
- `hey_jarvis.py`

Existing speech function:
- `speak(text: str, track_response: bool = False)`

Planned additions:
- guarded import of `VoiceNarratorAgent`
- `async def speak_agent_result(raw_output: str): ...`
- `def narrate_agent_result(raw_output: str, track_response: bool = False): ...`

Behavior:
- narrator returns spoken Turkish summary
- if narrator fails, fallback to sanitized `raw_output[:200]`
- keep existing TTS engine untouched

## Test Strategy

### Batch 1
- existing `tests/test_canonical_batch1.py`
- run to validate current foundation before continuing

### Batch 2
- add `tests/test_canonical_batch2.py`
- cover reviewer/debug response shapes and deterministic fallbacks

### Batch 3
- add `tests/test_canonical_batch3.py`
- cover release semver heuristic, docs markdown generation, narrator format limits

### Batch 4
- add `tests/test_canonical_batch4.py`
- cover mission control JSONL parsing and stuck/error detection

### Integration
- extend `tests/test_bridge_endpoints.py` only if the import surface stays manageable
- otherwise keep endpoint coverage inside batch4 or a focused new test module
