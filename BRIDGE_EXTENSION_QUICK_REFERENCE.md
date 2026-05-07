# Bridge Extension Quick Reference

**Quick guide for developers creating extensions**

---

## TL;DR

1. Create file: `extensions/my_feature.py`
2. Define class inheriting from `Extension`
3. Implement `register(registry)` method
4. Register commands/tools/agents
5. Bridge auto-loads on startup

---

## File Template

```python
from bridge_extensions import Extension, ToolWrapper

class MyExtension(Extension):
    def __init__(self):
        self.name = "my_feature"
        self.version = "1.0"
    
    def register(self, registry):
        # Register commands
        registry.register_command(
            "mycommand",
            self.handle_mycommand,
            "Help text here",
            "[arg1] [arg2]"
        )
        
        # Register tools (optional)
        registry.register_tool("my_tool", self.MyTool())
        
        # Register agents (optional)
        registry.register_agent("my_agent", {
            "description": "...",
            "system_prompt": "...",
            "tools": ["my_tool"],
            "model": "claude-opus"
        })
        
        # Register routes (optional)
        registry.register_route("my_route", {
            "model": "claude-haiku",
            "keywords": ["my", "custom"],
            "system": "You are...",
            "tools": ["my_tool"]
        })
    
    def handle_mycommand(self, args: str) -> str:
        """Handler called when user types /mycommand args"""
        if not args:
            return "Usage: /mycommand [arg]"
        return f"Result: {args}"
    
    class MyTool(ToolWrapper):
        def __init__(self):
            super().__init__("my_tool")
        
        def _execute_native(self, operation: str, params: dict) -> dict:
            # Implement tool logic
            return {"status": "success", "data": "..."}
```

---

## Registry API

### Commands

```python
registry.register_command(
    name="mycommand",           # Command name (no / prefix)
    handler=callable,           # Function(args: str) -> str
    help_text="Description",    # For /help output
    args="[optional] args"      # Usage string
)

result = registry.handle_command("mycommand", "arg1 arg2")
help_text = registry.get_command_help("mycommand")
```

### Tools

```python
class MyTool(ToolWrapper):
    def _execute_native(self, operation: str, params: dict) -> dict:
        # operation: "read", "write", "execute", etc.
        # params: dict of parameters
        # Return: {"status": "success"|"error"|"fallback", "data": ...}
        pass

registry.register_tool("my_tool", MyTool())
result = registry.execute_tool("my_tool", "read", {"path": "/file"})
```

### Agents

```python
registry.register_agent("my_agent", {
    "description": "Human-readable description",
    "system_prompt": "System prompt for agent",
    "tools": ["file_read", "bash_exec"],  # List of tool names
    "model": "claude-opus",
    # Optional:
    "kwargs": {}  # Additional config
})

agents = registry.get_agents()  # {"agent_name": "description"}
```

### Routes

```python
registry.register_route("my_route", {
    "model": "claude-haiku",
    "keywords": ["trigger", "words"],  # For auto-routing
    "system": "System prompt",
    # Optional:
    "tools": ["file_read"],  # Available tools
    "description": "Human description"
})

routes = registry.get_routes()  # {"route_name": [keywords]}
```

---

## Command Examples

### Simple Command
```python
def register(self, registry):
    registry.register_command(
        "hello",
        lambda args: f"Hello {args or 'World'}!",
        "Say hello",
        "[name]"
    )
```

### Command with Logic
```python
def register(self, registry):
    registry.register_command("greet", self.handle_greet, "Greet user", "[name]")

def handle_greet(self, args: str) -> str:
    name = args or "Friend"
    return f"Greetings, {name}! Welcome back."
```

### Command with Tool Access
```python
def register(self, registry):
    self.registry = registry  # Keep reference
    registry.register_command("read", self.handle_read, "Read file", "[path]")

def handle_read(self, args: str) -> str:
    if not args:
        return "Usage: /read [path]"
    result = self.registry.execute_tool("file_read", "read", {"path": args})
    if result["status"] == "success":
        return result["data"]
    else:
        return f"Error: {result.get('error')}"
```

