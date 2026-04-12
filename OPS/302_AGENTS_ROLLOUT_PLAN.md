# 302 Agents Rollout Plan

Date: 2026-04-13

## Plan Phase

Scope:
- read `AGENTS.md`
- audit runtime integration points
- refresh `OPS/300_AGENTS_AUDIT.md`
- refresh `OPS/301_AGENTS_IMPLEMENTATION_PLAN.md`
- refresh `OPS/302_AGENTS_ROLLOUT_PLAN.md`

Deliverable:
- planning artifacts reflect the real repository state
- batch1 identified as already present in `server/agents/canonical/`

## Batch 1

Scope:
- validate existing canonical package scaffold
- validate `CanonicalAgent` base
- validate `PlannerAgent`
- validate `RepoAnalystAgent`
- validate `DeveloperAgent`
- validate `tests/test_canonical_batch1.py`

Validation:
- `python -m pytest tests/test_canonical_batch1.py -v --tb=short`

Deliverable:
- batch1 confirmed green before further implementation

## Batch 2

Scope:
- `ReviewerAgent`
- `DebugAgent`
- `tests/test_canonical_batch2.py`
- registry update

Validation:
- `python -m pytest tests/test_canonical_batch2.py -v --tb=short`

Deliverable:
- read-only review flow
- root-cause analysis agent

## Batch 3

Scope:
- `ReleaseAgent`
- `DocsAgent`
- `VoiceNarratorAgent`
- `tests/test_canonical_batch3.py`
- registry update

Validation:
- `python -m pytest tests/test_canonical_batch3.py -v --tb=short`

Deliverable:
- release/docs output layer
- Turkish TTS summarization layer

## Batch 4

Scope:
- `MissionControlAgent`
- `tests/test_canonical_batch4.py`
- registry update to 9 agents

Validation:
- `python -m pytest tests/test_canonical_batch4.py -v --tb=short`

Deliverable:
- canonical health aggregation over JSONL history

## Integration Pass

Scope:
- `server/bridge.py`
  - `POST /agent`
  - canonical keyword dispatch in natural-language flow
- `hey_jarvis.py`
  - `VoiceNarratorAgent` hook
- `OPS/308_HANDOFF.md`

Validation:
- targeted pytest for canonical tests
- smoke import for 9 registered agents
- smoke calls for `planner`, `voice_narrator`, and `mission_control`

## CLAUDE.md Update Policy

After each phase:
- plan artifacts
- batch1 validation
- batch2
- batch3
- batch4 + integration + final handoff

Update section:
- `### AGENTS.md 9-Agent Canonical (Tab-3 Codex Sprint)`

Fields to maintain:
- `Durum`
- `Tamamlanan`
- `Kalan`
- `Sonraki Adim`

Commit policy:
- implementation commit for the phase
- separate `CLAUDE.md` progress commit immediately after
