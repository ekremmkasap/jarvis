# State Model (FAZ 1)

## Core Entities

### Task
- `id`, `title`, `goal`, `constraints`, `inputs`, `acceptance_criteria`
- `status`: `queued | planning | running | waiting | blocked | done | failed | cancelled`
- `plan`, `artifacts`, `events`

### Run
- Execution session for a task.
- Captures reproducibility metadata (model/config/skill versions).

### Agent Call
- Core -> Sub-agent interaction record.
- Includes role, prompt, inputs/outputs, trace id.

### Skill Invocation
- Agent -> Skill execution record.
- Includes args, result, side effects, logs.

## Lifecycle
- Happy path: `queued -> planning -> running -> reviewing -> done`
- Exception path: `running -> blocked | failed`
- External dependency path: `running -> waiting`

## Event Requirements
- Structured event IDs
- Trace correlation (`trace_id`, optional `parent_id`)
- Timestamps
- Decision reason for policy or quality gate outcomes
