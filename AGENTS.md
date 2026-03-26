# AGENTS.md — Jarvis Mission Control

> **Last updated:** 2026-03-26
> **Version:** 2.0.0
> Autonomous developer AI operating system — agent catalog and behavior reference.

---

## Architecture Overview

```
Voice Layer (Hey Jarvis)
    │
    ▼
Orchestrator (FastAPI :8090)
    │ WebSocket
    ▼
Dashboard (Next.js :3000)
    │
    ▼
Task Queue ──► Agent Runner ──► Model Router
                    │               │
              ┌─────┴──────┐    ┌───┴───────────────┐
              │            │    │                   │
         Agents...    Safety   Claude/OpenRouter  Ollama
                      Policy
```

---

## Agent Registry

### 🧠 PlannerAgent

| Property | Value |
|----------|-------|
| **ID** | `planner` |
| **Model chain** | `reasoning` |
| **Risk level** | Low |
| **Auto-approve** | ✅ Yes |

**Responsibility:** Receives high-level goals and decomposes them into structured, actionable plans with agent assignments, dependencies, and risk assessments.

**Input:**
```json
{ "goal": "string", "context": {} }
```

**Output:** JSON plan with steps, agent routing, risk score, and dependencies.

**Triggers:** Any unrouted task; voice commands; manual dispatch.

---

### 🔬 RepoAnalystAgent

| Property | Value |
|----------|-------|
| **ID** | `repo_analyst` |
| **Model chain** | `code` |
| **Risk level** | Low |
| **Auto-approve** | ✅ Yes |

**Responsibility:** Analyzes repository health — architecture, CI pass rate, PR velocity, stale code, missing tests, security hotspots.

**Input:**
```json
{ "goal": "analyze repo", "context": { "repo": "owner/repo", "report_type": "daily_summary" } }
```

**Output:** Markdown analysis report saved to `outputs/reports/`.

**Triggers:** `schedule.daily_summary`, voice "analyze repository", manual dispatch.

---

### 👨‍💻 DeveloperAgent

| Property | Value |
|----------|-------|
| **ID** | `developer` |
| **Model chain** | `code` (Claude Code priority) |
| **Risk level** | Medium |
| **Auto-approve** | ❌ Requires review |

**Responsibility:** Implements features, fixes bugs, writes tests, refactors code. Routes to Claude Code for repository-aware operations.

**Input:**
```json
{ "goal": "fix null pointer in auth service", "context": { "repo": "owner/repo" } }
```

**Output:** Implementation code, test suggestions, design notes.

**Triggers:** Explicit development tasks, planner delegation, voice "implement / fix / write".

**Safety:** Changes must be reviewed (creates draft PR, not direct push).

---

### 🔍 ReviewerAgent

| Property | Value |
|----------|-------|
| **ID** | `reviewer` |
| **Model chain** | `code` |
| **Risk level** | Low |
| **Auto-approve** | ✅ Yes |

**Responsibility:** Reviews pull requests for bugs, security vulnerabilities, performance issues, style, and documentation gaps. Read-only — never modifies code.

**Input:**
```json
{ "goal": "review PR #42", "context": { "repo": "owner/repo", "pr_number": 42 } }
```

**Output:** Structured review with CRITICAL/MAJOR/MINOR ratings, recommendation (approve/request-changes).

**Triggers:** `pull_request.opened`, `pull_request.synchronize`, manual dispatch.

---

### 🐛 DebugAgent

| Property | Value |
|----------|-------|
| **ID** | `debug` |
| **Model chain** | `reasoning` |
| **Risk level** | Low |
| **Auto-approve** | ✅ Yes |

**Responsibility:** Diagnoses CI failures, runtime errors, and exception traces. Produces root cause analysis and specific fix recommendations.

**Input:**
```json
{ "goal": "CI failure on main: npm test failed", "context": { "repo": "...", "run_id": 12345 } }
```

**Output:** Incident report with root cause, fix proposal, prevention recommendations.

**Triggers:** `workflow_run.failure` (GitHub), voice "debug / fix error", CI failure events.

---

### 🚀 ReleaseAgent

| Property | Value |
|----------|-------|
| **ID** | `release` |
| **Model chain** | `default` |
| **Risk level** | Medium |
| **Auto-approve** | ✅ Yes (draft only) |

