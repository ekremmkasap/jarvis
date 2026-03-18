# Phase 2 Modules (Implemented)

## 1) AutoUploader Module
- Skill: `auto_uploader`
- File: `src/runtime/skills/builtins/auto_uploader.ts`
- Purpose: Prepare platform upload queues for TikTok/Reels.
- Modes:
  - `ghost`: browser automation strategy
  - `api`: official API strategy
- Safe default: `dryRun: true` for simulation-first workflow.

## 2) Dynamic Content Shuffler
- Skill: `dynamic_content_shuffler`
- File: `src/runtime/skills/builtins/dynamic_content_shuffler.ts`
- Purpose: Build unique segment plans from raw clip library.
- Deterministic by seed for reproducibility.
- Output contains per-video segment map and uniqueness hash.

## 3) Engagement Loop
- Skill: `engagement_loop`
- File: `src/runtime/skills/builtins/engagement_loop.ts`
- Purpose: Build bounded interaction plans across personas.
- Actions: `follow`, `comment`, `boost`.
- Deterministic by seed and bounded by `maxActionsPerPersona`.

## Demo Entry
- File: `src/runtime/dev/run.ts`
- Includes sequential execution of all 3 modules after core checks.
