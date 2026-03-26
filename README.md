# 🤖 Jarvis Mission Control v2.0

> Autonomous developer AI operating system. Combines **Claude Code** (coding agent) + **OpenRouter** (multi-model routing) + **voice control** + **mission-control dashboard** into a single always-on platform.

---

## What It Does

- **Listens** for "Hey Jarvis" wake word → transcribes → executes → speaks back
- **Monitors** GitHub repos: auto-reviews PRs, triages issues, diagnoses CI failures
- **Dispatches** specialized agents: Planner, Developer, Reviewer, Debug, Release, Docs, and more
- **Visualizes** all agent activity in a futuristic real-time dashboard
- **Operates autonomously** for safe tasks, asks for confirmation on destructive ones
- **Routes models** intelligently: Claude for code, cheaper models for summaries, Ollama for local

---

## Quick Start

### 1. Install dependencies

```bash
# Python backend
pip install fastapi uvicorn[standard] pyyaml websockets requests pyaudio

# Optional: better STT
pip install faster-whisper

# Optional: better TTS
pip install edge-tts

# Dashboard (Node.js 18+)
cd apps/web-ui && npm install
```

### 2. Configure environment

```bash
cp .env.example .env
# Fill in:
# OPENROUTER_API_KEY=your_key
# GITHUB_TOKEN=your_token
# JARVIS_WATCHED_REPOS=owner/repo1,owner/repo2
# PICOVOICE_ACCESS_KEY=optional_for_wake_word
```

### 3. Start the orchestrator

```bash
python -m services.orchestrator.main
# Listening on http://localhost:8090
# WebSocket at ws://localhost:8090/ws
```

### 4. Start the dashboard

```bash
cd apps/web-ui && npm run dev
# Open http://localhost:3000
```

### 5. Start voice service (optional)

```bash
python services/voice/voice_service.py
# Say "Hey Jarvis" to activate
```

### 6. Start GitHub worker (optional)

