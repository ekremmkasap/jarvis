# CODEX Bridge Integration Design

**Document Version:** 1.0  
**Date:** 2026-04-04  
**Status:** PLANNING (No code changes yet)  
**Target:** Integrate Claude Code modules into bridge.py

---

## Executive Summary

This document outlines the architecture for integrating Claude Code modules (agents, tools, commands) into the Jarvis Mission Control `bridge.py` infrastructure. The design preserves existing functionality while enabling extensibility through a plugin-based command/agent/tool system.

**Key Goals:**
- Enable new Claude Code features without modifying core bridge.py
- Support specialized agents (backend, security, voice, video, etc.)
- Wrap Claude Code tools with fallback capabilities
- Maintain backward compatibility with existing Telegram + Ollama routing

---

## Part 1: Current Bridge.py Architecture Analysis

### 1.1 Core Components

#### Command Handling (`handle_command()`)
- **Pattern:** Simple string prefix matching (`/command args`)
- **Current Commands:** ~15+ hard-coded in if/elif chain
  - `/status`, `/models`, `/reset`
  - `/ebay`, `/hava`, `/haber`, `/altin`, `/kur`, `/hesap`
  - `/printify`, `/trendyol`
  - `/code`, `/plan`
  - `$` prefix for system commands
- **Limitations:**
  - Commands tightly coupled to implementation
  - No dynamic registration
  - No namespacing (all commands flat)
  - Command help text mixed with implementation

#### Agent Routing (`detect_route()` + `MODEL_ROUTES`)
- **Pattern:** Keyword-based LLM model selection
- **Routes:** code, reasoning, search, system, chat
- **Fallback:** Chain of alternative models
- **Implementation:** Ollama API calls with conversation history
- **Features:**
  - Per-route system prompts
  - Temperature/prediction parameters configurable
  - Memory integration (saved in Memory class)

#### Tool Integration
- **Pattern:** Import + try/except fallback to Ollama LLM
- **Examples:**
  - ebay_research → analyze_product()
  - utils_skill → get_weather(), get_currency(), etc.
  - printify_skill → format_overview()
  - trendyol_skill → full_trendyol_analysis()
- **Fallback Strategy:** If skill import/call fails, use Ollama with prompt
- **Constraints:**
  - Skills must be in `/opt/jarvis/skills/` or registered in sys.path
  - Hard-coded try/except per command
  - No unified tool registry

#### HTTP Web Server (`WebHandler`)
- **Purpose:** Dashboard + web API
- **Endpoints:** GET `/` (dashboard HTML), POST `/api/chat` (chat queries)
- **Integration Points:**
  - Reads memory.json for session history
  - Calls process_message() for inference
  - Returns Telegram-formatted responses

#### Memory System
- **JSON-based:** memory.json with sessions, history, stats
- **Optional Enhancement:** memory_skill integration (SQLite)
- **Scope:** Per chat_id, last 20 messages, basic stats

---

### 1.2 Current Data Flow

```
Telegram/Web Input
    ↓
process_message(chat_id, text)
    ↓
  ├─ Command? → handle_command() → skill try/except → response
  ├─ System ($)? → run_command_safe() → shell → response
  └─ Chat? → detect_route() → call_ollama() → memory → response
    ↓
Response → Telegram/Web Output
```

---

### 1.3 Extensibility Points (Current)

1. **MODEL_ROUTES dict** - Add new route, custom system prompt
2. **handle_command() if/elif chain** - Add new command (hard-coded)
3. **sys.path insertion** - Add skill directory before import
4. **WebHandler.do_GET/POST** - Modify HTML/endpoints (fragile)

---

## Part 2: Claude Code Module Integration Design

### 2.1 Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Bridge.py (Core)                          │
│  - Telegram/Web I/O                                             │
│  - Memory management                                            │
│  - Message routing                                              │
└────────────────────┬────────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ↓                         ↓
   ┌─────────────┐        ┌──────────────────────┐
   │  Commands   │        │  Extensions Registry │
   │  System     │        │  (Plugin Loader)     │
   └─────────────┘        └──────────────────────┘
        │                         │
        ├─ /legacy (built-in)     │
        └─ /codex (Claude Code)   ├─ Agent types
                                  ├─ Tool wrappers
                                  ├─ Routes
                                  └─ Custom handlers
