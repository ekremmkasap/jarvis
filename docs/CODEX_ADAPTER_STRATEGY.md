# CODEX Code Adapter Strategy - Jarvis Mission Control

**Status:** Planning & Specification  
**Target:** Adapt Claude Code (TypeScript) modules to Jarvis API (Python)  
**Date:** 2026-04-04  
**Scope:** Top 20 high-value modules, 3 sample adapters, migration checklist

---

## Executive Summary

The Claude Code repository (leaked 2026-03-31) contains 1,900+ TypeScript files with proven patterns for:
- **Tool execution engines** with permission-based access control
- **Agent framework** with routing, spawning, and state management
- **Model routing logic** supporting multi-model orchestration
- **Error handling patterns** for fault tolerance and retries
- **State management** with persistent session tracking

This strategy identifies the **top 20% of modules** (by value-to-complexity ratio) and prepares them for integration into Jarvis' Python-based API without modifying existing runtime structures.

---

## Part 1: Top 20 High-Value Modules (20% Analysis)

### Category A: Core Engine (Must Adapt)

| # | Module | Location | Purpose | Value | Complexity |
|---|--------|----------|---------|-------|-----------|
| 1 | **Tool System** | `src/Tool.ts` + `src/tools.ts` | Base type definitions, tool registry, schema validation | ★★★★★ | Medium |
| 2 | **Tool Execution Pipeline** | `src/QueryEngine.ts` | Orchestrates LLM -> Tool -> Result loops, handles retries | ★★★★★ | High |
| 3 | **Agent Tool Framework** | `src/tools/AgentTool/` | Sub-agent spawning, scoping, capability restrictions | ★★★★★ | High |
| 4 | **Bash Execution Engine** | `src/tools/BashTool/` | Shell command execution with timeout/sandbox support | ★★★★ | Medium |
| 5 | **File Operations Suite** | `src/tools/File{Read,Write,Edit}Tool/` | Atomic file ops, diff-based edits, multi-format support (PDF, notebook) | ★★★★ | Medium |

### Category B: State & Permissions (Should Adapt)

| # | Module | Location | Purpose | Value | Complexity |
|---|--------|----------|---------|-------|-----------|
| 6 | **Permission System** | `src/types/permissions.js`, `src/utils/permissions/` | Capability-based access control, denial tracking, policy gates | ★★★★ | Medium |
| 7 | **Task Management** | `src/tasks/`, `src/Task.ts` | Task lifecycle, execution tracking, resource cleanup | ★★★★ | Medium |
| 8 | **AppState Manager** | `src/state/AppState.ts` | Session persistence, config state, working directory tracking | ★★★ | Low |
| 9 | **Memory System** | `src/memdir/`, `src/services/SessionMemory/` | Persistent session memory, knowledge extraction, recall | ★★★★ | High |

### Category C: Routing & Orchestration (Reference + Adapt)

| # | Module | Location | Purpose | Value | Complexity |
|---|--------|----------|---------|-------|-----------|
| 10 | **Multi-Agent Coordinator** | `src/coordinator/` | Routes tasks across specialized agents, waits for completion | ★★★★ | High |
| 11 | **Model Routing** | `src/utils/model/model.ts`, `src/query.ts` | Selects model by cost/speed/capability, handles fallbacks | ★★★★ | Medium |
| 12 | **Query Pipeline** | `src/query.ts` | Batches messages, manages context windows, streaming output | ★★★ | Medium |
| 13 | **Skill System** | `src/skills/`, `src/tools/SkillTool/` | Declarative skill loading, execution isolation | ★★★ | Low |

### Category D: Error Handling & Observability (Must Adapt)

| # | Module | Location | Purpose | Value | Complexity |
|---|--------|----------|---------|-------|-----------|
| 14 | **Error Classification** | `src/services/api/errors.ts` | Categorizes API/runtime errors, triggers retries vs. fails | ★★★ | Low |
| 15 | **Cost Tracker** | `src/cost-tracker.ts` | Tracks token usage per model, projects burn rate | ★★★ | Low |
| 16 | **Session History** | `src/assistant/sessionHistory.ts` | Maintains turn-by-turn transcript, enables rewind/resume | ★★★ | Low |
| 17 | **Hooks System** | `src/utils/hooks/` | Pre/post-tool execution hooks for monitoring/gating | ★★ | Low |