**Responsibility:** Prepares releases — drafts changelogs (keep-a-changelog format), writes user-facing release notes, suggests semver bumps, generates upgrade guides.

**Input:**
```json
{ "goal": "prepare release v2.1.0", "context": { "repo": "owner/repo" } }
```

**Output:** Changelog entry, GitHub release notes, version bump recommendation.

**Safety:** Only drafts documents — does not create releases, tags, or push commits without confirmation.

---

### 📚 DocsAgent

| Property | Value |
|----------|-------|
| **ID** | `docs` |
| **Model chain** | `default` |
| **Risk level** | Low |
| **Auto-approve** | ✅ Yes |

**Responsibility:** Writes and updates technical documentation: README, AGENTS.md (this file), RUNBOOK, API docs, inline comments, prompt docs.

**Input:**
```json
{ "goal": "update README with new config options", "context": { "doc_type": "readme" } }
```

**Output:** Production-ready markdown documentation.

**Triggers:** Post-feature completion, scheduled doc sync, manual "update docs".

---

### 🔊 VoiceNarratorAgent

| Property | Value |
|----------|-------|
| **ID** | `voice_narrator` |
| **Model chain** | `chat` |
| **Risk level** | Low |
| **Auto-approve** | ✅ Yes |

**Responsibility:** Converts technical agent outputs into short, natural spoken announcements for the TTS engine. Max 2-3 sentences, no markdown or URLs.

**Input:**
```json
{ "goal": "PR #42 review complete: 2 issues found", "context": {} }
```

**Output:** Plain text suitable for speech synthesis.

**Triggers:** Task completion events, CI failures, PR merges, scheduled announcements.

---

### 🎮 MissionControlAgent

| Property | Value |
|----------|-------|
| **ID** | `mission_control` |
| **Model chain** | `reasoning` |
| **Risk level** | Low |
| **Auto-approve** | ✅ Yes |

**Responsibility:** Top-level coordinator. Monitors all agents, detects stuck/failed workflows, generates system health reports, coordinates cross-agent handoffs, sends weekly engineering digests.

**Input:**
```json
{ "goal": "system health check", "context": {} }
```

**Output:** Dashboard status report (GREEN/YELLOW/RED), active agent summary, recommended actions.

**Triggers:** Weekly schedule, manual "status" command, anomaly detection.

---

## Autonomy Policy

### ✅ Auto-Approved (No Confirmation Required)
- Issue triage and labeling
- PR review and commenting
- Code analysis and reports
- CI failure diagnosis
- Changelog drafting
- Release note generation
- Documentation updates (README, AGENTS.md, RUNBOOK)
- Daily/weekly summaries
- Stale PR/issue detection
- Dashboard updates

### ⚠️ Requires User Confirmation
- Merging to protected branches (main, master, release, prod)
- Force pushing
- Deleting files or branches
- Rotating secrets or credentials
- Executing shell commands
- Publishing releases
- Any irreversible production change

### 🚫 Blocked (Never Executed)
- Destructive filesystem operations
- Billing/payment modifications
- Access credential exfiltration

---

## Model Routing

| Chain | Primary Model | Fallback |
|-------|--------------|---------|
| `code` | `anthropic/claude-sonnet-4-6` via OpenRouter | `deepseek/deepseek-v3.2` |
| `reasoning` | `anthropic/claude-opus-4.6` via OpenRouter | `z-ai/glm-5-turbo` |
| `chat` | `minimax/minimax-m2.7` via OpenRouter | `stepfun/step-3.5-flash:free` |
| `default` | `qwen3:8b` via Ollama | `deepseek/deepseek-v3.2` |

Claude Code is the primary execution engine for repository-aware coding tasks. OpenRouter provides multi-model fallback for all other workloads.

---

## Adding a New Agent

1. Create `agents/your_agent.py` extending `RuntimeAgent`
2. Set `name`, `description`, `model_chain`, `risk_level`
3. Implement `execute_task(self, task) -> str`
4. Register in `agents/registry.py` under `_RUNTIME_AGENTS`
5. Add config entry to `config/agents.yaml`
6. Document here in AGENTS.md

---

## Retry Policy

All agents retry up to `max_retries` times (default: 2) with exponential backoff.
If all retries fail → task moves to `FAILED` status.
Failed tasks appear in dashboard and trigger a VoiceNarrator announcement if `announce_task_completion: true`.
