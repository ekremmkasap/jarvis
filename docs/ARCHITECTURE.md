# Jarvis / Mission Control Architecture (FAZ 1)

## Goal
Build a modular, extensible, auditable core runtime using:
- Core Agent
- Sub-agents
- Skills
- Memory
- State and observability

## High-Level Components
1. Mission Control (Orchestrator)
   - Translates user intent into tasks.
   - Plans, dispatches, executes, retries, and finalizes.
2. Core Agent (Executive)
   - Single decision authority.
   - Applies policy, quality gates, and synthesis.
3. Sub-Agents
   - Role-specific specialists (planner, implementer, reviewer, ops, curator).
   - Restricted capability scope.
4. Skills
   - Small deterministic units: input -> process -> output (+logs).
5. Memory
   - Working Memory (WM), Project Memory (PM), Knowledge Store (KS).
6. State + Observability
   - Task lifecycle, events, artifacts, decision records.

## Runtime Flow
`Intake -> Clarify -> Plan -> Dispatch -> Execute -> Review -> Synthesize -> Memory Update`

## State Machine
- Normal: `queued -> planning -> running -> reviewing -> done`
- Error: `running -> blocked | failed`
- External dependency: `waiting`

## Security and Governance
- Capability-based permissions per agent and skill.
- Policy gate before sensitive operations.
- Audit trail for significant decisions.

## MVP Core
- Core + Planner + Implementer + Reviewer
- Memory curation can be embedded in Core initially.
