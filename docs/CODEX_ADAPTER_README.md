# CODEX Code Adapter - Project Index

**Project Name:** CODEX Code Adapter  
**Objective:** Adapt Claude Code (leaked TypeScript) modules to Jarvis API (Python)  
**Status:** Planning Phase Complete  
**Date Created:** 2026-04-04  

---

## Quick Start

Read these documents in order:

1. **CODEX_ADAPTER_STRATEGY.md** — Complete strategy with top 20 modules, 3 sample adapters
2. **CODEX_MIGRATION_CHECKLIST.md** — Detailed task breakdown by phase
3. **This file** — Index and navigation

---

## Overview: What is CODEX?

On March 31, 2026, the full source code of Anthropic's Claude Code CLI was leaked. The codebase contains:

- **1,900+ TypeScript files**
- **512,000+ lines of code**
- **Proven patterns for:** tool execution, agent orchestration, permission gating, state management

**Value for Jarvis:** Extract battle-tested algorithms and patterns without rewriting from scratch.

---

## Documents Created

### 1. CODEX_ADAPTER_STRATEGY.md (Main Strategy)

**Length:** 50+ pages  
**Purpose:** Complete analysis and planning document  

**Sections:**
- Executive Summary
- Part 1: Top 20 High-Value Modules (5 categories)
- Part 2: Adaptation Strategy (import refactoring, function wrapping, class subclassing)
- Part 3: Migration Checklist (Phase 1/2/3 breakdown)
- Part 4: Sample Adapter Implementations (3 working examples)
- Part 5: Integration Points with Jarvis

**Key Content:**
- Table of 20 modules by value/complexity
- Architecture diagram (Claude Code → Jarvis mapping)
- Strategy for each file type (copy, adapt, reference)
- 3 complete adapter implementations in pseudocode
- Integration hooks for `server/bridge.py`

**How to Use:**
- Start with executive summary for high-level overview
- Review Part 1 table to understand module priority
- Study Part 4 sample adapters for concrete patterns
- Use Part 5 to understand integration points

---

### 2. CODEX_MIGRATION_CHECKLIST.md (Implementation Tasks)

**Length:** 30+ pages  
**Purpose:** Actionable task breakdown by phase  

**Phases:**
1. **Phase 1 (Foundation):** Type definitions & schemas (5-10 hours)
2. **Phase 2 (Core Logic):** Tool system & execution (20-30 hours)
3. **Phase 3 (Reference):** Documentation & analysis (5-10 hours)
4. **Validation:** Unit/integration tests (10-15 hours)
5. **Deployment:** Rollout & monitoring (5-10 hours)

**Each Task Includes:**
- File mapping (src/ → server/)
- Detailed subtasks (checkboxes)
- Validation criteria
- Effort estimate

**How to Use:**
- Copy all checkboxes into your project tracker
- Follow phase order for minimal risk
- Use effort estimates for sprint planning
- Follow validation criteria to know when done

---

### 3. CODEX_ADAPTER_README.md (This File)

**Purpose:** Navigation and reference  

**Sections:**
- Document index
- Quick links to each file
- Key patterns explained
- FAQ and risks
- Next steps

---

## Key Concepts

### The 5 Categories (Top 20 Modules)

| Category | Purpose | Examples | Priority |
|----------|---------|----------|----------|
| **A: Core Engine** | Tool execution orchestration | QueryEngine, Tool system, Bash/File tools | MUST |
| **B: State & Permissions** | Session & access control | AppState, permissions, task lifecycle | SHOULD |
| **C: Routing & Orchestration** | Multi-agent coordination | Coordinator, model routing | SHOULD |
| **D: Error & Observability** | Error handling, metrics | Error classification, cost tracking | MUST |
| **E: Context & Config** | Configuration management | System context, config schema | REFERENCE |

### The 3 Adaptation Strategies

| Strategy | Use Case | Example |
|----------|----------|---------|
| **Copy (Minimal Changes)** | Type definitions, configs | `permissions.ts` → `permissions.py` |
| **Adapt (Significant Changes)** | Core algorithms, ported logic | `QueryEngine.ts` → tool_executor.py |
| **Reference (Documentation)** | High-level patterns | `coordinator/` → Design docs + recommendations |

### The 3 Sample Adapters

1. **Tool Base Class Wrapper** (`adapter_claude_tool_base.py`)
   - Shows how to create base class for all tools
   - Demonstrates permission hook integration
   - Includes progress callback pattern

