# Implementation Plan: CloudManagerSystem — Jarvis Cloud Yönetim Skill'i

**Branch**: `001-cloudmanagersystem-jarvis-entegreli` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)

## Summary

Jarvis'e `/cloud` komutu üzerinden AWS kaynaklarını (EC2, S3) Telegram'dan yönetme, maliyet sorgulama ve otomatik eşik uyarısı yeteneği kazandırılacak. Skill `server/skills/cloud_manager_skill.py` olarak eklenir, `bridge.py`'a minimal `elif command == "/cloud"` bloğu eklenerek mevcut handler zinciri korunur. Web UI'a `/cloud` route'u eklenerek dashboard paneli sunulur.

## Technical Context

**Language/Version**: Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui)
**Primary Dependencies**: boto3 (AWS SDK), python-dotenv (hâlihazırda mevcut), requests (mevcut)
**Storage**: `.env` — kimlik bilgileri; `server/data/cloud_cost_cache.json` — maliyet önbelleği (günlük)
**Testing**: Manuel smoke test (boto3 mock veya localstack opsiyonel)
**Target Platform**: Windows 10 local — Jarvis bridge.py HTTP server (port 5001), web-ui (port 8081)
**Project Type**: Jarvis skill (Python) + web-ui panel (Next.js)
**Performance Goals**: Telegram yanıt < 10s, web dashboard yükleme < 3s
**Constraints**: AWS anahtarları log/UI payload/event'e sızmaz (Constitution III); bridge.py backward-safe; boto3 yoksa graceful fallback
**Scale/Scope**: Tek kullanıcı (Ekrem), v1 yalnızca AWS

## Constitution Check

*GATE: Faz 0'dan önce geçmesi zorunlu. Faz 1 tasarımı sonrası tekrar kontrol.*

| Prensip | Durum | Notlar |
|---------|-------|--------|
| I. Local-First | ✅ PASS | Skill local çalışır; cloud çağrısı özelliğin kendisi, kaçınılmaz |
| II. Spec Before Impl | ✅ PASS | specify → plan → tasks → implement zinciri izleniyor |
| III. Security/Redaction | ⚠️ GATE | AWS_SECRET_ACCESS_KEY log/UI/event'e yazılmamalı; tüm log satırlarında redaction zorunlu |
| IV. Read Before Write | ✅ PASS | bridge.py ve skill pattern okunundu |
| V. Verify Before Done | ⚠️ GATE | Smoke test kanıtı: boto3 bağlantısı + /cloud komut çıktısı gösterilmeli |

**Gate Actions**:
- `cloud_manager_skill.py` içinde tüm log çağrılarında `AWS_SECRET_ACCESS_KEY` ve `AWS_ACCESS_KEY_ID` değerleri `***REDACTED***` ile maskelenmeli.
- Bridge'e eklenen `/cloud` bloğu mevcut komutların sırasını değiştirmemeli.

## Project Structure

### Documentation (this feature)

```text
specs/001-cloudmanagersystem-jarvis-entegreli/
├── plan.md              # Bu dosya
├── research.md          # Faz 0 — kararlar ve alternatifler
├── data-model.md        # Faz 1 — entity ve state modeli
├── contracts/
│   ├── cloud-commands.md   # Telegram komut şeması
│   └── cloud-api.md        # Web UI → bridge HTTP API
└── tasks.md             # /speckit.tasks komutu çıktısı (sonraki faz)
```

### Source Code (repository root)

```text
server/
├── skills/
│   └── cloud_manager_skill.py      # YENİ — AWS EC2/S3/Cost skill
├── bridge.py                       # DEĞİŞİKLİK — +/cloud elif bloğu, +/api/cloud/* endpoint
└── data/
    └── cloud_cost_cache.json       # YENİ — otomatik oluşturulur (runtime)

apps/web-ui/src/
├── app/
│   └── cloud/
│       └── page.tsx                # YENİ — Cloud dashboard route
└── components/
    └── CloudDashboard.tsx          # YENİ — kaynak kartları + maliyet özeti
```

**Structure Decision**: Mevcut skill pattern (`server/skills/*.py`) korunur. Bridge'e ekleme minimumdur: tek `elif command == "/cloud"` bloğu + iki HTTP endpoint. Web UI mevcut Next.js app router yapısına yeni bir segment olarak eklenir.

## Complexity Tracking

> Yalnızca Constitution ihlali varsa doldurulur

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Dış ağ bağımlılığı (boto3/AWS API) | Özelliğin kendisi cloud yönetimi | Lokalde çalıştırılamaz; tek makul seçenek |
| Arka plan thread (maliyet polling) | 15dk eşik uyarısı için periyodik kontrol | Webhook/push AWS'den desteklenmiyor (Cost Explorer pull-based) |