### Category E: Context & Config (Reference)

| # | Module | Location | Purpose | Value | Complexity |
|---|--------|----------|---------|-------|-----------|
| 18 | **System Context** | `src/context.ts` | Collects system info (git, env, files) for prompt injection | ★★ | Low |
| 19 | **Config Schema** | `src/schemas/`, `src/utils/config.ts` | Validates and manages user settings | ★★ | Low |
| 20 | **API Client** | `src/services/api/` | HTTP wrapper for Anthropic SDK, retry logic | ★★ | Low |

---

## Part 2: Adaptation Strategy

### Architecture Overview

```
Claude Code (TypeScript)          Jarvis (Python)
┌─────────────────────┐          ┌──────────────────────┐
│ Tool System         │  ───→    │ JarvisTool Base      │
│ (Tool.ts)           │          │ (server/agents/...)  │
└─────────────────────┘          └──────────────────────┘
        │                                  │
        ↓                                  ↓
┌─────────────────────┐          ┌──────────────────────┐
│ QueryEngine.ts      │  ───→    │ ToolExecutor Wrapper │
│ (tool orchestration)│          │ (server/bridge.py)   │
└─────────────────────┘          └──────────────────────┘
        │                                  │
        ↓                                  ↓
┌─────────────────────┐          ┌──────────────────────┐
│ Agent Tool Framework│  ───→    │ Agent Registry       │
│ (AgentTool/)        │          │ (server/agents/...)  │
└─────────────────────┘          └──────────────────────┘
```

### Strategy by File Type

#### Import Refactoring

**Files that need extensive refactoring:**
- `src/Tool.ts` → Translate Zod schemas to Pydantic
- `src/tools.ts` → Registry pattern unchanged, import paths adjusted
- `src/QueryEngine.ts` → Split LLM loop from Jarvis integration point

**Files that need partial refactoring:**
- `src/tools/BashTool/` → Reuse shell execution logic, wrap in Python subprocess
- `src/tools/File*Tool/` → Reuse edit strategies, wrap in Python pathlib
- `src/types/permissions.ts` → Map to dataclasses, enum patterns

**Files that can be referenced as-is:**
- `src/coordinator/` → Study orchestration pattern, implement in Python
- `src/utils/model/` → Study model selection logic, adapt for OpenRouter
- `src/services/api/errors.ts` → Implement error classification in Python

#### Function Wrapping Strategy

**High-priority wrapping targets:**

1. **Tool Execution**
   - Source: `QueryEngine.executeToolCall()`
   - Wrapper: `JarvisToolExecutor.execute(tool_name, inputs, context)`
   - Integration: Hook into `server/bridge.py` main loop

2. **Agent Spawning**
   - Source: `AgentTool.invoke()`
   - Wrapper: `JarvisAgentManager.spawn_agent(agent_config, task)`
   - Integration: Connect to `server/agents/agent_runner.py`

3. **Permission Checking**
   - Source: `useCanUseTool()` hook
   - Wrapper: `JarvisPermissionGate.check(tool, context)`
   - Integration: Add pre-execution hook to bridge.py

4. **State Serialization**
   - Source: `AppState.ts` serialization
   - Wrapper: `JarvisSessionState.save()/load()`
   - Integration: Persist to `server/data/sessions/`

#### Class Subclassing Strategy

**Tools that will be subclassed:**

```python
# Pseudo-pattern
class JarvisTool(ABC):
    """Base class inspired by Claude Code Tool.ts"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    async def execute(self, inputs: Dict, context: ToolContext) -> ToolResult:
        """Must be overridden by subclasses"""
        pass
    
    async def check_permission(self, context: ToolContext) -> bool:
        """Default: allow. Subclasses override for restrictions."""
        return True

class JarvisBashTool(JarvisTool):
    """Adapted from BashTool, wraps subprocess with timeout/sandbox"""
    
class JarvisAgentTool(JarvisTool):
    """Adapted from AgentTool, spawns sub-agents with capability scoping"""
    
class JarvisFileTool(JarvisTool):
    """Adapted from FileEditTool, atomic file modifications"""
```

#### API Compatibility Layer

**Required adapters:**