2. **Agent Tool Wrapper** (`adapter_agent_tool.py`)
   - Shows how to spawn sub-agents
   - Demonstrates capability scoping
   - Includes timeout/resource enforcement

3. **Permission Gate Wrapper** (`adapter_permission_gate.py`)
   - Shows how to gate access to tools
   - Demonstrates permission modes (ALLOW/DENY/ASK/QUARANTINE)
   - Includes denial tracking pattern

---

## Implementation Approach

### DO ✓

- Study Claude Code patterns before adapting
- Create adapters as wrappers (don't modify original logic)
- Use existing Jarvis structures (`server/bridge.py`, agent system)
- Test each phase independently
- Document integration points clearly
- Get team review before production

### DON'T ✗

- Copy code directly without refactoring for Python idioms
- Modify Claude Code repo (only read/study)
- Change existing `server/` runtime structure
- Skip testing phases
- Deploy without feature flag and rollback plan

---

## Integration Checklist

Before implementing, ensure:

- [ ] Claude Code repo available locally for reference
- [ ] Jarvis server structure understood (`server/bridge.py`, agents/)
- [ ] Team agrees on scope (all 20 modules? Top 10?)
- [ ] Effort estimates accepted (45-75 hours total)
- [ ] Testing infrastructure in place (`pytest`)
- [ ] Deployment process documented

---

## Timeline

| Phase | Week | Hours | Output |
|-------|------|-------|--------|
| Foundation | 1 | 5-10 | Type definitions, schemas |
| Core Logic | 2-3 | 20-30 | Tool executor, agent system, permissions |
| Reference | 3 | 5-10 | Architecture docs, recommendations |
| Testing | 4 | 10-15 | Unit/integration/smoke tests |
| Deployment | 4 | 5-10 | Feature flag, monitoring, rollout |

**Total:** 4 weeks, 45-75 person-hours

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Type incompatibilities | Medium | Medium | Extensive Pydantic validation |
| Permission model drift | Low | Medium | Centralized permission logic, tests |
| State persistence bugs | Low | High | Use existing session storage, test thoroughly |
| Performance regression | Low | Medium | Benchmarks, performance tests |
| Tool naming conflicts | Very Low | Low | Prefix adapters (`claude_`) |

---

## FAQ

### Q: Why adapt Claude Code instead of using it directly?

**A:** Claude Code is TypeScript/Bun. Jarvis is Python. We adapt patterns, not code.

### Q: Will this break existing Jarvis functionality?

**A:** No. Adapters are wrappers. Original code unchanged. Use feature flag for safety.

### Q: How much code needs to be rewritten?

**A:** ~40-50% translated, ~30% reimplemented for Python, ~20% referenced (docs only).

### Q: Should we adapt all 20 modules?

**A:** Recommend starting with top 10 (Categories A & B). Categories C-E can follow later.

### Q: What if something doesn't work?

**A:** Feature flag lets you disable adapters. Rollback plan: revert to old tool system.

### Q: How do we ensure quality?

**A:** Unit tests (80%+ coverage), integration tests, smoke tests, canary deployment.

---

## Key Files & Locations

### Strategy Documents (Already Created)

```
docs/
├── CODEX_ADAPTER_STRATEGY.md          ← Main strategy (50+ pages)
├── CODEX_MIGRATION_CHECKLIST.md       ← Task breakdown (30+ pages)
└── CODEX_ADAPTER_README.md            ← This file
```

### Implementation Files (To Be Created)

```
server/
├── types/
│   ├── permissions.py                 ← From src/types/permissions.ts
│   ├── tool_schema.py                 ← From src/Tool.ts
│   ├── tool_progress.py               ← From src/types/tools.ts
│   ├── messages.py                    ← From src/types/message.ts
│   └── ... (15+ other type files)
│
├── tools/
│   ├── adapter_claude_tool_base.py    ← Adapter 1: Tool base
│   ├── adapter_agent_tool.py          ← Adapter 2: Agent tool
│   ├── adapter_permission_gate.py     ← Adapter 3: Permission gate
│   ├── bash_tool.py                   ← Adapted from BashTool
│   ├── file_tools.py                  ← Adapted from File*Tool
│   └── ... (10+ other tool files)
│
├── api/
│   ├── error_classifier.py            ← From src/services/api/errors.ts
│   └── tool_executor.py               ← Main execution engine
│
├── agents/
│   ├── agent_spawner.py               ← Uses AgentToolAdapter
│   └── permission_evaluator.py        ← Uses PermissionGateAdapter
│
└── tests/
    ├── unit/                          ← Unit tests
    ├── integration/                   ← Integration tests
    └── smoke/                         ← Bridge.py smoke tests
```

---

## How to Use These Documents

### For Project Managers
1. Read this file
2. Review CODEX_ADAPTER_STRATEGY.md executive summary
3. Use CODEX_MIGRATION_CHECKLIST.md timeline to plan sprints
4. Copy checklists into your project tracker

### For Engineers (Starting Implementation)
1. Read CODEX_ADAPTER_STRATEGY.md Part 1 (top 20 modules)
2. Study Part 4 (3 sample adapters) for concrete patterns
3. Follow CODEX_MIGRATION_CHECKLIST.md Phase 1 tasks
4. Reference Part 5 when integrating with Jarvis

### For Architects
1. Review CODEX_ADAPTER_STRATEGY.md Part 2 (adaptation strategy)
2. Study integration points (Part 5)
3. Review Phase 3 reference docs for architectural alignment
4. Approve before implementation begins

### For Team Lead
1. Share this README with team
2. Review timeline and risk assessment
3. Confirm scope (all 20 modules? Phase 1 only?)
4. Schedule architecture review meeting

---

## Success Metrics

By end of implementation, you'll have:

- [ ] **20 modules analyzed** with value/complexity scoring
- [ ] **3 sample adapters** demonstrating concrete patterns
- [ ] **Migration checklist** with 80+ actionable tasks
- [ ] **Unit tests** (80%+ coverage) for all adapters
- [ ] **Integration tests** validating end-to-end tool execution
- [ ] **Smoke tests** confirming server/bridge.py compatibility
- [ ] **Performance baseline** (<500ms p50 tool latency)
- [ ] **Documentation** updated for new adapters
- [ ] **Team trained** on new adapter usage
- [ ] **Feature flag** for gradual rollout

---

## Contact & Questions

**For clarification on:**
- **Strategy & scope** → Review CODEX_ADAPTER_STRATEGY.md Part 1
- **Implementation tasks** → Review CODEX_MIGRATION_CHECKLIST.md
- **Sample code patterns** → Review CODEX_ADAPTER_STRATEGY.md Part 4
- **Integration details** → Review CODEX_ADAPTER_STRATEGY.md Part 5

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-04-04 | Initial strategy, migration checklist, 3 sample adapters |

---

## Appendix: Module Reference

### Quick Lookup by Name

**Tool System**
- `Tool.ts` → Part 1, Category A #1 → Part 4, Adapter 1
- `tools.ts` → Part 1, Category A #1 → Part 2, Strategy
- `QueryEngine.ts` → Part 1, Category A #2 → Part 2, Integration

**Agent Framework**
- `src/tools/AgentTool/` → Part 1, Category A #3 → Part 4, Adapter 2
- `AgentTool/index.ts` → Part 1, Category A #3 → Part 4, Adapter 2

**Permissions**
- `src/types/permissions.ts` → Part 1, Category B #6 → Part 4, Adapter 3
- `src/utils/permissions/` → Part 1, Category B #6 → Part 4, Adapter 3

**Execution Tools**
- `BashTool/` → Part 1, Category A #4 → Part 2, Strategy
- `File*Tool/` → Part 1, Category A #5 → Part 2, Strategy

**State & Memory**
- `AppState.ts` → Part 1, Category B #8 → Migration Checklist, Phase 2
- `memdir/` → Part 1, Category B #9 → Migration Checklist, Phase 2

**Routing**
- `coordinator/` → Part 1, Category C #10 → Phase 3 (Reference)
- `model/` → Part 1, Category C #11 → Phase 3 (Reference)

**Error Handling**
- `src/services/api/errors.ts` → Part 1, Category D #14 → Migration Checklist, Phase 2
- `cost-tracker.ts` → Part 1, Category D #15 → Migration Checklist, Phase 2

---

**Next Step:** Open CODEX_ADAPTER_STRATEGY.md to begin detailed planning.

---

**Document Version:** 1.0  
**Status:** Ready for Team Review  
**Last Updated:** 2026-04-04  
**Total Pages Generated:** 80+  
**Scope:** Planning & Design Phase (No Code Changes)