---

## Tool Examples

### Simple Tool
```python
class MyTool(ToolWrapper):
    def __init__(self):
        super().__init__("my_tool", fallback_llm=True)
    
    def _execute_native(self, operation: str, params: dict) -> dict:
        if operation == "compute":
            return {
                "status": "success",
                "data": sum(params.get("numbers", []))
            }
        raise NotImplementedError(operation)
```

### Tool with Fallback
```python
class APITool(ToolWrapper):
    def __init__(self):
        super().__init__("api_call", fallback_llm=True)  # Enable LLM fallback
    
    def _execute_native(self, operation: str, params: dict) -> dict:
        # Try native API call
        try:
            import requests
            response = requests.get(params["url"], timeout=5)
            return {"status": "success", "data": response.json()}
        except:
            raise  # Will trigger fallback
    
    def _execute_fallback(self, operation: str, params: dict) -> dict:
        # Fallback: ask LLM to describe expected result
        return {
            "status": "fallback",
            "data": f"[LLM would call: {params['url']}]"
        }
```

---

## Agent Examples

### Simple Agent Definition
```python
registry.register_agent("backend_dev", {
    "description": "Backend engineering specialist",
    "system_prompt": "You are a senior backend engineer. Focus on scalability, security, and clean code.",
    "tools": ["file_read", "bash_exec"],
    "model": "claude-opus"
})
```

### Agent with Complex Tools
```python
registry.register_agent("security_auditor", {
    "description": "Security audit specialist",
    "system_prompt": """You are a security expert. Analyze code for:
    - SQL injection vulnerabilities
    - Authentication bypasses
    - Data exposure risks
    - Cryptography issues""",
    "tools": ["file_read", "grep_tool", "report_generator"],
    "model": "claude-opus",
    "kwargs": {
        "temperature": 0.3,  # Focused responses
        "max_tokens": 2000
    }
})
```

---

## Route Examples

### Simple Route
```python
registry.register_route("code_review", {
    "model": "claude-opus",
    "keywords": ["review", "audit", "quality"],
    "system": "You are a code review expert. Focus on quality, security, performance."
})
```

### Route with Tools
```python
registry.register_route("architecture_design", {
    "model": "claude-opus",
    "keywords": ["design", "architecture", "refactor", "diagram"],
    "system": "You are a systems architect. Think in components, flows, and trade-offs.",
    "tools": ["file_read", "diagram_generator", "documentation"],
    "description": "System architecture design assistant"
})
```

---

## Error Handling

### Command Errors
```python
def handle_mycommand(self, args: str) -> str:
    try:
        # Do something
        return result
    except ValueError as e:
        return f"Invalid input: {e}"
    except Exception as e:
        return f"Error: {e}"  # Will be logged automatically
```

### Tool Errors
```python
class MyTool(ToolWrapper):
    def _execute_native(self, operation: str, params: dict) -> dict:
        try:
            # Try operation
            pass
        except FileNotFoundError:
            return {"status": "error", "error": "File not found"}
        except PermissionError:
            return {"status": "error", "error": "Permission denied"}
        # Other exceptions trigger fallback automatically
```

---

## Best Practices

### 1. Naming
- Command: lowercase with hyphens (`/my-command`)
- Tool: snake_case (`my_tool`)
- Agent: snake_case (`my_agent`)
- Route: snake_case (`my_route`)

### 2. Documentation
```python
def register(self, registry):
    """Register commands and tools"""
    registry.register_command(
        "mycommand",
        self.handle_mycommand,
        "Detailed help text explaining what this does",  # Important!
        "[arg1] [optional_arg2]"  # Usage pattern
    )
```

### 3. Graceful Degradation
```python
def handle_mycommand(self, args: str) -> str:
    # Always provide a fallback message
    try:
        return do_something(args)
    except:
        return "Feature temporarily unavailable. Try /help for alternatives."
```

### 4. Keep It Simple
- One file per logical feature
- One Extension class per file
- Reuse ToolWrapper for common patterns
- Test independently