```bash
python services/github-worker/worker.py
# Polls watched repos every 60 seconds
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   JARVIS MISSION CONTROL                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Voice Service          Dashboard (Next.js :3000)          │
│  ┌──────────────┐       ┌──────────────────────────────┐   │
│  │ Wake Word    │       │ Agent Graph  │ Task Queue     │   │
│  │ STT/Whisper  │       │ Command      │ Notifications  │   │
│  │ TTS/Edge     │       │ Console      │ Stats Bar      │   │
│  └──────┬───────┘       └──────┬───────────────────────┘   │
│         │ HTTP POST             │ WebSocket                 │
│         ▼                      ▼                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Orchestrator (FastAPI :8090)                 │   │
│  │  POST /task  │  GET /tasks  │  WS /ws                │   │
│  │  POST /voice │  GET /agents │  POST /tasks/:id/confirm│  │
│  │                                                      │   │
│  │  Safety Policy ──► Task Queue ──► Agent Runner       │   │
│  └────────────────────────┬─────────────────────────────┘   │
│                            │                                 │
│        ┌───────────────────┼────────────────────┐           │
│        ▼                   ▼                    ▼           │
│  ┌──────────┐       ┌────────────┐      ┌────────────┐      │
│  │ Planner  │       │ Developer  │      │ Reviewer   │      │
│  │ Analyst  │       │(Claude Code│      │ Debugger   │      │
│  │ Narrator │       │ priority)  │      │ Release    │      │
│  └────┬─────┘       └─────┬──────┘      └─────┬──────┘      │
│       └──────────────────┬┘────────────────────┘            │
│                          ▼                                   │
│                  ┌───────────────┐                          │
│                  │  Model Router │                          │
│                  │  OpenRouter   │                          │
│                  │  Ollama       │                          │
│                  └───────────────┘                          │
│                                                             │
│  GitHub Worker                     GitHub Actions          │
│  ┌────────────────┐               ┌─────────────────────┐  │
│  │ PR Monitor     │               │ pr-review.yml       │  │
│  │ Issue Monitor  │               │ issue-triage.yml    │  │
│  │ CI Monitor     │               │ daily-summary.yml   │  │
│  │ Daily Summary  │               │ ci-failure.yml      │  │
│  └────────────────┘               └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Roster

| Agent | Purpose | Auto-approve |
|-------|---------|-------------|
| `planner` | Breaks goals into plans | ✅ |
| `repo_analyst` | Repository health analysis | ✅ |
| `developer` | Code implementation (Claude Code) | ⚠️ Review needed |
| `reviewer` | PR code review | ✅ |
| `debug` | CI failure diagnosis | ✅ |
| `release` | Changelog & release notes | ✅ (draft only) |
| `docs` | Documentation writing | ✅ |
| `voice_narrator` | TTS announcements | ✅ |
| `mission_control` | System health & coordination | ✅ |

See [AGENTS.md](AGENTS.md) for full agent documentation.

---

## Model Strategy

| Workload | Provider | Model |
|---------|---------|-------|
| Code review, implementation | OpenRouter | `anthropic/claude-sonnet-4-6` |
| Complex reasoning, planning | OpenRouter | `anthropic/claude-opus-4.6` |
| Background summaries | OpenRouter | `deepseek/deepseek-v3.2` |
| Cheap fast tasks | OpenRouter | `stepfun/step-3.5-flash:free` |
| Voice/chat responses | OpenRouter | `minimax/minimax-m2.7` |
| Local/offline fallback | Ollama | `qwen3:8b` |

Claude Code is the **primary coding agent** for repository-aware work. OpenRouter routes everything else with cost-optimized fallback chains.

---

## Directory Structure

```
jarvis-mission-control/
├── apps/
│   └── web-ui/              # Next.js dashboard
├── services/
│   ├── orchestrator/        # FastAPI + WebSocket + task queue
│   ├── voice/               # Wake word + STT + TTS
│   └── github-worker/       # GitHub event polling
├── agents/
│   ├── runtime_base.py      # Base class for orchestrator agents
│   ├── planner_agent.py
│   ├── repo_analyst_agent.py
│   ├── developer_agent.py
│   ├── reviewer_agent.py
│   ├── debug_agent.py
│   ├── release_agent.py
│   ├── docs_agent.py
│   ├── voice_narrator_agent.py
│   ├── mission_control_agent.py
│   └── registry.py
├── config/
│   ├── jarvis.yaml          # Main config
│   ├── agents.yaml          # Agent config
│   └── model_router.yml     # Model routing chains
├── prompts/                 # Prompt templates
├── memory/                  # Persistent state (SQLite)
├── outputs/                 # Agent outputs, reports
├── logs/                    # Application logs
├── .github/
│   └── workflows/
│       ├── pr-review.yml
│       ├── issue-triage.yml
│       ├── daily-summary.yml
│       └── ci-failure-diagnosis.yml
├── AGENTS.md
└── README.md
```

---

## API Reference

### Orchestrator (`:8090`)

| Endpoint | Method | Description |
|---------|--------|-------------|
| `/task` | POST | Create a new task |
| `/tasks` | GET | List all tasks |
| `/tasks/:id` | GET | Get task details |
| `/tasks/:id/confirm` | POST | Confirm a pending task |
| `/agents` | GET | List registered agents |
| `/voice` | POST | Submit voice command |
| `/health` | GET | System health check |
| `/ws` | WebSocket | Real-time event stream |

### Task Create Body

```json
{
  "goal": "Review PR #42 in owner/repo",
  "agent": "reviewer",
  "priority": "normal",
  "context": { "repo": "owner/repo", "pr_number": 42 },
  "dry_run": false
}
```

---

## Voice Commands

| Say | Action |
|-----|--------|
| "Hey Jarvis, analyze the repository" | repo_analyst task |
| "Hey Jarvis, review PRs" | reviewer task |
| "Hey Jarvis, debug the CI failure" | debug task |
| "Hey Jarvis, prepare release notes" | release task |
| "Hey Jarvis, status" | mission_control health check |
| "Hey Jarvis, daily summary" | repo_analyst daily report |

---

## Environment Variables

See `.env.example` for full list. Key variables:

```bash
OPENROUTER_API_KEY=       # Required for cloud models
GITHUB_TOKEN=             # Required for GitHub automation
JARVIS_WATCHED_REPOS=     # Comma-separated: owner/repo1,owner/repo2
PICOVOICE_ACCESS_KEY=     # Optional: better wake word detection
OLLAMA_URL=               # Default: http://127.0.0.1:11434
ORCHESTRATOR_PORT=        # Default: 8090
ORCHESTRATOR_URL=         # Default: http://127.0.0.1:8090
```

---

## GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM calls |
| `GITHUB_TOKEN` | Auto-provided by Actions |

---

## License

MIT — Jarvis Mission Control