1. **Message Format Translator**
   - Claude Code: `ToolUseBlockParam` (Anthropic SDK types)
   - Jarvis: Plain dict/dataclass format
   - Converter: Maps between formats for cross-system compatibility

2. **Permission Model Converter**
   - Claude Code: `CanUseToolFn(context) → boolean`
   - Jarvis: Policy-based gate with rule engine
   - Adapter: Wraps policy checks in function signature

3. **Error Handler Unifier**
   - Claude Code: `categorizeRetryableAPIError()`
   - Jarvis: `ErrorClassifier` enum (Retryable, Fatal, Credential, RateLimit, etc.)
   - Mapping: Normalizes error types across APIs

---

## Part 3: Migration Checklist

### Phase 1: Foundation (Files to Copy with Minimal Changes)

**No logic changes, interface adapters only:**

- [ ] `src/types/permissions.ts` → `server/types/permissions.py` (Dataclass conversion)
- [ ] `src/Tool.ts` type structure → `server/tools/base_tool.py` (Pydantic models)
- [ ] `src/types/tools.ts` progress types → `server/types/tool_progress.py`
- [ ] `src/cost-tracker.ts` logic → `server/metrics/cost_tracker.py`
- [ ] `src/services/api/errors.ts` → `server/api/error_classifier.py`

**Effort:** 20-30 files, 5-10 hours

### Phase 2: Significant Adaptation (Core Logic Ported)

**Algorithmic porting, not direct translation:**

- [ ] `src/QueryEngine.ts` tool loop → `server/bridge.py` tool_execution_loop() (refactored for async)
- [ ] `src/tools/AgentTool/` → `server/agents/agent_spawner.py` (multi-agent routing)
- [ ] `src/tools/BashTool/` → `server/tools/bash_tool.py` (subprocess management)
- [ ] `src/tools/File*Tool/` → `server/tools/file_tools.py` (file operations)
- [ ] `src/utils/permissions/` → `server/security/permission_gate.py` (access control)
- [ ] `src/Task.ts` → `server/types/task.py` (lifecycle management)
- [ ] `src/memdir/` → `server/memory/session_memory.py` (persistent memory)

**Effort:** 30-40 files, 20-30 hours

### Phase 3: Reference & Inspiration (Documentation + Pattern Study)

**Not ported; studied for architecture:**

- [ ] `src/coordinator/` → Document orchestration patterns in `docs/ORCHESTRATION_PATTERNS.md`
- [ ] `src/utils/model/` → Reference for `server/model_router.py` v2 (already exists)
- [ ] `src/services/mcp/` → Study for future MCP integration
- [ ] `src/skills/` → Analyze for Jarvis skill system enhancement
- [ ] `src/components/` (UI) → Reference only (not applicable to API)

**Effort:** 5-10 hours (documentation + analysis)

### Validation Checklist

- [ ] No code copied without explicit import/reference comment
- [ ] All type signatures match Python conventions (snake_case, type hints)
- [ ] Permission model integrated with existing `server/agents/guard_agent.py`
- [ ] Tool registry updated in `server/bridge.py`
- [ ] Error handling routes through `server/agents/error_handler_agent.py`
- [ ] Cost tracking merges with existing usage tracking
- [ ] Session persistence uses existing `server/data/sessions/` structure
- [ ] All tests pass: `pytest server/tests/`

---

## Part 4: Sample Adapter Implementations

### Adapter 1: Tool Base Class Wrapper

**File:** `server/tools/adapter_claude_tool_base.py`

