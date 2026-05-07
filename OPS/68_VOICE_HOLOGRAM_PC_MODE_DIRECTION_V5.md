# OPS/68_VOICE_HOLOGRAM_PC_MODE_DIRECTION_V5

Tarih: 2026-04-04

## Truth
- Voice surface baselinede reliable tarafta ama interruption issue kapanmis degil.
- User hedefi acikca “Jarvis erken kesmeyi biraksin” oldugu icin mevcut acceptance claim’i yok.
- `external-repos/Mark-XXXV` voice continuity ve PC-control gating icin local donor olarak mevcut.
- Microsoft voice assistant style dedike local donor bu sprintte bulunmadi.

## Direction
- Listening / speaking / thinking / muted state machine runtime event seviyesinde izlenmeli.
- Mute / stop-speaking / push-to-talk controls operator-visible olmalı.
- PC-mode high-risk lane olarak explicit confirmation, allowlist, action log ve emergency stop gerektirir.

