# Memory Model (FAZ 2 - OpenViking Context DB Integration)

## Layers (Hierarchical File-System Paradigm)

### Working Memory (WM)
- Ephemeral, run-scoped context dynamically managed like an OS RAM process.
- Temporary plans, notes, intermediate artifacts.
- Archived or discarded after run completion.

### Project Memory (PM)
- Long-term project rules, decisions, standards, conventions.
- Modeled hierarchically (Directory-tree scaling pattern per OpenViking architecture).

### Knowledge Store (KS) / Context Graph
- Structured reference summaries, snippets, templates, standards.
- Uses Interactive Knowledge Graph mapping (inspired by GitNexus).
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
