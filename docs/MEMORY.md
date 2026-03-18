# Memory Model (FAZ 1)

## Layers

### Working Memory (WM)
- Ephemeral, run-scoped context.
- Temporary plans, notes, intermediate artifacts.
- Archived or discarded after run completion.

### Project Memory (PM)
- Long-term project rules, decisions, standards, conventions.
- Equivalent to project memory docs (`MISSION.md`, `MEMORY.md`).

### Knowledge Store (KS)
- Structured reference summaries, snippets, templates, standards.
- Indexed by tags/source/date.

## Memory Gate Policy
Not all data should be persisted.

Persist to PM/KS only if:
- Reusable
- Strategic
- Project-governing
- Versionable or policy-relevant

Otherwise keep in WM.

## Curator Questions
- Will this be needed again?
- Is this project-specific or general knowledge?
- Should this be versioned or reviewed?
