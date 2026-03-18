# Skills Specification (FAZ 1)

## Definition
A skill is a small, testable, reusable unit with deterministic behavior and observable logs.

## Skill Categories
- Cognitive: planning, requirement parsing, risk assessment
- Execution: writing files, running tests, command execution
- IO: read/parse/transform data
- Governance: policy checks, approvals, redaction

## Skill Manifest Contract
Each skill must define:
- `name`
- `version`
- `input_schema`
- `output_schema`
- `permissions`
- `failure_modes`
- `emitted_events`

## Skill Invocation Record
- `skill_name`
- `args`
- `result`
- `side_effects`
- `logs`

## Quality Rules
- Fail fast on invalid input schema.
- Emit structured error data on failure.
- Never perform side effects outside declared permissions.
