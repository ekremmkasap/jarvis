# 300 Agents Audit

Date: 2026-04-13
Scope: AGENTS.md 9-agent canonical implementation audit for Tab-3 Codex sprint.

## Canonical Spec Summary

### PlannerAgent
- ID: `planner`
- Chain: `reasoning`
- Responsibility: goal decomposition, dependency mapping, routing, risk assessment.
- Input: `{ "goal": "string", "context": {} }`
- Output: structured JSON plan.

### RepoAnalystAgent
- ID: `repo_analyst`
- Chain: `code`
- Responsibility: repo health, CI/test/risk/staleness analysis.
- Output target from AGENTS.md: markdown report under `outputs/reports/`.

### DeveloperAgent
- ID: `developer`
- Chain: `code`
- Responsibility: implement features/fixes/tests/refactors.
- Safety: changes require review; should stay bounded to explicit targets.

### ReviewerAgent
- ID: `reviewer`
- Chain: `code`
- Responsibility: PR/code review, read-only, structured severity report.

### DebugAgent
- ID: `debug`
- Chain: `reasoning`
- Responsibility: diagnose failures, root cause, fix recommendation.

### ReleaseAgent
- ID: `release`
- Chain: `default`
- Responsibility: changelog, semver suggestion, release note drafts.

### DocsAgent
- ID: `docs`
- Chain: `default`
- Responsibility: README/RUNBOOK/API docs/prompt docs updates.

### VoiceNarratorAgent
- ID: `voice_narrator`
- Chain: `chat`
- Responsibility: compress technical output to 2-3 spoken Turkish sentences.

### MissionControlAgent
- ID: `mission_control`
- Chain: `reasoning`
- Responsibility: monitor agent health, detect stuck/failed workflows, emit system health.

## Current Runtime Audit

### Relevant Existing Files
- `AGENTS.md`: canonical source of truth for the 9 agents.
- `server/agent_loop.py`: legacy ReAct loop against direct Ollama HTTP; not canonical-agent-ready.
- `server/model_router.py`: reusable multi-provider router with chain/fallback handling. This is the required LLM entry point.
- `server/bridge.py`: operator-facing HTTP + Telegram runtime, currently exposes `/api/chat`, `/command`, `/health`, `/metrics`, Telegram `/agent`, and natural-language routing.
- `hey_jarvis.py`: hologram/voice runtime; primary speech API is synchronous `speak(text, track_response=False)`.
- `config/agents.yaml`: already contains config entries for all 9 canonical agents.

### Existing `server/agents/`
- Present: legacy/local agents such as `planner_agent.py`, `task_planner_agent.py`, `executor_agent.py`, clone lanes under `server/agents/clones/`, and multi-slot codex agents under `atlas/forge/nexus/shield/spark`.
- Present: `server/agents/canonical/` already exists and contains:
  - `base.py`
  - `planner.py`
  - `repo_analyst.py`
  - `developer.py`
  - `__init__.py`
- Constraint: canonical agents must stay separate from clone swarm agents.

### Existing Tests
- Present: `tests/test_canonical_batch1.py`
- Missing:
  - `tests/test_canonical_batch2.py`
  - `tests/test_canonical_batch3.py`
  - `tests/test_canonical_batch4.py`
- Existing bridge/model-router tests provide integration patterns for endpoint-safe additions.

## Gap Analysis Per Canonical Agent

### PlannerAgent
- Status: implemented in `server/agents/canonical/planner.py`
- Remaining:
  - keep registry aligned when other agents land
  - validate batch1 tests before moving on

### RepoAnalystAgent
- Status: implemented in `server/agents/canonical/repo_analyst.py`
- Remaining:
  - no additional structural gaps beyond validation

### DeveloperAgent
- Status: implemented in `server/agents/canonical/developer.py`
- Remaining:
  - ensure write guard stays strict
  - preserve review-required status semantics

### ReviewerAgent
- Gap: missing canonical implementation and tests.

### DebugAgent
- Gap: missing canonical implementation and tests.

### ReleaseAgent
- Gap: missing canonical implementation and tests.

### DocsAgent
- Gap: missing canonical implementation and tests.

### VoiceNarratorAgent
- Gap: missing canonical implementation and `hey_jarvis.py` hook.

### MissionControlAgent
- Gap: missing canonical implementation and JSONL activity analysis.

## `bridge.py` Routing Audit

### Existing `/agent` State
- Telegram command `/agent` already exists and selects from a large non-canonical agent catalog.
- This command must remain untouched semantically.

### Existing HTTP State
- `WebHandler.do_POST` currently handles:
  - `POST /api/chat`
  - `POST /command`
  - `POST /api/accounts/update`
- `POST /agent` does not exist yet.

### Natural-Language Telegram Flow
- `TelegramBot._handle_update()` sends non-command text into `process_message(chat_id, text)`.
- `process_message()` eventually routes generic text via `detect_route(...)` and `call_ollama(...)`.
- Canonical keyword routing can be inserted before generic route detection without breaking slash commands or the existing Telegram `/agent` behavior.

## Confirmed Constraints
- Do not touch `master_launcher.py`.
- Do not modify clone swarm agents in `server/agents/clones/`.
- Do not bypass `server/model_router.py` for LLM access.
- Do not break existing `bridge.py` endpoints or Telegram `/agent` command.
- Do not log API keys, tokens, cookies, or raw secret-bearing context.
