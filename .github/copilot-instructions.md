# 🤖 Jarvis Mission Control — AI Agent Instructions

**Last updated**: 2026-04-23 | **Version**: 2.0  
**Project**: Autonomous multi-agent AI orchestration system

---

## Quick Context

Jarvis Mission Control is an autonomous AI operating system that combines:
- **9+ specialized agents** (Planner, Developer, Reviewer, Debug, Release, Docs, etc.)
- **Codex execution slots** (forge, nexus, spark, shield, atlas)
- **Multi-model routing** (Claude/OpenRouter primary, Ollama fallback)
- **FastAPI bridge** for agent dispatch and Telegram integration
- **Voice control** + real-time dashboard
- **Persistent agent memory** per slot

**Your task**: Help develop, test, and deploy agent components, skills, and integrations.

---

## Essential Commands

Run these from `src/` directory:

```bash
# Backend tests (all test_*.py in tests/)
pytest tests/test_canonical_batch1.py tests/test_codex_management.py -v --tb=short

# Lint Python code
ruff check . --fix

# Frontend check (if modifying web-ui)
cd apps/web-ui && npm run build && npm run dev

# Start orchestrator (main server)
python -m services.orchestrator.main

# Quick validate (bridge + agents + memory)
python -c "from server.bridge import app; print('✓ bridge OK')"
```

**Key files to run tests**: Always validate `tests/test_canonical_*.py`, `tests/test_codex_*.py`, `tests/test_skill_registry.py`.

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────┐
│  Voice Input / Telegram / Dashboard         │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  Bridge (server/bridge.py)                  │
│  - Route to agents                          │
│  - Telegram command handlers                │
│  - Account redaction                        │
└────────┬─────────────┬──────────────────────┘
         │             │
    ┌────▼────┐   ┌────▼────────┐
    │  Agents  │   │  Skills     │
    │(canonical)  │ (registry)  │
    └────┬────┘   └────┬────────┘
         │             │
    ┌────▼────────────▼───────────┐
    │ Codex Slots                 │
    │ forge/nexus/spark/shield    │
    └────┬───────────────────────┘
         │
    ┌────▼────────────────────────┐
    │  Model Router               │
    │  Claude/OpenRouter/Ollama   │
    └─────────────────────────────┘

Memory: state/agent_memory/{agent_name}/
Logs:   server/logs/, state/logs/
Config: config/agents.yaml, config/persona_execution_map.json
```

---

## Where Things Live

| What | Where | Notes |
|------|-------|-------|
| **Agents** | `server/agents/canonical/` | 9 canonical agents, lazy-loaded |
| **Skills** | `server/skills/` | AWS EC2, S3, Cost; Cloud; Telegram handlers |
| **Bridge** | `server/bridge.py` | Central router, API endpoints |
| **Codex** | `server/codex_*.py` | Job manager, orchestrator, workspace, task router, auth |
| **Memory** | `state/agent_memory/{name}/` | Per-agent persistent state (JSON) |
| **Config** | `config/` | agents.yaml, persona_execution_map.json |
| **Tests** | `tests/test_*.py` | Pytest suite; run all before commit |
| **Docs** | [AGENTS.md](../../AGENTS.md), [CLAUDE.md](../../CLAUDE.md) | Agent registry, tech stack, sprints |
| **Handoffs** | `OPS/` | 200-209 audit/rollout, 300-308 agents, 408 cloud |

---

## Key Principles

### 1. **Agent Development**
- Inherit from `RuntimeAgent` class
- Implement `execute_task(self, task: dict) -> str` — main entry point
- Set `name`, `description`, `model_chain`, `risk_level` attributes
- Use `self.remember(data)` and `self.recall()` for state persistence
- Always validate input with `_validate_input()`
- Catch exceptions specifically (not bare `except`)
- Return JSON for structured output

**Model chains**: 
- `reasoning` = planning, analysis (Opus)
- `code` = repos, reviews, implementations (Sonnet)
- `chat` = user interaction, summaries (MiniMax/Step)
- `default` = general, fallbacks (Qwen/DeepSeek)

### 2. **Skill Registry**
- Skills live in `server/skills/` with `registry_entries/` for bridge routes
- Register in `server/skill_registry.py`
- Add Telegram command handlers if user-facing
- Include in `/help` command output

### 3. **Bridge Integration**
- All public endpoints in `server/bridge.py`
- Use `account_manager.py` to redact operator payloads
- Follow `/api/agents/{name}` or `/agent/{command}` URL patterns
- Telegram: prefix with `/` (e.g., `/codex-durum`)

### 4. **Testing**
- **Every agent/skill** needs `tests/test_{name}.py`
- Cover: happy path, error cases, state persistence
- Use fixtures from existing tests (e.g., `test_account_manager.py`)
- Target 80%+ coverage
- Run: `pytest tests/test_{name}.py -v --tb=short`

### 5. **State Management**
- Write to `state/agent_memory/{agent_name}/` (JSON only, never pickle)
- Use `state/codex_cooldowns.json` for dispatch cooldowns
- Audit logs: `state/logs/codex_dispatch_audit.jsonl`
- Never commit credentials — use `.env` and `os.getenv()`

### 6. **Codex Slots & Personas**
- **7 personas**: Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri
- **5 execution slots**: forge (Seda), nexus (Mert), spark (Buse), shield (Eren), atlas (Sabri)
- Persona → slot mapping in `config/persona_execution_map.json`
- Active persona stored in `state/active_agent.json`
- Per-persona memory in `server/agents/clones/{ajan}/memory/`

---

## Common Workflows

### Add a New Agent

1. Create `server/agents/canonical/{agent_name}.py`:
   ```python
   from server.agents.runtime_agent import RuntimeAgent
   
   class MyAgent(RuntimeAgent):
       name = "my_agent"
       description = "..."
       model_chain = "reasoning"  # or code/chat/default
       risk_level = "low"  # or medium/high
       
       def execute_task(self, task: dict) -> str:
           if not self._validate_input(task):
               return json.dumps({"error": "..."})
           # your logic
           return json.dumps({"result": "..."})
   ```

2. Register in `server/agents/registry.py`: add to `_RUNTIME_AGENTS` dict
3. Create test: `tests/test_my_agent.py`
4. Add config entry to `config/agents.yaml`
5. Update [AGENTS.md](../../AGENTS.md) agent table
6. Run tests: `pytest tests/test_my_agent.py -v --tb=short`

### Add a New Skill

1. Create `server/skills/my_skill.py` (inherit from `BaseSkill`)
2. Create `server/skills/registry_entries/my_entries.py` (bridge routes)
3. Register in `server/skill_registry.py`
4. Add Telegram handlers if needed (in bridge route)
5. Create test: `tests/test_my_skill.py`
6. Update [CLAUDE.md](../../CLAUDE.md) handoff section
7. Run: `pytest tests/test_my_skill.py -v --tb=short`

### Deploy Bridge Changes

1. Edit `server/bridge.py` or skills
2. Run lint: `ruff check server/bridge.py --fix`
3. Create/update tests
4. Validate: `pytest tests/test_bridge_*.py -v --tb=short`
5. Check canary: POST to `/health` → expect `{"status": "ok"}`

### Add Telegram Command

1. Create handler in `server/skills/registry_entries/` or `server/bridge.py`
2. Add route to bridge: `@app.post("/telegram")`
3. Extract command keyword, dispatch to agent/skill
4. Return plain text (not JSON) for TTS
5. Test with: `pytest tests/test_canonical_telegram.py -v --tb=short`

---

## Testing Strategy

**Before committing any code**:
```bash
# Run full test suite
pytest tests/ -v --tb=short

