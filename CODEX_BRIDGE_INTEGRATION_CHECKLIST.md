# CODEX Bridge Integration - Implementation Checklist

**Status:** PLANNING (2026-04-04)  
**Target Completion:** Wave 2 integration (after Wave 1 parallel tasks)  
**Owner:** Ekrem (Jarvis Project)

---

## Phase 1: Core Claude Code Integration (Weeks 1-2)

### Analysis & Design
- [x] Analyze bridge.py structure (command handlers, routing, tools)
- [x] Design extension architecture (registry pattern)
- [x] Document integration plan (CODEX_BRIDGE_INTEGRATION.md)
- [x] Create extension template (bridge_extensions_template.py)
- [x] Design extension interface (custom_skill.py pattern)

### Core Framework Implementation
- [ ] Create `bridge_extensions.py` (production version from template)
- [ ] Create `extensions/` directory
- [ ] Create `extensions/__init__.py` (30 lines)
- [ ] Move template → `extensions/custom_skill.py` (documentation)
- [ ] Copy `bridge_extensions_template.py` → `bridge_extensions.py` (actual registry)

### Phase 1 Extensions
- [ ] Create `extensions/core.py` (150 lines)
  - [ ] `/claude [task]` — Call Claude Code CLI
  - [ ] `/agent-spawn [type]` — Create specialist agent
  - [ ] `/task [title]` — Add to task bus
  - [ ] `/codex-status` — Check companion status
  - [ ] Error handling & fallback

- [ ] Create `extensions/toolwrap.py` (200 lines)
  - [ ] FileRead wrapper (read, write, grep)
  - [ ] BashExec wrapper (timeout, safe mode)
  - [ ] Fallback-to-LLM logic for both
  - [ ] Error handling

### Bridge Integration
- [ ] Modify `bridge_current.py`:
  - [ ] Import ExtensionRegistry (1 line)
  - [ ] Create registry instance (1 line)
  - [ ] Call `registry.load_extensions("extensions/")` (1 line)
  - [ ] In `handle_command()`: Check registry before legacy fallback (3 lines)
  - [ ] Update `/help` to include extension commands (2 lines)

### Documentation
- [ ] Create `docs/EXTENSIONS.md`:
  - [ ] How to create an extension
  - [ ] Command registration pattern
  - [ ] Tool wrapper pattern
  - [ ] Agent registration pattern
  - [ ] Examples (eBay, voice, etc.)

- [ ] Create `docs/API.md`:
  - [ ] ExtensionRegistry API reference
  - [ ] Tool execution flow
  - [ ] Error handling guide

- [ ] Create `docs/EXAMPLES.md`:
  - [ ] Example 1: Simple command extension
  - [ ] Example 2: Tool wrapper extension
  - [ ] Example 3: Agent extension

### Testing
- [ ] Smoke test: Bridge loads without errors
  - [ ] `python3 bridge_current.py` starts
  - [ ] Extensions loaded: X extensions found
  - [ ] No import errors in startup logs

- [ ] Command tests:
  - [ ] `/claude "hello"` → Claude Code result (or timeout graceful fail)
  - [ ] `/agent-spawn backend` → Agent created (or error message)
  - [ ] `/task "test task"` → Task added (or error)
  - [ ] `/codex-status` → Status returned (or fallback)

- [ ] Backward compatibility:
  - [ ] `/help` works, shows both old + new commands
  - [ ] `/status` works (system status)
  - [ ] `/models` works (list models)
  - [ ] `/code "test"` works (still routes to Ollama)
  - [ ] `/plan "test"` works (still routes to Ollama)

- [ ] Fallback tests:
  - [ ] Tool fails → LLM fallback activates
  - [ ] Command missing → Unknown command message
  - [ ] Extension missing dep → Skipped gracefully

### Phase 1 Completion Criteria
- [x] Bridge structure fully analyzed
- [ ] Extension framework implemented (bridge_extensions.py)
- [ ] Phase 1 extensions working (core.py, toolwrap.py)
- [ ] Bridge integration minimal & safe (<10 LOC changes)
- [ ] All smoke tests passing
- [ ] Documentation complete (EXTENSIONS.md, API.md)
- [ ] No regression in existing commands
- [ ] Ready for Phase 2

---

## Phase 2: Advanced Features (Week 3-4)

### Specialist Agents
- [ ] Create agent definitions in `extensions/agents.py`:
  - [ ] backend agent (engineering specialist)
  - [ ] security agent (audit/threat analysis)
  - [ ] voice agent (audio processing)
  - [ ] swarm agent (planning/orchestration)