```

### 2.2 Extension Points (Proposed)

#### A. Command Registration
```python
# Extension interface (to be auto-loaded)
class CommandExtension:
    """Base class for command extensions"""
    def __init__(self):
        self.commands = {}  # {"name": {"handler": fn, "help": str, "args": str}}
    
    def register(self, name, handler, help_text, args=""):
        """Register a new command"""
        pass
    
    def handle(self, cmd_name, args) -> str:
        """Execute command"""
        pass
```

**Phase 1 Integration:**
- `/claude [task]` → Claude Code runner
- `/agent-spawn [type]` → Create specialist agent
- `/task [title]` → Add to task bus
- `/codex-status` → Codex companion status

#### B. Agent Types
```python
# Define agent type registry
AGENT_TYPES = {
    "backend": {
        "description": "Backend engineering specialist",
        "system_prompt": "...",
        "tools": ["read", "write", "bash", "edit"],
        "model": "claude-opus",  # or fallback chain
    },
    "security": {
        "description": "Security audit & threat analysis",
        "system_prompt": "...",
        "tools": ["read", "grep", "bash", "audit"],
        "model": "claude-opus",
    },
    "voice": {
        "description": "Voice/audio processing",
        "system_prompt": "...",
        "tools": ["piper", "transcribe", "audio_edit"],
        "model": "claude-haiku",
    },
    # ... more agents
}
```

**Phase 1 Integration:**
- Query AGENT_TYPES registry
- Spawn agent via task bus
- Stream results back to Telegram/Web

#### C. Tool Wrappers
```python
# Tool wrapper interface
class ToolWrapper:
    """Base class for tool execution"""
    def __init__(self, name, fallback_llm=True):
        self.name = name
        self.fallback_llm = fallback_llm
        self.capabilities = {}
    
    def execute(self, operation, params) -> dict:
        """Execute tool, fallback to LLM if needed"""
        try:
            return self._execute_native(operation, params)
        except Exception as e:
            if self.fallback_llm:
                return self._execute_fallback(operation, params)
            raise
```

**Phase 1 Wrappers:**
- FileRead (read, write, search)
- BashExec (run, timeout, safe mode)
- GitTools (status, diff, commit)
- EditorTools (edit, replace, insert)

#### D. Route Extensions
```python
# Add new routes alongside existing MODEL_ROUTES
CLAUDE_ROUTES = {
    "code-review": {
        "description": "Code review specialist",
        "model": "claude-opus",
        "tools": ["read", "grep", "bash"],
        "keywords": ["review", "audit", "inspect", "quality"],
        "system": "You are a code review expert. Focus on quality, security, performance.",
    },
    "architecture": {
        "description": "System architecture design",
        "model": "claude-opus",
        "tools": ["read", "bash", "diagram"],
        "keywords": ["design", "architecture", "diagram", "refactor"],
        "system": "You are a systems architect. Think in components, flows, trade-offs.",
    },
}
```

---

### 2.3 Extension Loader Pseudo-Code

```python
# bridge_extensions.py (new file)
class ExtensionRegistry:
    def __init__(self):
        self.commands = {}       # name -> {handler, help, args}
        self.agents = {}         # type -> {system, tools, model, desc}
        self.tools = {}          # name -> ToolWrapper instance
        self.routes = {}         # name -> {model, keywords, system, tools}
        self.handlers = {}       # pattern -> handler_fn
    
    def register_command(self, name, handler, help_text, args=""):
        """Add new /{name} command"""
        self.commands[name] = {
            "handler": handler,
            "help": help_text,
            "args": args,
        }
    
    def register_agent(self, agent_type, config):
        """Add new agent type"""
        self.agents[agent_type] = config
    
    def register_tool(self, name, wrapper):
        """Register tool wrapper"""
        self.tools[name] = wrapper
    
    def register_route(self, route_name, config):
        """Add new inference route"""
        self.routes[route_name] = config
    
    def handle_command(self, cmd_name, args) -> str:
        """Execute command via registry"""
        if cmd_name not in self.commands:
            return f"Unknown command: /{cmd_name}"
        handler = self.commands[cmd_name]["handler"]
        return handler(args)
    
    def load_extensions(self, extension_dir):
        """Auto-load extension modules"""
        # Scan extension_dir for extension_*.py files
        # Import and call register() on each
        pass

