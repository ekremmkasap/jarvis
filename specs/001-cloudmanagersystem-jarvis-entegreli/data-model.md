# Data Model: CloudManagerSystem

**Phase**: 1 — Design
**Date**: 2026-04-12

---

## Entities

### CloudProvider

Desteklenen cloud sağlayıcı yapılandırması. v1'de yalnızca AWS aktif.

| Alan | Tip | Açıklama |
|------|-----|----------|
| `name` | string | "aws" / "gcp" / "azure" |
| `enabled` | bool | Aktif mi? (v1: yalnızca aws=True) |
| `region` | string | Varsayılan bölge (ör. "us-east-1") |
| `credential_source` | string | "env" (`.env` dosyası) |

**Validation**: `name` `["aws", "gcp", "azure"]` içinde olmalı.

---

### CloudResource

Bir cloud kaynağını temsil eder (EC2 instance veya S3 bucket).

| Alan | Tip | Açıklama |
|------|-----|----------|
| `resource_id` | string | AWS kaynak ID (ör. "i-0abc1234", "my-bucket") |
| `resource_type` | enum | "ec2" \| "s3" |
| `name` | string | Kaynak etiketi/adı (Name tag veya bucket adı) |
| `region` | string | AWS bölgesi |
| `state` | enum | "running" \| "stopped" \| "pending" \| "unknown" (EC2); "active" (S3) |
| `provider` | string | "aws" |
| `last_updated` | ISO8601 | Son sorgulama zamanı |

**State Transitions (EC2)**:
```
stopped  →  [start_instance]  →  pending  →  running
running  →  [stop_instance]   →  stopping →  stopped
```
Bridge bu geçişi tetikler; nihai durum AWS'den polling ile doğrulanır.

---

### CostRecord

Aylık maliyet verisi (önbelleklenmiş).

| Alan | Tip | Açıklama |
|------|-----|----------|
| `provider` | string | "aws" |
| `period` | string | "YYYY-MM" formatı (ör. "2026-04") |
| `total_usd` | float | Dönem toplam maliyeti (USD) |
| `breakdown` | dict | Servis bazlı döküm `{"EC2": 12.5, "S3": 0.3, ...}` |
| `fetched_at` | ISO8601 | Cache güncellenme zamanı |
| `is_stale` | bool | 24 saatten eski ise True |

**Cache Dosyası**: `server/data/cloud_cost_cache.json`
**Güncelleme Frekansı**: 24 saatte bir (ilk çağrı veya cache yoksa anında)

---

### CostAlert

Kullanıcının tanımladığı maliyet eşiği.

| Alan | Tip | Açıklama |
|------|-----|----------|
| `threshold_usd` | float | Eşik tutarı (USD) |
| `provider_scope` | string | "aws" \| "all" |
| `notify_channel` | string | "telegram" (sabit, v1) |
| `last_triggered_at` | ISO8601 \| null | Son uyarı zamanı (tekrar spam önleme) |
| `cooldown_hours` | int | Aynı eşik için minimum uyarı aralığı (varsayılan: 24) |

**Depolama**: `.env` içinde `CLOUD_COST_ALERT_USD=500` olarak; runtime'da parse edilir.
**Cooldown kuralı**: Aynı eşik için 24 saat içinde en fazla 1 Telegram bildirimi gönderilir.

---

### CloudCommand

Gelen Telegram komutu ve işlem kaydı (log amaçlı).

| Alan | Tip | Açıklama |
|------|-----|----------|
| `raw_text` | string | Kullanıcının yazdığı ham metin |
| `parsed_action` | enum | "list_ec2" \| "start_ec2" \| "stop_ec2" \| "list_s3" \| "cost_query" \| "set_alert" \| "unknown" |
| `target_resource_id` | string \| null | Hedef kaynak ID (varsa) |
| `result_summary` | string | Kullanıcıya dönen yanıt (kısaltılmış) |
| `success` | bool | İşlem başarılı mı? |
| `timestamp` | ISO8601 | Komut zamanı |
| `error_message` | string \| null | Hata varsa mesaj (redacted) |

**Log Dosyası**: `server/logs/cloud_commands.jsonl` (satır başına 1 JSON)
**Redaction**: `error_message` ve `result_summary` alanlarında AWS kimlik bilgileri maskelenir.

---

## Cost Cache Schema (cloud_cost_cache.json)

```json
{
  "aws": {
    "period": "2026-04",
    "total_usd": 14.82,
    "breakdown": {
      "Amazon EC2": 12.50,
      "Amazon S3": 0.32,
      "AWS Cost Explorer": 0.00
    },
    "fetched_at": "2026-04-12T08:00:00Z",
    "is_stale": false
  }
}
```

---

## Alert State Schema (cloud_alert_state.json)

```json
{
  "threshold_usd": 500.0,
  "last_triggered_at": null,
  "cooldown_hours": 24
}
```

**Depolama**: `server/data/cloud_alert_state.json` (runtime'da otomatik oluşturulur)