```python
"""
Claude Code Tool System Adapter
Bridges Claude Code's Tool.ts to Jarvis JarvisTool base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable
from enum import Enum

# ─── Type Definitions (from src/types/tools.ts pattern) ───
class ToolProgressType(str, Enum):
    """Tool execution progress stages"""
    INITIATED = "initiated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ToolProgress:
    """Progress tracking (from ToolProgressData)"""
    type: ToolProgressType
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ToolResult:
    """Result structure (from ToolResultBlockParam pattern)"""
    content: str
    is_error: bool = False
    tool_use_id: Optional[str] = None
    progress: Optional[ToolProgress] = None

@dataclass
class ToolInputSchema:
    """JSON Schema representation (simplified from Tool.ts)"""
    type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    required: list = field(default_factory=list)
    description: Optional[str] = None

# ─── Base Tool Adapter ───
class ClaudeToolAdapter(ABC):
    """
    Adapter for Claude Code Tool.ts interface.
    
    Design pattern from src/Tool.ts:
    - Static schema definition
    - Input validation
    - Permission checking (before execution)
    - Progress streaming
    - Error handling
    """
    
    name: str
    description: str
    input_schema: ToolInputSchema
    
    # Adapter from useCanUseTool() hook
    _permission_checker: Optional[Callable[[Dict[str, Any]], bool]] = None
    
    @abstractmethod
    async def execute(
        self,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
        on_progress: Optional[Callable[[ToolProgress], None]] = None
    ) -> ToolResult:
        """
        Execute tool (from Tool.ts pattern).
        
        Args:
            inputs: Validated tool inputs (matches input_schema)
            context: Execution context (working_dir, session_id, cwd, etc.)
            on_progress: Callback for progress updates
        
        Returns:
            ToolResult with content and optional error status
        """
        pass
    
    async def check_permission(
        self,
        context: Dict[str, Any]
    ) -> bool:
        """
        Permission check (from CanUseToolFn pattern).
        
        Called before execute(). Default allows all.
        Subclasses override to restrict access.
        
        Adapted from src/hooks/useCanUseTool.ts
        """
        if self._permission_checker:
            return self._permission_checker(context)
        return True
    
    def get_input_schema(self) -> ToolInputSchema:
        """Return schema (static from Tool.ts)"""
        return self.input_schema
    
    def register_permission_checker(
        self,
        checker: Callable[[Dict[str, Any]], bool]
    ):
        """Register a permission checking function"""
        self._permission_checker = checker

# ─── Integration Hook ───
class ToolExecutionAdapter:
    """
    Wraps Claude Code's tool execution loop (from QueryEngine.ts).
    
    Pattern:
    1. Tool lookup (from registry)
    2. Permission check
    3. Execute
    4. Return result to LLM
    """
    
    def __init__(self):
        self.tools: Dict[str, ClaudeToolAdapter] = {}
    
    def register_tool(self, tool: ClaudeToolAdapter):
        """Register a tool (like src/tools.ts registry)"""
        self.tools[tool.name] = tool
    
    async def execute_tool_call(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute tool with permission gating.
        
        Pattern from QueryEngine.ts:executeToolCall()
        """
        if tool_name not in self.tools:
            return ToolResult(
                content=f"Unknown tool: {tool_name}",
                is_error=True
            )
        
        tool = self.tools[tool_name]
        
        # Check permission (from src/hooks/useCanUseTool.ts)
        if not await tool.check_permission(context):
            return ToolResult(
                content=f"Permission denied for tool: {tool_name}",
                is_error=True
            )
        
        # Execute
        try:
            return await tool.execute(inputs, context)
        except Exception as e:
            return ToolResult(
                content=f"Tool error: {str(e)}",
                is_error=True
            )
```

---

### Adapter 2: Agent Tool Wrapper (Multi-Agent Spawning)

**File:** `server/tools/adapter_agent_tool.py`

