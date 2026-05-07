---
name: jarvis-agent-generator
description: "Use when: creating new Jarvis agents, skills, or Codex runtime components. Generates canonical agent/skill structure with proper type hints, error handling, state management, and test stubs. Includes bridge integration hooks and Telegram command routing."
agent: "agent"
argument-hint: "Create a [type] called [name] that [does what]"
tags: [agents, skills, codex, python]
applyTo: ["server/agents/**", "server/skills/**"]
---

# Jarvis Agent & Skill Generator

You are generating new agent or skill code for the Jarvis Mission Control system.

## Agent/Skill Context

The Jarvis ecosystem has:
- **Agents**: Autonomous units in `server/agents/canonical/` with model chains (reasoning, code, chat, default)
- **Skills**: Reusable capabilities in `server/skills/` with registry entries
- **Codex Slots**: Execution environments (forge, nexus, spark, shield, atlas) managed by `codex_orchestrator.py`
- **Bridge**: FastAPI router at `server/bridge.py` that dispatches to agents/skills
- **State**: Per-agent memory in `state/agent_memory/`

## What to Generate

When given a component request (e.g., "create a security auditing agent" or "add an EC2 metrics skill"):

1. **Structure**
   - Use canonical class names: `{Name}Agent` or `{Name}Skill`
   - Inherit from `RuntimeAgent` (agents) or `BaseSkill` (skills)
   - Set `name`, `description`, `model_chain`, `risk_level`
   - Implement core methods with type hints (Python 3.11)

2. **Core Methods**
   - `execute_task(self, task: dict) -> str` — main entry point
   - `_validate_input(self, task: dict) -> bool` — guard clauses
   - `_log_action(self, message: str, level: str = "info")` — structured logging
   - Return JSON or plain text as specified

3. **Error Handling**
   - Try/except with specific exceptions (not bare `except`)
   - Log errors to `state/logs/{agent_name}.log`
   - Graceful fallbacks for API failures

4. **State Management**
   - Read/write to `state/agent_memory/{agent_name}/` for persistence
   - Use JSON for state files, never pickle
   - Include `remember()` and `recall()` helpers if stateful

5. **Bridge Integration** (if needed)
   - Add route to `server/bridge.py` under `/api/agents/{name}` or `/agent/{command}`
   - Redact sensitive fields before returning to operator
   - Add Telegram command handler if agent is user-facing

6. **Tests**
   - Create `tests/test_{agent_name}.py` with minimal fixtures
   - Cover happy path, error cases, state persistence
   - Use `pytest` with `--tb=short` format
   - Target 80%+ coverage

7. **Documentation**
   - Docstring for class + each public method
   - Example input/output in docstring
   - List required environment variables (AWS keys, API tokens, etc.)

## Model Chain Guidance

| Chain | Use When | Examples |
|-------|----------|----------|
| `reasoning` | Planning, analysis, decision trees | PlannerAgent, DebugAgent, MissionControlAgent |
| `code` | Repository tasks, code review, implementations | DeveloperAgent, ReviewerAgent |
| `chat` | User interaction, summaries, announcements | VoiceNarratorAgent, assistant-style tasks |
| `default` | General purpose, fallback | DocsAgent, ReleaseAgent |

## Risk Level Policy

- **Low**: Read-only, no side effects → auto-approve
- **Medium**: Changes files/state, no destructive ops → requires review
- **High**: Destructive, credentials, production → blocked by policy

## Canonical Example

```python
from typing import Optional
import json
import logging
from pathlib import Path

class SecurityAuditAgent:
    """Audits codebase for security vulnerabilities."""
    
    name = "security_audit"
    description = "Scans Python files for hardcoded secrets, unsafe imports, injection risks."
    model_chain = "reasoning"
    risk_level = "low"
    
    def __init__(self):
        self.memory_dir = Path("state/agent_memory/security_audit")
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(self.name)
    
    def execute_task(self, task: dict) -> str:
        """
        Execute security audit.
        
        Input:
            {"goal": "audit", "context": {"repo_path": ".", "file_pattern": "**/*.py"}}
        
        Output:
            JSON with findings, severity, remediation steps.
        """
        if not self._validate_input(task):
            return json.dumps({"error": "Invalid task format"})
        
        try:
            repo_path = task.get("context", {}).get("repo_path", ".")
            self._log_action(f"Starting audit on {repo_path}")
            
            # Main logic here
            findings = self._scan_files(repo_path)
            
            # Persist results
            self.remember({"last_audit": findings})
            
            return json.dumps({
                "status": "complete",
                "findings_count": len(findings),
                "findings": findings
            })
        except Exception as e:
            self._log_action(f"Audit failed: {str(e)}", "error")
            return json.dumps({"error": str(e)})
    
    def _validate_input(self, task: dict) -> bool:
        return isinstance(task, dict) and "goal" in task
    
    def _log_action(self, message: str, level: str = "info") -> None:
        getattr(self.logger, level)(message)
    
    def _scan_files(self, repo_path: str) -> list:
        # Implementation
        return []
    
    def remember(self, data: dict) -> None:
        """Persist state to memory."""
        state_file = self.memory_dir / "state.json"
        with open(state_file, "w") as f:
            json.dump(data, f)
    
    def recall(self) -> dict:
        """Retrieve persisted state."""
        state_file = self.memory_dir / "state.json"
        if state_file.exists():
            with open(state_file, "r") as f:
                return json.load(f)
        return {}
```

## After Generation

- Place file in correct location (`server/agents/` or `server/skills/`)
- Register in `server/agents/registry.py` or `server/skills/registry.py`
- Add config entry to `config/agents.yaml` or skill config
- Create test file in `tests/`
- Update `CLAUDE.md` handoff section if new capability
- Run: `cd src; pytest tests/test_{name}.py -v --tb=short`

## Örnek Kullanımlar

### 1. Yeni Agent Oluştur
```
/jarvis-agent-generator
Create an agent called DataQualityAgent that validates data pipelines and reports anomalies.
Risk level: low, model chain: reasoning
```

### 2. Yeni Skill Oluştur
```
/jarvis-agent-generator
Create a skill for AWS Lambda management. Should list, invoke, and monitor Lambda functions.
Include Telegram command: /lambda-durum
```

### 3. Codex Slot Bileşeni
```
/jarvis-agent-generator
Create a runtime component for the 'shield' Codex slot that monitors security events.
Should integrate with bridge.py and emit alerts to active_agent.json
```

## İlişkili Promptlar & Dosyalar

- [AGENTS.md](../../../AGENTS.md) — Agent katalog ve davranış referansı
- [CLAUDE.md](../../../CLAUDE.md) — Proje geliştirme kılavuzu ve teknoloji yığını
- [server/agents/registry.py](../../../server/agents/registry.py) — Agent kaydı
- [server/bridge.py](../../../server/bridge.py) — FastAPI router ve Telegram bağlantısı
- [tests/](../../../tests/) — Test örnekleri ve fixture'lar

---

**Version:** 2.0 | **Last Updated:** 2026-04-23
