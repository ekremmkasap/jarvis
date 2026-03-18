# Jarvis Mission Control - Architecture (FAZ 1)

## Sistem Bilesenleri
- **Mission Control (Orchestrator)**: orchestrator.py - istekleri Task'a ceviren katman
- **Core Agent**: core/agent.py - tek karar verici, state machine, policy gate
- **Sub-Agents**: planner / implementer / reviewer
- **Skills**: cognitive / execution / io / governance
- **Memory**: working_memory (anlık) / project_memory (kalici) / knowledge_store

## Akis
Intake -> Policy Check -> Planning -> Running -> Reviewing -> Synthesize -> Memory Update

## Dizin Yapisi
/opt/jarvis/
  core/          - agent.py, orchestrator.py
  agents/        - planner, implementer, reviewer
  skills/        - cognitive, execution, io, governance
  memory/        - working_memory, project_memory, knowledge_store
  config/        - konfigurasyonlar
  logs/          - agent.log, audit.jsonl