```python
"""
Agent Tool Adapter
Bridges Claude Code AgentTool (src/tools/AgentTool/) to Jarvis multi-agent system.

Pattern from src/tools/AgentTool/:
- Load agent definitions from manifest
- Validate agent capabilities against restrictions
- Spawn with sandboxed scope
- Monitor execution
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from enum import Enum
import asyncio

# ─── Definitions (from src/tools/AgentTool/loadAgentsDir.ts pattern) ───

@dataclass
class AgentCapability:
    """Agent capability restriction (from AgentTool)"""
    tool_names: List[str] = field(default_factory=list)
    max_concurrency: int = 1
    timeout_seconds: int = 300
    memory_limit_mb: Optional[int] = None

@dataclass
class AgentDefinition:
    """Agent definition (from loadAgentsDir.ts)"""
    id: str
    name: str
    description: str
    instructions: str
    capabilities: AgentCapability
    parent_agent_id: Optional[str] = None

@dataclass
class AgentSpawnRequest:
    """Request to spawn an agent"""
    agent_id: str
    task_description: str
    input_data: Dict[str, Any] = field(default_factory=dict)
    parent_session_id: Optional[str] = None

@dataclass
class AgentExecutionStatus(str, Enum):
    """Execution status (from agent monitoring)"""
    SPAWNED = "spawned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"

@dataclass
class AgentExecutionResult:
    """Result of agent execution"""
    agent_id: str
    status: AgentExecutionStatus
    output: str
    error: Optional[str] = None
    duration_seconds: float = 0.0

# ─── Agent Tool Adapter ───
class AgentToolAdapter:
    """
    Wraps Claude Code's AgentTool (src/tools/AgentTool/).
    
    Design from src/tools/AgentTool/index.ts:
    - Load agents from manifest
    - Validate before spawning
    - Monitor for capability violations
    - Enforce timeouts and resource limits
    """
    
    name = "AgentTool"
    description = "Spawn and coordinate sub-agents (adapted from Claude Code)"
    
    def __init__(self, agent_registry_path: str):
        self.agent_registry_path = agent_registry_path
        self.agents: Dict[str, AgentDefinition] = {}
        self.running_agents: Dict[str, asyncio.Task] = {}
    
    async def load_agents(self):
        """Load agent definitions (pattern: loadAgentsDir.ts)"""
        # In real implementation, would load from JSON/YAML manifest
        # For now, placeholder
        pass
    
    async def spawn_agent(
        self,
        request: AgentSpawnRequest,
        context: Dict[str, Any]
    ) -> AgentExecutionResult:
        """
        Spawn an agent with capability validation.
        
        Pattern from src/tools/AgentTool/invoke():
        1. Validate agent exists
        2. Check capabilities against restrictions
        3. Enforce sandboxing (timeout, memory)
        4. Monitor execution
        5. Return result
        """
        
        agent_id = request.agent_id
        if agent_id not in self.agents:
            return AgentExecutionResult(
                agent_id=agent_id,
                status=AgentExecutionStatus.FAILED,
                output="",
                error=f"Agent not found: {agent_id}"
            )
        
        agent = self.agents[agent_id]
        
        # Validate capabilities
        parent_context_tools = context.get("available_tools", [])
        for tool_name in agent.capabilities.tool_names:
            if tool_name not in parent_context_tools:
                return AgentExecutionResult(
                    agent_id=agent_id,
                    status=AgentExecutionStatus.FAILED,
                    output="",
                    error=f"Agent {agent_id} requested restricted tool: {tool_name}"
                )
        
        # Spawn with timeout (from AgentTool timeout pattern)
        try:
            # Create agent task (would interface with server/agents/agent_runner.py)
            agent_task = asyncio.create_task(
                self._run_agent(agent, request)
            )
            self.running_agents[agent_id] = agent_task
            
            # Wait with timeout
            output = await asyncio.wait_for(
                agent_task,
                timeout=agent.capabilities.timeout_seconds
            )
            
            return AgentExecutionResult(
                agent_id=agent_id,
                status=AgentExecutionStatus.COMPLETED,
                output=output,
                duration_seconds=agent.capabilities.timeout_seconds
            )
        
        except asyncio.TimeoutError:
            return AgentExecutionResult(
                agent_id=agent_id,
                status=AgentExecutionStatus.TIMED_OUT,
                output="",
                error=f"Agent timed out after {agent.capabilities.timeout_seconds}s",
                duration_seconds=agent.capabilities.timeout_seconds
            )
        
        except Exception as e:
            return AgentExecutionResult(
                agent_id=agent_id,
                status=AgentExecutionStatus.FAILED,
                output="",
                error=str(e)
            )
    
    async def _run_agent(
        self,
        agent: AgentDefinition,
        request: AgentSpawnRequest
    ) -> str:
        """
        Internal: run agent (would call into server/agents/agent_runner.py).
        This is a placeholder for actual multi-agent execution.
        """
        # In real implementation:
        # runner = get_agent_runner(agent.id)
        # return await runner.execute(request.task_description, request.input_data)
        return f"Agent {agent.name} executed: {request.task_description}"
```

---

### Adapter 3: Permission Gate Wrapper (Access Control)

**File:** `server/tools/adapter_permission_gate.py`

