# 302 Agents Rollout Plan

Date: 2026-04-13

## Batch 1

Scope:
- canonical package scaffold
- `CanonicalAgent` base
- `PlannerAgent`
- `RepoAnalystAgent`
- `DeveloperAgent`
- `tests/test_canonical_batch1.py`

Validation:
- `python -m pytest tests/test_canonical_batch1.py -v --tb=short`

Deliverable:
- canonical registry exists
- 3 agents runnable
- safe file-write guard in developer agent

## Batch 2

Scope:
- `ReviewerAgent`
- `DebugAgent`
- `tests/test_canonical_batch2.py`

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

Validation:
- `python -m pytest tests/test_canonical_batch3.py -v --tb=short`

Deliverable:
- release/docs output layer
- Turkish TTS summarization layer

## Batch 4

Scope:
- `MissionControlAgent`
- `tests/test_canonical_batch4.py`

Validation:
- `python -m pytest tests/test_canonical_batch4.py -v --tb=short`

Deliverable:
- canonical health aggregation over JSONL history

## Integration Pass

Scope:
- `server/bridge.py`
  - `POST /agent`
  - canonical keyword dispatch in `process_message()`
- `hey_jarvis.py`
  - `VoiceNarratorAgent` hook
- `OPS/308_HANDOFF.md`

Validation:
- targeted pytest for canonical tests
- smoke import for 9 registered agents
- smoke `planner`, `voice_narrator`, `mission_control`

## CLAUDE.md Update Policy

After each of the following phases:
- Plan artifacts
- Batch 1
- Batch 2
- Batch 3
- Batch 4
- Integration/final handoff

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
