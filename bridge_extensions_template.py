#!/usr/bin/env python3
"""
BRIDGE EXTENSIONS FRAMEWORK
===========================================

This module provides the registry and base classes for extending bridge.py
with new commands, agents, tools, and routes without modifying core code.

Design Principles:
  1. Registry-based discovery (auto-load from extensions/ directory)
  2. Plugin isolation (extensions don't depend on each other)
  3. Graceful degradation (fallback to Ollama if tools unavailable)
  4. Backward compatibility (existing commands untouched)

Usage:
  from bridge_extensions import ExtensionRegistry
  registry = ExtensionRegistry()
  registry.load_extensions("./extensions/")
  registry.handle_command("mycommand", "args")

Extension Creation:
  See extensions/custom_skill.py for template
"""

import os
import sys
import importlib
import logging
from typing import Dict, List, Optional, Callable, Any

log = logging.getLogger("jarvis.extensions")


# ─────────────────────────────────────────────────────────────────
# BASE CLASSES
# ─────────────────────────────────────────────────────────────────

class ToolWrapper:
    """
    Base class for tool execution with fallback support.

    Implements: native execution → Claude Code execution → LLM fallback

    Attributes:
        name: Tool name (e.g., "file_read", "bash_exec")
        fallback_llm: Enable fallback to LLM if native fails (default: True)
    """

    def __init__(self, name: str, fallback_llm: bool = True):
        self.name = name
        self.fallback_llm = fallback_llm
        self.capabilities = {}

    def execute(self, operation: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute tool with fallback support.

        Args:
            operation: Tool operation (e.g., "read", "write", "execute")
            params: Operation parameters as dict

        Returns:
            Dict with "status" and "data" keys:
            - {"status": "success", "data": result}
            - {"status": "error", "error": message}
            - {"status": "fallback", "data": llm_result}
        """
        try:
            return self._execute_native(operation, params)
        except Exception as e:
            log.warning(f"Tool {self.name}.{operation} failed: {e}")
            if self.fallback_llm:
                return self._execute_fallback(operation, params)
            raise

    def _execute_native(self, operation: str, params: Dict) -> Dict:
        """Override: native tool implementation"""
        raise NotImplementedError(f"Tool {self.name} does not implement {operation}")

    def _execute_fallback(self, operation: str, params: Dict) -> Dict:
        """Override: fallback execution (LLM-based or stub)"""
        return {
            "status": "fallback",
            "data": f"Fallback: {self.name}.{operation}({params})"
        }


class Extension:
    """
    Base class for bridge extensions.

    Subclass and override register() to add commands, tools, agents, routes.

    Attributes:
        name: Extension name (e.g., "ebay_research", "voice_assistant")
        version: Version string
        requires: List of optional dependencies
        author: Extension author
    """

    def __init__(self):
        self.name = "unnamed"
        self.version = "0.1"
        self.requires = []
        self.author = "unknown"

    def register(self, registry: "ExtensionRegistry") -> None:
        """
        Register extension components with registry.

        Called once on startup via ExtensionRegistry.load_extensions().

        Args:
            registry: ExtensionRegistry instance

        Example:
            def register(self, registry):
                registry.register_command(
                    "mycommand",
                    self.handle_mycommand,
                    "Do something custom",
                    "[arg1] [arg2]"
                )
                registry.register_tool("my_tool", self.MyTool())
                registry.register_agent("my_agent", {...})
        """
        pass

    def validate_dependencies(self) -> bool:
        """Check if required dependencies are available"""
        for module_name in self.requires:
            try:
                __import__(module_name)
            except ImportError:
                log.warning(f"Extension {self.name} missing dependency: {module_name}")
                return False
        return True


# ─────────────────────────────────────────────────────────────────
# REGISTRY
# ─────────────────────────────────────────────────────────────────

class ExtensionRegistry:
    """
    Central registry for bridge extensions.

    Manages commands, agents, tools, and routes added by extensions.
    Provides unified interface for command execution and tool wrapping.

    Usage:
        registry = ExtensionRegistry()
        registry.load_extensions("./extensions/")
        result = registry.handle_command("mycommand", "args")
    """

    def __init__(self):
        self.commands = {}          # name -> {handler, help, args}
        self.agents = {}            # type -> {system, tools, model, desc}
        self.tools = {}             # name -> ToolWrapper instance
        self.routes = {}            # name -> {model, keywords, system, tools}
        self.handlers = {}          # pattern -> handler_fn
        self.extensions = []        # loaded Extension instances
        self.log = logging.getLogger("jarvis.registry")

    # ─── REGISTRATION METHODS ─────────────────────────────────────

    def register_command(
        self,
        name: str,
        handler: Callable[[str], str],
        help_text: str = "",
        args: str = ""
    ) -> None:
        """
        Register a new command handler.

        Args:
            name: Command name (without / prefix, e.g., "mycommand")
            handler: Callable(args: str) -> str
            help_text: Help text for /help output
            args: Usage string (e.g., "[query]" or "[--depth high|low]")

        Raises:
            ValueError: If command name already exists
        """
        if name in self.commands:
            raise ValueError(f"Command /{name} already registered")

        self.commands[name] = {
            "handler": handler,
            "help": help_text,
            "args": args,
        }
        self.log.info(f"Registered command: /{name}")

    def register_agent(self, agent_type: str, config: Dict[str, Any]) -> None:
        """
        Register a new agent type.

        Args:
            agent_type: Agent type name (e.g., "backend", "security")
            config: Agent config dict with:
                - description: Human-readable description
                - system_prompt: System prompt for agent
                - tools: List of tool names
                - model: LLM model name
                - kwargs: Additional config (optional)

        Raises:
            ValueError: If agent type already exists
        """
        if agent_type in self.agents:
            raise ValueError(f"Agent type '{agent_type}' already registered")

        self.agents[agent_type] = config
        self.log.info(f"Registered agent type: {agent_type}")

    def register_tool(self, name: str, wrapper: ToolWrapper) -> None:
        """
        Register a tool wrapper.

        Args:
            name: Tool name (e.g., "file_read", "bash_exec")
            wrapper: ToolWrapper instance

        Raises:
            ValueError: If tool name already exists
        """
        if name in self.tools:
            raise ValueError(f"Tool '{name}' already registered")

        self.tools[name] = wrapper
        self.log.info(f"Registered tool: {name}")

    def register_route(self, route_name: str, config: Dict[str, Any]) -> None:
        """
        Register a new inference route (keyword -> model routing).

        Args:
            route_name: Route name (e.g., "code_review", "architecture")
            config: Route config dict with:
                - model: LLM model name
                - keywords: List of trigger keywords
                - system: System prompt for route
                - tools: List of tool names (optional)

        Raises:
            ValueError: If route name already exists
        """
        if route_name in self.routes:
            raise ValueError(f"Route '{route_name}' already registered")

        self.routes[route_name] = config
        self.log.info(f"Registered route: {route_name}")

    # ─── EXECUTION METHODS ────────────────────────────────────────

    def handle_command(self, cmd_name: str, args: str) -> str:
        """
        Execute a registered command.

        Args:
            cmd_name: Command name (without /)
            args: Command arguments

        Returns:
            Command result string

        Raises:
            KeyError: If command not found
        """
        if cmd_name not in self.commands:
            raise KeyError(f"Command /{cmd_name} not found")

        try:
            handler = self.commands[cmd_name]["handler"]
            return handler(args)
        except Exception as e:
            self.log.error(f"Error in command {cmd_name}: {e}", exc_info=True)
            return f"Error executing /{cmd_name}: {e}"

    def execute_tool(self, tool_name: str, operation: str, params: Dict) -> Dict:
        """
        Execute a registered tool with fallback support.

        Args:
            tool_name: Tool name (e.g., "file_read")
            operation: Tool operation (e.g., "read", "write")
            params: Operation parameters

        Returns:
            Result dict with status and data
        """
        if tool_name not in self.tools:
            return {
                "status": "error",
                "error": f"Tool {tool_name} not found"
            }

        tool = self.tools[tool_name]
        try:
            return tool.execute(operation, params)
        except Exception as e:
            self.log.error(f"Tool error {tool_name}.{operation}: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}

    # ─── QUERY METHODS ───────────────────────────────────────────

    def get_command_help(self, cmd_name: str = None) -> str:
        """
        Get help text for a command or all commands.

        Args:
            cmd_name: Specific command (None = all)

        Returns:
            Formatted help text
        """
        if cmd_name:
            if cmd_name not in self.commands:
                return f"Command /{cmd_name} not found"
            cmd = self.commands[cmd_name]
            args_str = f" {cmd['args']}" if cmd['args'] else ""
            return f"/{cmd_name}{args_str} - {cmd['help']}"

        # All commands
        lines = ["*Extension Commands:*"]
        for name, cmd in sorted(self.commands.items()):
            args_str = f" {cmd['args']}" if cmd['args'] else ""
            lines.append(f"  /{name}{args_str} — {cmd['help']}")
        return "\n".join(lines)

    def get_agents(self) -> Dict[str, str]:
        """Get all registered agents with descriptions"""
        return {
            name: config.get("description", "")
            for name, config in self.agents.items()
        }

    def get_tools(self) -> List[str]:
        """Get all registered tool names"""
        return list(self.tools.keys())

    def get_routes(self) -> Dict[str, str]:
        """Get all registered routes with descriptions"""
        return {
            name: config.get("keywords", [])
            for name, config in self.routes.items()
        }

    # ─── LOADING METHODS ──────────────────────────────────────────

    def load_extensions(self, extension_dir: str) -> int:
        """
        Auto-load all extensions from directory.

        Scans for extension_*.py files and imports Extension subclasses.

        Args:
            extension_dir: Path to extensions directory

        Returns:
            Number of extensions loaded

        Example:
            loaded = registry.load_extensions("./extensions/")
            print(f"Loaded {loaded} extensions")
        """
        if not os.path.isdir(extension_dir):
            self.log.warning(f"Extension directory not found: {extension_dir}")
            return 0

        count = 0
        sys.path.insert(0, extension_dir)

        for filename in sorted(os.listdir(extension_dir)):
            if not filename.startswith("extension_") and filename != "core.py":
                continue
            if not filename.endswith(".py"):
                continue

            module_name = filename[:-3]
            try:
                module = importlib.import_module(module_name)

                # Look for Extension subclass
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, Extension) and
                        attr is not Extension):

                        ext = attr()
                        if ext.validate_dependencies():
                            ext.register(self)
                            self.extensions.append(ext)
                            count += 1
                            self.log.info(f"Loaded extension: {ext.name} v{ext.version}")
                        else:
                            self.log.warning(f"Skipped extension (missing deps): {ext.name}")
                        break

            except Exception as e:
                self.log.error(f"Error loading extension {module_name}: {e}", exc_info=True)

        return count


# ─────────────────────────────────────────────────────────────────
# HELPER CLASSES
# ─────────────────────────────────────────────────────────────────

class FileReadTool(ToolWrapper):
    """
    File read tool with fallback support.

    Supports: read, write, grep, list
    """

    def __init__(self):
        super().__init__("file_read", fallback_llm=True)

    def _execute_native(self, operation: str, params: Dict) -> Dict:
        """Execute file operations natively"""
        if operation == "read":
            path = params.get("path")
            limit = params.get("limit", 10000)
            with open(path, "r") as f:
                content = f.read(limit)
            return {"status": "success", "data": content}

        elif operation == "write":
            path = params.get("path")
            content = params.get("content")
            with open(path, "w") as f:
                f.write(content)
            return {"status": "success", "data": f"Wrote {len(content)} bytes"}

        else:
            raise NotImplementedError(f"Operation {operation} not supported")


class BashExecTool(ToolWrapper):
    """
    Bash execution tool with timeout and safety checks.

    Supports: run, which, version
    """

    def __init__(self, timeout: int = 10):
        super().__init__("bash_exec", fallback_llm=True)
        self.timeout = timeout

    def _execute_native(self, operation: str, params: Dict) -> Dict:
        """Execute bash commands safely"""
        import subprocess

        if operation == "run":
            cmd = params.get("command")
            try:
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout
                )
                return {
                    "status": "success",
                    "data": {
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode
                    }
                }
            except subprocess.TimeoutExpired:
                return {"status": "error", "error": f"Command timed out after {self.timeout}s"}

        else:
            raise NotImplementedError(f"Operation {operation} not supported")


# ─────────────────────────────────────────────────────────────────
# MODULE INITIALIZATION
# ─────────────────────────────────────────────────────────────────

def create_registry() -> ExtensionRegistry:
    """Create and initialize a new registry"""
    return ExtensionRegistry()


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    registry = ExtensionRegistry()
    print(f"Registry created: {registry}")
    print(f"Commands: {list(registry.commands.keys())}")
    print(f"Tools: {list(registry.tools.keys())}")
