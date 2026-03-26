# Jarvis Mission Control - Architecture

## Canonical Runtime
- **Gateway**: `server/bridge.py` - web, Telegram, and command intake
- **Agent OS Runtime**: `server/agent_os/runtime.py` - route selection, department loading, context packet assembly
- **Team Orchestrator**: `server/core/team_orchestrator.py` - planner -> builder -> guard -> research -> synthesizer workflow
- **Department Workspace**: `server/agent_workspace/departments/*` - AGENT, MEMORY, and skill files per department
- **Team Agents**: `server/agents/*.py` - execution roles used by the orchestrator

## Main Flow
Intake -> Route -> Department Context -> Planning -> Build -> Guard -> Synthesis -> Memory

## Department Model
- `assistant` - intake, routing, executive framing
- `builder` - implementation and code-first outputs
- `guard` - security and logic review
- `research` - comparisons and architecture choices
- `marketing` - campaign/content workflows
- `sales` - offer and outreach workflows

## Key Files
- `server/config/department_manifest.json`
- `server/config/team_config.json`
- `server/logs/team_audit.jsonl`
- `server/memory/working_memory/team_tasks.jsonl`

## Notes
- `server/bridge.py` remains the active Windows runtime.
- `/team` is now backed by the Agent OS runtime rather than a thin direct orchestrator call.
- Department context is file-based so the system can evolve toward AgentClaw-style context engineering.
- Pinokio launcher compatibility is no longer a primary design goal; the runtime is a standalone local Python service.
- `C:\pinokio\api\ekrem\app` is treated as a donor source for prompts and patterns only.
