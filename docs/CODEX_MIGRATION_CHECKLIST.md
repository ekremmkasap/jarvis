# CODEX Code Adapter - Migration Checklist

**Status:** Planning Document  
**Version:** 1.0  
**Date:** 2026-04-04  

---

## Phase 1: Foundation (Type Definitions & Schemas)
**Estimated Effort:** 5-10 hours  
**Risk Level:** Low  
**Files to Copy/Adapt:** 20+ type definition files  

### Core Type Files

- [ ] **permissions.ts → permissions.py**
  - [ ] `src/types/permissions.ts` → `server/types/permissions.py`
  - [ ] Convert `PermissionMode` enum
  - [ ] Convert `PermissionResult` type
  - [ ] Convert `AdditionalWorkingDirectory` dataclass
  - [ ] Add type hints, validation
  - **Validation:** `pytest server/types/test_permissions.py`

- [ ] **tool_progress.ts → tool_progress.py**
  - [ ] `src/types/tools.ts` progress types → `server/types/tool_progress.py`
  - [ ] Implement `ToolProgressData` dataclass
  - [ ] Implement `BashProgress`, `MCPProgress`, etc.
  - **Validation:** Ensure all progress types have correct fields

- [ ] **messages.ts → messages.py**
  - [ ] `src/types/message.ts` → `server/types/messages.py`
  - [ ] Convert `Message`, `UserMessage`, `AssistantMessage` types
  - [ ] Convert tool-use block params
  - **Validation:** Validate message serialization

- [ ] **tool_schema.py**
  - [ ] `src/Tool.ts` schema definitions → `server/types/tool_schema.py`
  - [ ] Implement `ToolInputJSONSchema` dataclass
  - [ ] Add Pydantic validation
  - **Validation:** Test schema validation with sample inputs

### Error & Logging Types

- [ ] **error_classifier.py**
  - [ ] `src/services/api/errors.ts` → `server/api/error_classifier.py`
  - [ ] Implement `ErrorType` enum (Retryable, Fatal, etc.)
  - [ ] Implement categorization logic
  - **Validation:** Test with sample Anthropic API errors

- [ ] **cost_types.py**
  - [ ] `src/cost-tracker.ts` types → `server/types/cost_types.py`
  - [ ] Implement `ModelUsage`, `CostMetrics` dataclasses
  - **Validation:** Verify token counting logic

- [ ] **session_types.py**
  - [ ] `src/assistant/sessionHistory.ts` types → `server/types/session_types.py`
  - [ ] Implement `SessionRecord`, `TurnRecord` dataclasses
  - **Validation:** Test serialization/deserialization

### Utility Functions (Minimal Changes)

- [ ] **task.py**
  - [ ] `src/Task.ts` → `server/types/task.py`
  - [ ] Implement `Task` dataclass with lifecycle states
  - **Validation:** Verify state machine (queued → planning → running → done)

- [ ] **config_schema.py**
  - [ ] `src/schemas/` configs → `server/types/config_schema.py`
  - [ ] Use Pydantic for schema validation
  - **Validation:** Test with real Jarvis config

### Phase 1 Completion Checklist
- [ ] All type files compile (Python -m py_compile)
- [ ] All imports resolve correctly
- [ ] No circular dependencies
- [ ] Type hints complete for 90%+ of functions
- [ ] Unit tests written for all types
- [ ] Documentation added to each module

---

## Phase 2: Core Logic (Tool System & Execution)
**Estimated Effort:** 20-30 hours  
**Risk Level:** Medium  
**Files to Adapt/Create:** 30-40 files  

### Tool Base System

- [ ] **adapter_claude_tool_base.py**
  - [ ] Create base class `ClaudeToolAdapter` (from `src/Tool.ts`)
  - [ ] Implement schema validation
  - [ ] Implement permission checking hook
  - [ ] Add progress callback mechanism
  - [ ] Implement error handling
  - **Validation:** Unit test each method

- [ ] **tool_registry.py**
  - [ ] Create `ToolRegistry` class (from `src/tools.ts`)
  - [ ] Implement tool lookup by name
  - [ ] Implement tool validation on registration
  - **Validation:** Test registration/lookup of 5+ tools

### Tool Execution Engine

- [ ] **tool_executor.py** (core adaptation from `src/QueryEngine.ts`)
  - [ ] Create `ToolExecutionEngine` class
  - [ ] Implement `execute_tool_call()` method
  - [ ] Add permission gating
  - [ ] Add error categorization
  - [ ] Add retry logic (retryable vs. fatal)
  - [ ] Add progress streaming
  - **Validation:** Integration test with mock LLM

- [ ] **async_tool_runner.py**
  - [ ] Create async wrapper for tool execution
  - [ ] Implement timeout handling
  - [ ] Implement cancellation support
  - **Validation:** Test timeout enforcement