```python
"""
Permission Gate Adapter
Bridges Claude Code's permission system (src/hooks/useCanUseTool.ts, 
src/utils/permissions/) to Jarvis' guard agent.

Pattern from src/utils/permissions/:
- Permission mode (allow/deny/ask)
- Denial tracking (prevent repeated denials)
- Policy gates (sensitive operations)
- Context-aware rules
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum
import time

# ─── Enums & Types (from src/types/permissions.ts pattern) ───

class PermissionMode(str, Enum):
    """Permission state (from PermissionMode)"""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    QUARANTINE = "quarantine"

class PermissionResult(str, Enum):
    """Decision result (from PermissionResult)"""
    GRANTED = "granted"
    DENIED = "denied"
    DEFERRED = "deferred"

@dataclass
class ToolPermissionContext:
    """Context for permission decision (from Tool.ts context)"""
    tool_name: str
    user_id: str
    session_id: str
    working_directory: str
    requested_action: str  # e.g., "write", "execute", "network"
    arguments: Dict[str, Any]
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

@dataclass
class DenialRecord:
    """Denial tracking (from DenialTrackingState pattern)"""
    tool_name: str
    timestamp: float
    reason: str

# ─── Permission Gate ───
class PermissionGateAdapter:
    """
    Wraps Claude Code's permission system.
    
    Pattern from src/hooks/useCanUseTool.ts + src/utils/permissions/:
    - Declarative permission rules
    - Denial tracking (don't re-ask same denial)
    - Sensitive operation gates (code execution, network, etc.)
    - Policy-based override
    """
    
    def __init__(self):
        # Default modes for different tool types
        self.tool_modes: Dict[str, PermissionMode] = {
            "BashTool": PermissionMode.QUARANTINE,  # Dangerous, always review
            "FileWriteTool": PermissionMode.ASK,    # Sensitive, confirm large ops
            "WebFetchTool": PermissionMode.ALLOW,   # Safe
            "GrepTool": PermissionMode.ALLOW,       # Safe, read-only
            "WebSearchTool": PermissionMode.ALLOW,  # Safe
        }
        
        # Denial tracking (from DenialTrackingState)
        self.denial_records: Dict[str, List[DenialRecord]] = {}
        self.denial_cooldown_seconds = 300  # Don't re-ask within 5min
    
    async def check_permission(
        self,
        context: ToolPermissionContext,
        policy_gate: Optional[Dict[str, Any]] = None
    ) -> PermissionResult:
        """
        Check if tool use is permitted.
        
        Pattern from src/hooks/useCanUseTool.ts:
        1. Check tool mode
        2. Check denial records (cooldown)
        3. Apply policy gates
        4. Return decision
        
        Returns:
            GRANTED: proceed
            DENIED: fail immediately
            DEFERRED: ask user (would be handled by guard agent)
        """
        
        tool_name = context.tool_name
        mode = self.tool_modes.get(tool_name, PermissionMode.ASK)
        
        # Check denial cooldown
        if self._is_recently_denied(tool_name, context.session_id):
            return PermissionResult.DENIED
        
        # Mode-based decision
        if mode == PermissionMode.ALLOW:
            return PermissionResult.GRANTED
        
        elif mode == PermissionMode.DENY:
            self._record_denial(
                tool_name,
                context.session_id,
                "Tool disabled by policy"
            )
            return PermissionResult.DENIED
        
        elif mode == PermissionMode.QUARANTINE:
            # For dangerous tools, apply extra checks
            if policy_gate and policy_gate.get("security_level") == "restricted":
                self._record_denial(
                    tool_name,
                    context.session_id,
                    "Security policy blocks tool"
                )
                return PermissionResult.DENIED
            # Otherwise, defer to guard agent
            return PermissionResult.DEFERRED
        
        else:  # ASK
            # Sensitive operation, ask user (deferred to guard agent)
            return PermissionResult.DEFERRED
    
    def _is_recently_denied(self, tool_name: str, session_id: str) -> bool:
        """Check if tool was recently denied (cooldown active)"""
        key = f"{tool_name}:{session_id}"
        if key not in self.denial_records:
            return False
        
        records = self.denial_records[key]
        if not records:
            return False
        
        last_denial = records[-1].timestamp
        age_seconds = time.time() - last_denial
        return age_seconds < self.denial_cooldown_seconds
    
    def _record_denial(
        self,
        tool_name: str,
        session_id: str,
        reason: str
    ):
        """Record a denial (from DenialTrackingState)"""
        key = f"{tool_name}:{session_id}"
        if key not in self.denial_records:
            self.denial_records[key] = []
        
        self.denial_records[key].append(
            DenialRecord(
                tool_name=tool_name,
                timestamp=time.time(),
                reason=reason
            )
        )
    
    # ─── Integration with guard_agent ───
    
    async def request_policy_decision(
        self,
        context: ToolPermissionContext
    ) -> PermissionResult:
        """
        Request permission from guard agent.
        
        Would integrate with server/agents/guard_agent.py
        
        For now, placeholder that would call:
        return await guard_agent.evaluate(context)
        """
        # Placeholder for integration with guard_agent.py
        decision = await self.check_permission(context)
        if decision == PermissionResult.DEFERRED:
            # Would ask guard_agent here
            # For now, return GRANTED
            return PermissionResult.GRANTED
        return decision
```