- [ ] Implement agent spawning:
  - [ ] `registry.spawn_agent(agent_type)` method
  - [ ] Agent state tracking (in-memory or Redis)
  - [ ] Task bus integration
  - [ ] Result streaming to Telegram

### Route Extensions
- [ ] Create routes in `extensions/routes.py`:
  - [ ] `code-review` route (Opus model, quality focus)
  - [ ] `architecture` route (system design specialist)
  - [ ] `security-audit` route (threat analysis)
  - [ ] `voice-assistant` route (audio processing)

- [ ] Keyword-based routing:
  - [ ] Update `detect_route()` to check CLAUDE_ROUTES
  - [ ] Fallback to MODEL_ROUTES if no match
  - [ ] Logging of selected route

### Tool Integration
- [ ] Enhanced FileRead tool:
  - [ ] Read (native)
  - [ ] Write (native)
  - [ ] Search/grep (fallback-friendly)
  - [ ] List directory (fallback-friendly)

- [ ] Enhanced BashExec tool:
  - [ ] Safe command allowlist (git, grep, ls, etc.)
  - [ ] Timeout enforcement (10s default)
  - [ ] Output size limits
  - [ ] Fallback for denied commands

- [ ] Git tool wrapper:
  - [ ] Read-only operations (status, diff, log)
  - [ ] Safe (no push/force operations)

### Commands
- [ ] `/list-agents` — Show available agent types
- [ ] `/agent-spawn [type]` — Already in Phase 1, enhance
- [ ] `/code-review [file]` — Code review via Claude
- [ ] `/design [component]` — Architecture design assistant
- [ ] `/audit [path]` — Security audit specialist
- [ ] `/voice-process [file]` — Voice/audio processing

### Testing
- [ ] Agent spawning:
  - [ ] 4+ agents spawning successfully
  - [ ] Agent state tracking working
  - [ ] Task bus integration confirmed

- [ ] Routes:
  - [ ] Code review detects issues
  - [ ] Architecture suggests improvements
  - [ ] Security audit finds vulnerabilities

- [ ] Tool access:
  - [ ] Tools accessible to agents
  - [ ] Fallback activates on error
  - [ ] No security bypasses

- [ ] Performance:
  - [ ] Agent spawn time < 2s
  - [ ] Tool execution < 5s
  - [ ] Results stream within 2s
  - [ ] No Telegram throughput regression

### Phase 2 Completion Criteria
- [ ] 4+ specialist agents operational
- [ ] 3+ new routes with Claude models
- [ ] Tool wrappers secure & tested
- [ ] Agent-to-Telegram streaming working
- [ ] Zero performance regression
- [ ] All Phase 2 tests passing
- [ ] Documentation updated

---

## Phase 3: Full Integration (Future - Post Wave 1)

### MCP Servers
- [ ] Supabase MCP wrapper
- [ ] GitHub MCP wrapper
- [ ] Stripe MCP wrapper
- [ ] OpenAI/Anthropic API wrapper

### Advanced Memory
- [ ] RAG from knowledge base
- [ ] Persistent agent memory
- [ ] Long-term task tracking
- [ ] Knowledge graph integration

### Long-Running Workflows
- [ ] Workflow definition language
- [ ] State machine for workflows
- [ ] Resume capability
- [ ] Error recovery

### Webhooks
- [ ] GitHub webhook handlers
- [ ] CI/CD pipeline triggers
- [ ] Event-driven agent spawning
- [ ] Result callbacks

### Dashboard & UI
- [ ] Agent management UI
- [ ] Workflow visualization
- [ ] Metrics dashboard
- [ ] Agent logs viewer

### Observability
- [ ] Agent throughput metrics
- [ ] Token usage tracking
- [ ] Latency p50/p99
- [ ] Cost analysis

---

## Critical Success Factors

### Architecture
- [x] Minimal core changes (extensibility via plugin)
- [ ] Fast command lookup (dict-based, O(1))
- [ ] Safe tool execution (sandboxed, timeouts)
- [ ] Memory-efficient (registry ~100KB per 50 extensions)

### Safety & Security
- [ ] No eval() or arbitrary code execution
- [ ] File operations limited by OS permissions
- [ ] Command allowlisting for system commands
- [ ] Tool execution audit logging

### Performance
- [ ] Command routing: < 1ms
- [ ] Tool execution: < 5s timeout
- [ ] Agent spawn: < 2s
- [ ] Telegram latency: no regression
- [ ] Memory usage: no unbounded growth