### Specialized Tools (Adapted from src/tools/)

- [ ] **bash_tool.py** (from `src/tools/BashTool/`)
  - [ ] Create `BashToolAdapter` class
  - [ ] Implement subprocess execution
  - [ ] Add timeout/signal handling
  - [ ] Add output capture (stdout/stderr)
  - [ ] Add working directory context
  - **Validation:** Execute 5+ shell commands, verify output

- [ ] **file_tools.py** (from `src/tools/File*Tool/`)
  - [ ] Create `FileReadToolAdapter`
  - [ ] Create `FileWriteToolAdapter`
  - [ ] Create `FileEditToolAdapter` (atomic edits)
  - [ ] Support multi-format reads (PDF, Jupyter, etc.)
  - [ ] Add file size limits
  - **Validation:** Read/write/edit test files

- [ ] **search_tools.py** (from `src/tools/Glob* & Grep*Tool/`)
  - [ ] Create `GlobToolAdapter`
  - [ ] Create `GrepToolAdapter`
  - [ ] Add ripgrep integration
  - [ ] Add result filtering
  - **Validation:** Search 1000+ file repos

### State & Memory

- [ ] **session_memory.py** (from `src/memdir/`)
  - [ ] Create `SessionMemory` class
  - [ ] Implement persistent storage (to `server/data/sessions/`)
  - [ ] Implement memory extraction logic
  - [ ] Implement recall/context retrieval
  - **Validation:** Test save/load cycle with 100+ sessions

- [ ] **session_state.py** (from `src/state/AppState.ts`)
  - [ ] Create `SessionState` dataclass
  - [ ] Store working directory, config, context
  - [ ] Implement serialization
  - **Validation:** Verify state persistence

### Permissions & Access Control

- [ ] **permission_gate.py** (from `src/utils/permissions/`)
  - [ ] Create `PermissionGate` class
  - [ ] Implement permission mode logic (ALLOW/DENY/ASK/QUARANTINE)
  - [ ] Implement denial tracking (cooldown)
  - [ ] Implement policy gates for sensitive operations
  - **Validation:** Test all permission modes

- [ ] **hook_system.py** (from `src/utils/hooks/`)
  - [ ] Create `HookManager` class
  - [ ] Implement pre-execution hooks (permission, logging)
  - [ ] Implement post-execution hooks (cleanup, metrics)
  - **Validation:** Test hook ordering and error handling

### Multi-Agent Integration

- [ ] **adapter_agent_tool.py** (from `src/tools/AgentTool/`)
  - [ ] Create `AgentToolAdapter` class
  - [ ] Implement agent spawning
  - [ ] Implement capability scoping
  - [ ] Implement timeout enforcement
  - [ ] Implement execution monitoring
  - **Validation:** Spawn 5+ test agents, verify isolation

- [ ] **agent_registry.py**
  - [ ] Load agent manifests (JSON/YAML)
  - [ ] Validate agent capabilities
  - [ ] Support agent versioning
  - **Validation:** Load 10+ agent definitions

### Error Handling & Retry Logic

- [ ] **error_handler.py**
  - [ ] Create `ErrorHandler` class
  - [ ] Implement error classification (from `error_classifier.py`)
  - [ ] Implement retry logic (exponential backoff)
  - [ ] Route fatal errors to `error_handler_agent.py`
  - **Validation:** Test retry on 5+ error types

- [ ] **cost_tracker.py** (from `src/cost-tracker.ts`)
  - [ ] Implement token counting per model
  - [ ] Track cumulative costs per session
  - [ ] Project burn rate
  - [ ] Alert on budget threshold
  - **Validation:** Verify cost calculations for 3+ models

### Phase 2 Completion Checklist
- [ ] All tool adapters pass unit tests (90%+ coverage)
- [ ] Integration tests pass (tool chain: permission → execute → result)
- [ ] Error handling tested (5+ error scenarios)
- [ ] Timeout handling tested (enforces limits)
- [ ] Memory/state persistence tested
- [ ] Permission gates tested (all modes)
- [ ] Agent spawning tested (multi-agent scenarios)
- [ ] Performance: tool execution <500ms p50
- [ ] Backward compatibility verified (existing `server/tools/` still work)

---

## Phase 3: Reference & Documentation
**Estimated Effort:** 5-10 hours  
**Risk Level:** Very Low  
**Output:** Architecture documents + pattern analysis  

### Orchestration Analysis

- [ ] **ORCHESTRATION_PATTERNS.md**
  - [ ] Document `src/coordinator/` patterns
  - [ ] Multi-agent coordination design
  - [ ] Task dispatch and monitoring
  - [ ] Fallback and retry strategies
  - **Output:** 5-10 page design document

### Model Routing Reference

