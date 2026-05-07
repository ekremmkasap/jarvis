---
tags: [project, aws, cloud, planning]
date: 2026-04-16
status: spec-ready
---

# CloudManagerSystem

AWS EC2/S3 yönetimi + maliyet tracker + Telegram komutları + web UI dashboard.

## Durum: Spec/Plan Hazır, Implementation Bekliyor

## Artifact'ler
- **Branch**: `001-cloudmanagersystem-jarvis-entegreli`
- **Spec**: `specs/001-cloudmanagersystem-jarvis-entegreli/spec.md`
- **Plan**: `specs/001-cloudmanagersystem-jarvis-entegreli/plan.md`

## Sonraki Adım
`/speckit.tasks` → sonra `/speckit.implement`

## Kapsam
- AWS EC2 start/stop/status
- S3 bucket listeleme + upload
- Maliyet tracker (daily/monthly)
- Telegram komutları: `/aws-ec2`, `/aws-s3`, `/aws-cost`
- Web UI dashboard (apps/web-ui)

## Güvenlik
AWS key'ler `.env`'de, loga/UI'a sızmaz. Redaction helper `server/bridge.py`'de.

## Bağlantılar
- [[jarvis-mission-control]] — ana repo
- [[06-Architecture/system-overview]]