---

## Part 5: Integration Points with Jarvis

### Hook Integration (server/bridge.py)

```python
# Pseudo-code showing integration
from server.tools.adapter_claude_tool_base import ToolExecutionAdapter
from server.tools.adapter_agent_tool import AgentToolAdapter
from server.tools.adapter_permission_gate import PermissionGateAdapter

# In bridge.py main loop:
tool_executor = ToolExecutionAdapter()
agent_tool = AgentToolAdapter("server/agents/agent_manifest.json")
permission_gate = PermissionGateAdapter()

# Register adapters
tool_executor.register_tool(agent_tool)
# ... register other tools

async def handle_tool_call(tool_name, inputs, context):
    """Main tool execution point"""
    
    # Check permission (adapted from Claude Code)
    perm_context = ToolPermissionContext(
        tool_name=tool_name,
        user_id=context["user_id"],
        session_id=context["session_id"],
        working_directory=context["cwd"],
        requested_action="execute",
        arguments=inputs
    )
    
    permission = await permission_gate.request_policy_decision(perm_context)
    if permission != PermissionResult.GRANTED:
        return {"error": "Permission denied"}
    
    # Execute tool
    result = await tool_executor.execute_tool_call(
        tool_name, inputs, context
    )
    return result
```

### Agent Integration (server/agents/)

New files to create:
- `server/agents/agent_spawner.py` — Uses `AgentToolAdapter` to manage sub-agents
- `server/agents/tool_executor.py` — Uses `ToolExecutionAdapter` for tool dispatch
- `server/agents/permission_evaluator.py` — Uses `PermissionGateAdapter` for gating

---

## Success Criteria Checklist

- [ ] **20 modules identified** with value/complexity analysis
- [ ] **3 sample adapters written** (Tool base, Agent Tool, Permission Gate)
- [ ] **Adaptation strategy documented** with import/wrap/subclass decisions
- [ ] **Migration checklist created** with phases and effort estimates
- [ ] **Integration points defined** (bridge.py hooks, agent system)
- [ ] **No actual code changes** to any repo (planning only)
- [ ] **Pseudocode samples** demonstrate concrete integration patterns

---

## Timeline Estimate

| Phase | Duration | Output |
|-------|----------|--------|
| Phase 1 (Foundation) | 5-10 hrs | 20 type definition files |
| Phase 2 (Core Logic) | 20-30 hrs | Tool executor, agent system, permissions |
| Phase 3 (Reference) | 5-10 hrs | Architecture documentation |
| **Testing & Integration** | 10-15 hrs | Smoke tests, bridge.py hooks |
| **Total** | **40-65 hrs** | Fully integrated adapters |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| TypeScript→Python type mismatch | Use Pydantic dataclasses, type hints, validation |
| LLM API incompatibility | Create message format translator layer |
| Permission model drift | Centralize permission logic, test extensively |
| State persistence issues | Use existing `server/data/sessions/` structure |
| Tool naming conflicts | Prefix Claude Code adapters with `claude_` |

---

## Next Steps

1. **Confirm scope** — Review this strategy with team, adjust top 20 if needed
2. **Create detailed specs** — For each of Phase 1 & 2 modules
3. **Prototype Phase 1** — Build type adapters first (low risk)
4. **Integrate Phase 2** — Tool executor, agent spawning
5. **Validation** — Test with real tool calls, stress test permission gates

---

**Document Version:** 1.0  
**Last Updated:** 2026-04-04  
**Author:** Codex Analysis Agent  
**Status:** Ready for Review
