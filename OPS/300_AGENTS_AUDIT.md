# 300 Agents Audit

Date: 2026-04-13
Scope: AGENTS.md 9-agent canonical implementation audit for Tab-3 Codex sprint.

## Canonical Spec Summary

### PlannerAgent
- ID: `planner`
- Chain: `reasoning`
- Responsibility: goal decomposition, dependencies, risk, agent assignment.
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
- Safety: changes require review; should not push directly.

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
- `server/bridge.py`: operator-facing HTTP + Telegram runtime, currently exposes `/api/chat`, `/command`, `/health`, `/metrics`, agent selection via Telegram `/agent`, and normal natural-language routing.
- `hey_jarvis.py`: hologram/voice runtime; primary speech API is synchronous `speak(text, track_response=False)`.

### Existing `server/agents/`
- Present: legacy/local agents such as `planner_agent.py`, `task_planner_agent.py`, `executor_agent.py`, clone lanes under `server/agents/clones/`, and multi-slot codex agents under `atlas/forge/nexus/shield/spark`.
- Missing: `server/agents/canonical/` package does not exist.
- Constraint: canonical agents must stay separate from clone swarm agents.

### Existing Tests
- Bridge/runtime/model-router tests already exist, but there are no canonical-agent tests.
- Relevant patterns:
  - `tests/test_model_router.py` already tests fallback behavior.
  - `tests/test_bridge_endpoints.py` focuses on endpoint helpers and response shapes.
  - `tests/test_task_planner_agent.py` shows lightweight unittest style for agent logic.

## Gap Analysis Per Canonical Agent

### PlannerAgent
- Gap: no canonical async agent wrapper, no canonical registry, no JSON envelope.

### RepoAnalystAgent
- Gap: no canonical repo audit agent, no report path convention in `outputs/reports/`.

### DeveloperAgent
- Gap: no bounded write-safe implementation agent tied to explicit `target_file`.

### ReviewerAgent
- Gap: existing review-related code is separate; no canonical read-only diff review agent.

### DebugAgent
- Gap: no canonical root-cause analysis agent envelope.

### ReleaseAgent
- Gap: no canonical changelog/semver agent.

### DocsAgent
- Gap: no canonical docs generation agent.

### VoiceNarratorAgent
- Gap: no canonical narrator agent and no `hey_jarvis.py` bridge hook.

### MissionControlAgent
- Gap: no canonical activity log and no monitor over canonical agent history.

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
- `process_message()` path today:
  - shell shorthands
  - optional intent handling
  - active `/agent` selection
  - team mode
  - generic route detection -> `call_ollama()`
- Canonical keyword routing can be inserted before generic route detection without breaking `/agent` command behavior.

## Constraints Confirmed
- Do not touch `master_launcher.py`.
- Do not modify clone swarm agents in `server/agents/clones/`.
- Do not bypass `server/model_router.py` for LLM access.
- Do not break existing `bridge.py` endpoints or Telegram `/agent` command.