# In handle_command():
registry = ExtensionRegistry()
if cmd_name in registry.commands:
    return registry.handle_command(cmd_name, args)
elif cmd_name in handle_command_legacy(cmd, args):  # fallback
    pass
```

---

## Part 3: Integration Roadmap

### Phase 1: Core Claude Code Integration (Weeks 1-2)

**Goal:** Basic Claude Code agent spawning + command support

**Tasks:**
1. Create `bridge_extensions.py` with ExtensionRegistry
2. Create `extensions/core.py`:
   - `/claude [task]` → Call Claude Code CLI
   - `/agent-spawn [type]` → Create specialist agent
   - `/task [title]` → Add to task bus
   - `/codex-status` → Check companion status
3. Create `extensions/toolwrap.py`:
   - FileRead wrapper (read, write, grep fallback)
   - BashExec wrapper (timeout, safe mode)
4. Modify `bridge_current.py`:
   - Import ExtensionRegistry
   - Load extensions on startup
   - Route commands to registry before fallback
5. Add to `/help` output
6. Smoke tests: `/claude "hello"`, `/agent-spawn backend`, `/task test`

**File Changes:**
- NEW: `bridge_extensions.py` (250 lines)
- NEW: `extensions/core.py` (150 lines)
- NEW: `extensions/toolwrap.py` (200 lines)
- MODIFY: `bridge_current.py` (5-10 lines: import + loader call)
- NEW: `extensions/__init__.py` (30 lines)

**Success Criteria:**
- ✓ Commands route to registry
- ✓ Claude Code spawning works
- ✓ Agent types accessible
- ✓ Tool wrappers fallback properly

---

### Phase 2: Advanced Features (Week 3-4)

**Goal:** Multi-agent orchestration, code review, architecture design

**Tasks:**
1. Create specialist agents:
   - `backend` (engineering) with tool access
   - `security` (auditing) with read/grep/bash
   - `voice` (audio processing) with Piper/transcribe
   - `swarm` (planning/orchestration)
2. Add routes:
   - `code-review` → Opus model for quality review
   - `architecture` → System design specialist
   - `security-audit` → Threat/vulnerability analysis
3. Create `extensions/agents.py`:
   - Agent spawning with task bus
   - Agent state tracking
   - Result streaming
4. Implement tool integration:
   - File operations (via Claude Code backend)
   - Bash execution (safe wrapper)
   - Git operations (read-only queries)
5. Add `/help agents` detailed listing

**File Changes:**
- NEW: `extensions/agents.py` (300 lines)
- NEW: `extensions/routes.py` (150 lines)
- MODIFY: `bridge_current.py` (register new routes)

**Success Criteria:**
- ✓ 3+ specialist agents spawning
- ✓ Code review route working
- ✓ Tool wrappers accessing files safely
- ✓ Results streaming to Telegram

---

### Phase 3: Full Integration (Future)

**Goal:** Complete Claude Code ecosystem integration

**Features:**
1. MCP server wrappers (Supabase, GitHub, etc.)
2. Advanced memory (RAG from knowledge base)
3. Long-running agent workflows
4. Webhook handlers for CI/CD
5. Dashboard UI for agent management
6. Metrics/observability (agent throughput, token usage)

---

## Part 4: Extension Interface Design

### 4.1 Creating a Custom Extension

**File: `extensions/custom_skill.py`**
```python
"""
Custom Extension Template for Bridge

Usage:
- Place in extensions/ directory
- Define Extension class with register() method
- Bridge auto-loads via ExtensionRegistry.load_extensions()
"""

from typing import Dict, List, Optional