# Or targeted:
pytest tests/test_bridge_endpoints.py tests/test_skill_registry.py -v --tb=short

# Lint
ruff check . --fix
```

**Critical test files** (must pass):
- `test_canonical_batch1.py`, `test_canonical_batch2.py`, `test_canonical_batch3.py`, `test_canonical_batch4.py`
- `test_codex_management.py`, `test_codex_orchestrator.py`, `test_codex_job_manager.py`
- `test_skill_registry.py`, `test_bridge_endpoints.py`

---

## Troubleshooting

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| Agent not loading | Check `server/agents/registry.py` registration | Add class to `_RUNTIME_AGENTS` dict |
| Bridge endpoint 404 | Verify route exists in `server/bridge.py` | Check `@app.post()` decorator and function name |
| State not persisting | Memory dir not created | Ensure `state/agent_memory/{name}/` exists; use `mkdir(parents=True)` |
| Telegram command fails | Handler not wired | Check `/telegram` route in bridge; verify keyword routing |
| Test import error | Module not in path | Run from root: `pytest tests/test_x.py` |
| OpenRouter timeout | Rate limit or model unavailable | Check `OPENROUTER_API_KEY` in `.env`; fallback to `default` chain |

---

## Documentation Roadmap

- [AGENTS.md](../../AGENTS.md) — Agent registry, model chains, autonomy policy
- [CLAUDE.md](../../CLAUDE.md) — Tech stack, recent changes, sprint status
- [OPS/209_MULTI_CODEX_HANDOFF.md](../../OPS/209_MULTI_CODEX_HANDOFF.md) — Slot architecture, Telegram commands, API table
- [OPS/408_CLOUDMANAGER_HANDOFF.md](../../OPS/408_CLOUDMANAGER_HANDOFF.md) — Cloud skills, EC2/S3/cost commands
- [.github/prompts/jarvis-agent-generator.prompt.md](.github/prompts/jarvis-agent-generator.prompt.md) — Agent/skill code generation template

---

## Quick Links

- **GitHub Repo**: This workspace
- **Model Router**: `server/model_router.py`
- **Skill Registry**: `server/skill_registry.py`
- **Bridge Source**: `server/bridge.py`
- **Codex Orchestrator**: `server/codex_orchestrator.py`

---

**Questions?** Check OPS/ handoff docs or existing test files for patterns.
