# Source Intelligence (Video Batch)

## Inputs Processed
- Source folder: `C:\Users\sergen\Desktop\jarvis kaynaklar`
- Video files: 21
- Total runtime: ~13.93 min

## Derived Data
- Manifest: `C:\Users\sergen\Desktop\jarvis kaynaklar\processed\manifest.json`
- Transcripts: `C:\Users\sergen\Desktop\jarvis kaynaklar\processed\transcripts\`
- Analysis report: `C:\Users\sergen\Desktop\jarvis kaynaklar\processed\TRAINING_REPORT.md`
- Pattern set: `C:\Users\sergen\Desktop\jarvis kaynaklar\processed\patterns.json`

## Key Signals
- Highest signal topic: content pipeline and social/video workflow
- Secondary signal: voice UI / dashboard feedback loop
- Operational signal: coding and ecommerce automation present
- Telegram/command signal exists and should be formalized into controlled command routing

## Runtime Backlog (Phase 2 Build)
1. `telegram_command_router` with allowlist and audit trail
2. `remote_code_task_runner` with sandboxed command policy
3. `ecom_market_researcher` with structured report output
4. `shopify_sync_operator` and `printify_sync_operator` (separate adapters)
5. `social_media_scheduler` with templated caption/media pipeline
6. `voice_feedback_dispatcher` integrated into event pipeline
7. `dashboard_telemetry_bridge` for trace-to-panel projection

## Security Baseline
- Do not hardcode bot/API tokens.
- Use `.env` + runtime secret loader only.
- Rotate any token previously exposed in chat or source history.