class CustomExtension:
    """
    Template for custom bridge extensions.
    
    Attributes:
        name: Extension name (e.g., "ebay-advanced")
        version: Version string
        requires: List of dependencies
    """
    
    def __init__(self):
        self.name = "custom_skill"
        self.version = "1.0"
        self.requires = []  # Optional: ["requests", "beautifulsoup4"]
    
    def register(self, registry):
        """
        Called by ExtensionRegistry during load_extensions().
        
        Args:
            registry: ExtensionRegistry instance
        
        Example:
            registry.register_command(
                name="mycommand",
                handler=self.handle_mycommand,
                help_text="Do something custom",
                args="[arg1] [arg2]"
            )
        """
        # Register commands
        registry.register_command(
            "mycommand",
            self.handle_mycommand,
            "Custom command example",
            "[query]"
        )
        
        # Register tools
        registry.register_tool("my_tool", self.MyToolWrapper())
        
        # Register agents (if any)
        registry.register_agent("my_agent", {
            "description": "...",
            "system_prompt": "...",
            "tools": ["my_tool"],
            "model": "claude-opus"
        })
        
        # Register routes (if any)
        registry.register_route("my_route", {
            "model": "claude-haiku",
            "keywords": ["my", "custom"],
            "system": "You are...",
            "tools": ["my_tool"]
        })
    
    def handle_mycommand(self, args: str) -> str:
        """
        Handler for /mycommand.
        
        Args:
            args: Command arguments (string after /mycommand)
        
        Returns:
            Response string (Telegram format)
        """
        if not args:
            return "Usage: /mycommand [query]"
        
        # Your implementation here
        result = self.do_something(args)
        return f"Result:\n{result}"
    
    def do_something(self, query: str) -> str:
        """Business logic - implement as needed"""
        return f"Processed: {query}"
    
    class MyToolWrapper:
        """Tool wrapper with fallback support"""
        
        def __init__(self):
            self.name = "my_tool"
            self.fallback_llm = True
        
        def execute(self, operation: str, params: dict) -> dict:
            """Execute tool or fallback to LLM"""
            try:
                return self._native(operation, params)
            except Exception as e:
                if self.fallback_llm:
                    return self._fallback(operation, params)
                raise
        
        def _native(self, op: str, params: dict) -> dict:
            """Native tool implementation"""
            # Implement actual tool logic here
            return {"status": "ok", "data": None}
        
        def _fallback(self, op: str, params: dict) -> dict:
            """Fallback to LLM-based execution"""
            return {
                "status": "fallback",
                "data": f"LLM would handle: {op} {params}"
            }
```

### 4.2 Command Registration Pattern

**Existing (bridge_current.py):**
```python
def handle_command(chat_id: int, cmd: str) -> str:
    parts = cmd.split(" ", 2)
    command = parts[0].lower()
    args = " ".join(parts[1:]) if len(parts) > 1 else ""
    
    if command == "/ebay":
        # ... 20 lines of logic
    elif command == "/code":
        # ... 10 lines of logic
    # ... 50+ more elif branches
```

**Proposed (via extension):**
```python
# In extension file:
def handle_ebay_extended(args: str) -> str:
    """Enhanced eBay analysis"""
    # Reusable, testable function
    pass

# In register():
registry.register_command(
    "ebay-pro",
    handle_ebay_extended,
    "Advanced eBay market analysis",
    "[product] [--depth high|low]"
)

# In bridge_current.py handle_command():
if cmd_name in registry.commands:
    return registry.handle_command(cmd_name, args)
```

### 4.3 Tool Wrapper Pattern

**Pattern: Graceful Degradation**
```python
class FileReadTool(ToolWrapper):
    """File reading with multiple fallback modes"""
    
    def execute(self, operation, params):
        """
        Modes:
        1. Native file read (fast)
        2. Through Claude Code (if available)
        3. LLM-based summary (if file too large)
        """
        path = params.get("path")
        
        # Try native first
        try:
            with open(path) as f:
                return {"status": "native", "content": f.read()}
        except IOError:
            pass
        
        # Try Claude Code backend
        try:
            result = self._claudecode_read(path)
            return {"status": "claude-code", "content": result}
        except:
            pass
        
        # Fallback to LLM description
        return {
            "status": "llm-fallback",
            "content": f"File would be read: {path}"
        }