### 5. Logging
```python
import logging
log = logging.getLogger("jarvis.extensions.myfeature")

def handle_mycommand(self, args: str) -> str:
    log.info(f"Executing mycommand with args: {args}")
    try:
        result = do_work(args)
        log.debug(f"Result: {result}")
        return result
    except Exception as e:
        log.error(f"Error in mycommand: {e}", exc_info=True)
        return f"Error: {e}"
```

---

## Testing

### Unit Test Template
```python
import pytest
from bridge_extensions import ExtensionRegistry
from extensions.my_feature import MyExtension

def test_my_command():
    registry = ExtensionRegistry()
    ext = MyExtension()
    ext.register(registry)
    
    result = registry.handle_command("mycommand", "test_arg")
    assert "test_arg" in result
    assert len(result) > 0

def test_my_tool():
    registry = ExtensionRegistry()
    ext = MyExtension()
    ext.register(registry)
    
    result = registry.execute_tool("my_tool", "read", {"path": "/tmp/test"})
    assert result["status"] in ["success", "error", "fallback"]
```

---

## Deployment Checklist

- [ ] File created in `extensions/` directory
- [ ] Class inherits from `Extension`
- [ ] `register()` method implemented
- [ ] All commands registered
- [ ] All tools registered (if any)
- [ ] All agents registered (if any)
- [ ] All routes registered (if any)
- [ ] Error handling in place
- [ ] Logging configured
- [ ] Unit tests pass
- [ ] Docstrings complete
- [ ] No hard-coded paths (use params)
- [ ] No external dependencies (or documented)
- [ ] Bridge loads without errors

---

## Common Patterns

### Fallback to Ollama
```python
def handle_mycommand(self, args: str) -> str:
    try:
        # Try native implementation
        return native_implementation(args)
    except Exception as e:
        # Fallback: ask Ollama
        return f"[Ollama would handle: {args}]"
```

### Using Multiple Tools
```python
def handle_mycommand(self, args: str) -> str:
    # Read file
    file_result = self.registry.execute_tool("file_read", "read", {"path": args})
    if file_result["status"] != "success":
        return "Cannot read file"
    
    # Execute bash
    bash_result = self.registry.execute_tool("bash_exec", "run", {"command": f"wc -l {args}"})
    if bash_result["status"] != "success":
        return "Cannot count lines"
    
    return f"File has {bash_result['data']['stdout']} lines"
```

### Agent Spawning
```python
def handle_spawn_agent(self, args: str) -> str:
    agent_type = args or "backend"
    
    agents = self.registry.get_agents()
    if agent_type not in agents:
        available = ", ".join(agents.keys())
        return f"Unknown agent. Available: {available}"
    
    # TODO: Implement actual spawning via task bus
    return f"✅ Spawning agent: {agent_type}"
```

---

## Troubleshooting

### "Command not found"
- Check file is in `extensions/` directory
- Check class inherits from `Extension`
- Check `register()` method calls `registry.register_command()`
- Check bridge logs for load errors

### "Tool execution failed"
- Check tool is registered before use
- Check tool name matches exactly
- Check operation is implemented in `_execute_native()`
- Check params format matches tool expectations

### "Fallback not triggering"
- Check `fallback_llm=True` in ToolWrapper.__init__()
- Check `_execute_native()` actually raises exception
- Check `_execute_fallback()` is implemented (or inherited)

### "Extension not loading"
- Check for Python syntax errors (use `python3 -m py_compile`)
- Check dependencies are installed (if any)
- Check logs: `bridge_current.py` logs loading errors
- Check class is actually named in file

---

## Resources

- **Full Design:** `docs/CODEX_BRIDGE_INTEGRATION.md`
- **Implementation Checklist:** `CODEX_BRIDGE_INTEGRATION_CHECKLIST.md`
- **Framework Source:** `bridge_extensions_template.py`
- **Example:** `extensions/custom_skill.py` (template)

---

**Happy extending!**

For questions or issues, check the design document or ask Claude Code.
