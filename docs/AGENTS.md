# Agents (FAZ 1)

## Core Agent (Executive)
- Owns orchestration and final decisions.
- Delegates to sub-agents.
- Enforces policy and quality gates.
- Produces final synthesized output.

## Sub-Agents

### 1) Planner
- Converts goal into task graph.
- Defines dependencies and risks.
- Outputs acceptance criteria.

### 2) Implementer
- Produces implementation artifacts (code/config/design outputs).
- Uses execution skills under restricted permissions.

### 3) Reviewer
- Validates quality, consistency, and edge cases.
- Flags risk and contradiction.

### 4) Memory Curator
- Decides what is persisted to PM/KS.
- Rejects non-reusable/noisy memory writes.

### 5) Operator (Ops)
- Executes operational procedures.
- Handles controlled command workflows.

## Rules
- No sub-agent can self-escalate permissions.
- All skill calls must pass policy checks.
- Every major action must be traceable.