```

---

## Part 5: Implementation Checklist

### Phase 1 Checklist

- [ ] Create `bridge_extensions.py` with ExtensionRegistry class
- [ ] Create `extensions/` directory structure
- [ ] Create `extensions/__init__.py`
- [ ] Create `extensions/core.py` with basic commands
- [ ] Create `extensions/toolwrap.py` with FileRead/BashExec wrappers
- [ ] Modify `bridge_current.py` to load extensions (5-10 LOC)
- [ ] Create `extensions/custom_skill.py` template file
- [ ] Write smoke tests for `/claude`, `/agent-spawn`, `/task`
- [ ] Update `/help` output to include new commands
- [ ] Document in `docs/EXTENSIONS.md` how to create extensions
- [ ] Create `examples/extension_ebay.py` showing eBay extension

### Phase 2 Checklist

- [ ] Create `extensions/agents.py` with specialist agents
- [ ] Create `extensions/routes.py` with code-review, architecture, etc.
- [ ] Implement agent spawning via task bus
- [ ] Add agent state tracking (redis or in-memory)
- [ ] Implement tool access control
- [ ] Create streaming results to Telegram
- [ ] Add `/list-agents` command
- [ ] Create integration tests for multi-agent workflows

### Phase 3 Checklist (Future)

- [ ] MCP server wrappers
- [ ] Advanced memory/RAG
- [ ] Long-running workflows
- [ ] Webhooks
- [ ] Dashboard agent UI
- [ ] Metrics/observability

---

## Part 6: Risk Analysis & Mitigations

### Risk 1: Command Name Collisions

**Risk:** New extensions override built-in commands

**Mitigation:**
- Use namespace prefixes: `/codex-*`, `/agent-*`, `/skill-*`
- Registry.register() throws error on collision (opt-in override)
- Help text clearly shows namespace

### Risk 2: Tool Execution Security

**Risk:** Untrusted extensions run arbitrary code

**Mitigation:**
- Tool wrappers use native implementations first (no eval)
- File/bash operations limited by OS permissions
- Pre-flight validation in ToolWrapper.execute()
- Audit logging for tool calls

### Risk 3: Memory/Performance

**Risk:** Registry grows unbounded, Telegram latency increases

**Mitigation:**
- Registry is in-memory, ~100KB per 50 extensions
- Commands are O(1) lookup (dict-based)
- Tool execution has timeout wrapper
- Agent spawning is async (doesn't block Telegram loop)

### Risk 4: Backward Compatibility

**Risk:** Existing commands break when refactored

**Mitigation:**
- Phase 1 adds NEW commands, doesn't touch existing ones
- Existing `/ebay`, `/code`, `/plan` stay in bridge_current.py
- Registry is opt-in routing (before fallback to legacy)
- All changes confined to new files initially

---

## Part 7: File Organization

```
jarvis-mission-control/
├── bridge_current.py (CORE - minimal changes)
│   ├── +5 lines: import ExtensionRegistry
│   ├── +2 lines: registry.load_extensions("extensions/")
│   └── +5 lines: registry.handle_command() before legacy fallback
├── bridge_extensions.py (NEW - 250 lines)
│   └── ExtensionRegistry class
├── extensions/ (NEW directory)
│   ├── __init__.py (30 lines)
│   ├── core.py (150 lines) - /claude, /agent-spawn, /task
│   ├── toolwrap.py (200 lines) - FileRead, BashExec
│   ├── custom_skill.py (180 lines) - TEMPLATE
│   ├── agents.py (300 lines, Phase 2) - Specialist agents
│   └── routes.py (150 lines, Phase 2) - Code review, architecture
├── docs/
│   ├── CODEX_BRIDGE_INTEGRATION.md (THIS FILE)
│   ├── EXTENSIONS.md (NEW - how to create extensions)
│   └── API.md (NEW - registry API reference)
└── examples/
    ├── extension_ebay.py (Show eBay as extension)
    └── extension_voice.py (Show voice as extension)
