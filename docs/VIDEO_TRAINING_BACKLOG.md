# Video Training Backlog

This backlog converts `jarvis kaynaklar` clips into actionable Jarvis runtime improvements.

## Current Status
- Ingested videos: 21
- Audio extracted: complete
- Middle frames extracted: complete
- Transcription: placeholder mode (Whisper CLI not installed)

## Immediate Next Tasks
1. Install local transcription runtime (`whisper` or `faster-whisper`).
2. Re-run transcription pass to replace placeholders.
3. Create per-video summary cards:
   - command intent
   - orchestration behavior
   - UI/voice/telegram event patterns
4. Extract reusable automation patterns into skills backlog.

## Skills Backlog Derived From Video Program
- `telegram_command_router`
- `remote_code_task_runner`
- `ecom_market_researcher`
- `shopify_sync_operator`
- `printify_sync_operator`
- `social_media_scheduler`
- `voice_feedback_dispatcher`
- `war_room_status_reporter`

## Governance Backlog
- Secret handling policy (`.env` only, no hardcoded tokens)
- Approval gate for PM/KS writes
- Command allowlist for remote execution
- Audit trail export (`run_id`, `event_id`, `parent_id`)