- [ ] **MODEL_ROUTING_V2.md**
  - [ ] Analyze `src/utils/model/model.ts` patterns
  - [ ] Document selection criteria (cost, latency, capability)
  - [ ] Compare with existing `server/model_router.py`
  - [ ] Recommend v2 enhancements
  - **Output:** Enhancement proposal

### MCP Integration Planning

- [ ] **MCP_INTEGRATION_PLAN.md**
  - [ ] Analyze `src/services/mcp/`
  - [ ] Document MCP server lifecycle
  - [ ] Plan MCP integration with Jarvis
  - **Output:** Integration roadmap

### Skills System Analysis

- [ ] **SKILLS_SYSTEM_ANALYSIS.md**
  - [ ] Analyze `src/skills/` organization
  - [ ] Compare with Jarvis skill system
  - [ ] Recommend enhancements
  - **Output:** Improvement recommendations

### Phase 3 Completion Checklist
- [ ] 4 design documents written (each 5+ pages)
- [ ] Patterns documented with code examples
- [ ] Integration recommendations clear
- [ ] Team reviews and approves all recommendations

---

## Validation & Testing
**Estimated Effort:** 10-15 hours  
**Scope:** Cross-phase validation  

### Unit Tests

- [ ] **test_permissions.py** — All permission modes
- [ ] **test_tools.py** — All tool adapters
- [ ] **test_agent_tool.py** — Agent spawning scenarios
- [ ] **test_session_memory.py** — Memory persistence
- [ ] **test_error_handler.py** — Error classification & retry
- [ ] **Coverage target:** 80%+ for Phase 1 & 2 modules

### Integration Tests

- [ ] **test_tool_execution_chain.py**
  - [ ] Permission → Execute → Result full chain
  - [ ] 3+ sample tools (bash, file, search)
  - [ ] Verify correct error handling

- [ ] **test_agent_spawning_chain.py**
  - [ ] Spawn agent → Execute → Monitor → Complete
  - [ ] Test capability scoping
  - [ ] Test timeout enforcement

- [ ] **test_session_lifecycle.py**
  - [ ] Create session → Execute tools → Save/Load session
  - [ ] Verify state persistence
  - [ ] Verify cost tracking

### Smoke Tests (server/bridge.py integration)

- [ ] **Bridge accepts tool calls** from LLM
- [ ] **Tool executor routes correctly** to adapters
- [ ] **Permission gates enforce** before execution
- [ ] **Results flow back** to LLM context
- [ ] **Errors handled gracefully** (no crashes)

### Performance Tests

- [ ] **Tool latency:** <500ms p50 for simple tools
- [ ] **Agent spawn latency:** <2s for sub-agents
- [ ] **Memory usage:** <100MB per active session
- [ ] **Concurrency:** 5+ parallel tool calls

### Testing Checklist

- [ ] All unit tests pass (`pytest server/tests/unit/`)
- [ ] All integration tests pass (`pytest server/tests/integration/`)
- [ ] Smoke tests pass with real bridge.py
- [ ] Performance tests within targets
- [ ] No regressions in existing server functionality
- [ ] Code review approved by 2+ team members

---

## Deployment & Rollout
**Estimated Effort:** 5-10 hours  

### Pre-Deployment

- [ ] Create feature flag for adapters (off by default)
- [ ] Document migration instructions for team
- [ ] Create rollback plan (disable feature flag)

### Gradual Rollout

- [ ] **Day 1:** Enable adapters in dev environment only
- [ ] **Day 2:** Enable for 10% of sessions (canary)
- [ ] **Day 3:** Enable for 50% of sessions (if no errors)
- [ ] **Day 4:** Enable for 100% of sessions

### Monitoring

- [ ] **Metrics dashboard** for adapter usage
- [ ] **Error rate tracking** (target: <0.1%)
- [ ] **Latency monitoring** (track p50/p99)
- [ ] **Cost tracking** (verify accurate counting)

### Post-Deployment

- [ ] Monitor for 1 week
- [ ] Gather feedback from team
- [ ] Document lessons learned
- [ ] Plan Phase 2 enhancements

---

## Sign-Off Checklist

- [ ] Architecture review completed
- [ ] All phase tasks completed
- [ ] Testing targets met (80%+ coverage, <0.1% error rate)
- [ ] Documentation complete
- [ ] Team training completed
- [ ] Deployment plan approved
- [ ] Rollback plan tested

---

## Timeline Overview

| Milestone | Date | Effort | Status |
|-----------|------|--------|--------|
| Phase 1 Complete | Week 1 | 5-10h | — |
| Phase 2 Complete | Week 2-3 | 20-30h | — |
| Phase 3 Complete | Week 3 | 5-10h | — |
| Testing Complete | Week 4 | 10-15h | — |
| Production Deployment | Week 4 | 5-10h | — |
| **Total** | **4 weeks** | **45-75h** | — |

---

**Document Version:** 1.0  
**Status:** Ready for Team Review  
**Last Updated:** 2026-04-04