```

---

## Part 8: Success Metrics

### Phase 1 Success

- [ ] Bridge loads without errors
- [ ] `/claude "test"` returns Claude Code result
- [ ] `/agent-spawn backend` creates agent (status check)
- [ ] `/task "test task"` appears in task bus
- [ ] `/codex-status` returns companion status
- [ ] All existing commands still work
- [ ] Smoke tests pass (0 failures)

### Phase 2 Success

- [ ] 3+ specialist agents operational
- [ ] Code review route identifies issues
- [ ] Tool wrappers fallback gracefully
- [ ] Agents share context via memory
- [ ] Results stream to Telegram in <2 sec
- [ ] No performance regression (throughput unchanged)

---

## Appendix A: Bridge Structure Summary

```
Command Flow:
  Input → process_message()
    ├─ is command? → handle_command()
    │   ├─ NEW: ExtensionRegistry.handle_command()
    │   └─ OLD: if/elif chains (fallback)
    ├─ is system? → run_command_safe()
    └─ is chat? → detect_route() → call_ollama()

Model Routes:
  input keywords → detect_route()
    → MODEL_ROUTES or CLAUDE_ROUTES (Phase 2)
    → Select model + system prompt
    → call_ollama() with history
    → save to memory

Tool Integration:
  skill needed? → try native import/call
    ├─ Success → return result
    └─ Fail → fallback to Ollama LLM call

Memory:
  Every message → memory.add_message()
  Later request → memory.get_history(last_n=10)
```

---

## Appendix B: Claude Code Modules Reference

**Phase 1 Modules:**
- claude-code CLI (spawning agents)
- Task bus (adding/querying tasks)
- Companion status (health check)

**Phase 2 Modules:**
- Agent framework (specialist types)
- Tool integration (file, bash, git)
- MCP servers (Supabase, GitHub)

**Phase 3 Modules:**
- Long-running workflows
- Advanced memory/RAG
- Observability dashboards

---

## Appendix C: Example: Adding eBay as Extension

**Current Implementation (hard-coded in bridge_current.py):**
```python
elif command == "/ebay":
    query = args or "kazancli dropshipping urun"
    try:
        from ebay_research import analyze_product, format_report
        result = analyze_product(query)
        return format_report(result)
    except Exception as e:
        # ... fallback to Ollama
```

**Proposed Extension (extensions/ebay.py):**
```python
from bridge_extensions import ToolWrapper

class eBayExtension:
    def __init__(self):
        self.name = "ebay"
        self.version = "2.0"
    
    def register(self, registry):
        registry.register_command(
            "ebay",
            self.handle_ebay,
            "eBay market analysis",
            "[product]"
        )
        registry.register_command(
            "ebay-pro",
            self.handle_ebay_pro,
            "Advanced eBay analysis with trends",
            "[product] [--depth high|low]"
        )
        registry.register_tool("ebay", self.EBayTool())
        registry.register_route("ebay_search", {
            "model": "mistral",
            "keywords": ["ebay", "dropship", "listing"],
            "system": "You are an e-commerce expert...",
            "tools": ["ebay"]
        })
    
    def handle_ebay(self, args: str) -> str:
        query = args or "kazancli dropshipping urun"
        try:
            from ebay_research import analyze_product, format_report
            result = analyze_product(query)
            return format_report(result)
        except Exception as e:
            return f"Error: {e}. Use /ebay-pro for LLM fallback."
    
    def handle_ebay_pro(self, args: str) -> str:
        # Call Claude Code for advanced analysis
        return f"Advanced analysis for: {args}"
    
    class EBayTool(ToolWrapper):
        def execute(self, operation, params):
            if operation == "analyze":
                # Native implementation
                pass
            return super().execute(operation, params)
```

**Benefits:**
- eBay logic isolated from core bridge
- Can be versioned independently
- Can be disabled/replaced easily
- Extends via tool wrapper pattern
- Testable in isolation

---

## Conclusion

This design enables **extensible Claude Code integration** while preserving bridge.py's current simplicity and reliability. The three-phase approach balances immediate value (Phase 1) with long-term vision (Phase 3), keeping risks minimal through isolated extension files.

**Next Steps:**
1. Create `bridge_extensions.py` and `extensions/` directory
2. Implement Phase 1 core extension
3. Add to bridge_current.py's import/loader (5-10 lines only)
4. Test end-to-end with `/claude` command
5. Document extension creation in `docs/EXTENSIONS.md`