### Reliability
- [ ] Graceful degradation (fallback to Ollama)
- [ ] Error handling in all paths
- [ ] Extension load failures don't crash bridge
- [ ] Memory persistence (JSON + optional SQLite)

### Maintainability
- [ ] Code in separate files (not monolithic)
- [ ] Clear interfaces (Extension, ToolWrapper base classes)
- [ ] Comprehensive documentation
- [ ] Example extensions provided

---

## Risk Mitigations

| Risk | Impact | Mitigation | Status |
|------|--------|-----------|--------|
| Command name collision | Medium | Namespace prefixes + registry validation | Planned |
| Untrusted tool execution | High | Allowlists + timeouts + logging | Planned |
| Performance degradation | High | Caching + async agents | Planned |
| Memory unbounded growth | Medium | Registry cleanup + limits | Planned |
| Backward compatibility break | Critical | Phase 1 leaves legacy untouched | Ready |
| Extension load failure | Low | Try/except + logging + skips | Planned |

---

## File Structure

```
jarvis-mission-control/
├── bridge_current.py [MODIFY: +10 LOC for registry]
├── bridge_extensions.py [CREATE: production registry]
├── docs/
│   ├── CODEX_BRIDGE_INTEGRATION.md [CREATED: design doc]
│   ├── EXTENSIONS.md [CREATE: how-to guide]
│   └── API.md [CREATE: API reference]
├── extensions/ [CREATE: directory]
│   ├── __init__.py [CREATE: 30 LOC]
│   ├── custom_skill.py [CREATE: template]
│   ├── core.py [CREATE: Phase 1 core]
│   ├── toolwrap.py [CREATE: Phase 1 wrappers]
│   ├── agents.py [CREATE: Phase 2 agents]
│   └── routes.py [CREATE: Phase 2 routes]
└── examples/ [CREATE: directory]
    ├── extension_ebay.py [CREATE: reference]
    └── extension_voice.py [CREATE: reference]
```

---

## Schedule

| Phase | Duration | Start | End | Status |
|-------|----------|-------|-----|--------|
| Analysis | 2h | Now | Today | DONE |
| Phase 1 | 2 weeks | After Wave 1 | Week 2 | PLANNED |
| Phase 2 | 2 weeks | Week 3 | Week 4 | QUEUED |
| Phase 3 | Future | After Wave 2 | TBD | BACKLOG |

**Wave 1 Parallel Tasks:** Security, throughput, hologram, agents, docker (ongoing)  
**Bridge Integration:** Queued after Wave 1 completes

---

## Approval & Sign-Off

**Document Created:** 2026-04-04  
**Last Updated:** 2026-04-04  
**Status:** PLANNING (Ready for Phase 1 implementation)  
**Approval Required:** Yes (before Phase 1 code)  
**Owner:** Ekrem  
**Reviewer:** Claude Code

---

## Notes

1. **No Code Changes Yet:** This checklist documents planning only. bridge.py and extensions are NOT yet modified.

2. **Isolated Development:** Phase 1 extensions live in separate files. Core bridge.py changed by only ~10 lines.

3. **Backward Compatible:** All existing commands (`/ebay`, `/code`, `/plan`, etc.) continue working unchanged.

4. **Gradual Rollout:** Phase 1 adds new commands. Phase 2 upgrades with routes/agents. Phase 3 extends ecosystem.

5. **Dependencies:** Phase 1 has no new dependencies. Phase 2+ may require Claude Code SDK, MCP libraries, etc.

6. **Testing Strategy:** Smoke tests first (no errors), then functional tests (commands work), then regression (old commands still work).

---

## Appendix: Example Phase 1 Addition

**After Phase 1 completion, usage:**

```bash
# Telegram user sends:
/claude "Fix the TypeError in my code"

# Bridge logs:
[INFO] Loaded extension: core v1.0
[INFO] Registered command: /claude
[INFO] Executing command: /claude with args "Fix the TypeError in my code"

# Telegram receives:
[Claude] Here's the fix for your TypeError...
```

**Example Phase 2 usage:**

```bash
# Telegram user sends:
/agent-spawn backend
/code-review myfile.py

# Bridge:
[INFO] Spawned agent: backend (task_id: abc123)
[INFO] Agent executing code-review on myfile.py
[INFO] Route: code-review (model: claude-opus)

# Telegram receives:
✅ Agent spawned. Results incoming...
🔍 **Code Review: myfile.py**
- Issue 1: N+1 query on line 42
- Issue 2: Missing error handling on line 18
...
```

