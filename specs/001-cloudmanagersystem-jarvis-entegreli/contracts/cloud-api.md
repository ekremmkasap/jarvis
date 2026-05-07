# Contract: Web UI → Bridge HTTP API

**Version**: 1.0 | **Date**: 2026-04-12
**Base URL**: `http://127.0.0.1:5001`

Web UI (`apps/web-ui`) bu endpoint'leri kullanarak cloud verilerini gösterir ve aksiyonları tetikler.

---

## GET /api/cloud/resources

Tüm cloud kaynaklarını döner (EC2 + S3).

**Response** `200 OK`:
```json
{
  "provider": "aws",
  "region": "us-east-1",
  "fetched_at": "2026-04-12T10:30:00Z",
  "ec2": [
    {
      "id": "i-0abc1234",
      "name": "web-server",
      "state": "running",
      "type": "t3.micro",
      "region": "us-east-1"
    }
  ],
  "s3": [
    {
      "name": "my-bucket",
      "region": "us-east-1",
      "object_count": 142,
      "size_mb": 512.4
    }
  ]
}
```

**Error** `503`:
```json
{
  "error": "aws_unavailable",
  "message": "AWS bağlantısı kurulamadı."
}
```

---

## GET /api/cloud/costs

Aylık maliyet özetini döner (cache'den).

**Response** `200 OK`:
```json
{
  "provider": "aws",
  "period": "2026-04",
  "total_usd": 14.82,
  "breakdown": {
    "Amazon EC2": 12.50,
    "Amazon S3": 0.32
  },
  "fetched_at": "2026-04-12T08:00:00Z",
  "is_stale": false,
  "alert_threshold_usd": 500.0
}
```

---

## POST /api/cloud/action

EC2 başlat/durdur aksiyonlarını tetikler.

**Request body**:
```json
{
  "action": "start" | "stop",
  "resource_type": "ec2",
  "resource_id": "i-0abc1234"
}
```

**Response** `200 OK`:
```json
{
  "success": true,
  "resource_id": "i-0abc1234",
  "new_state": "pending",
  "message": "Instance başlatılıyor: i-0abc1234"
}
```

**Response** `400` (geçersiz aksiyon):
```json
{
  "success": false,
  "error": "invalid_action",
  "message": "Bilinmeyen aksiyon: restart"
}
```

**Response** `403` (yetki hatası):
```json
{
  "success": false,
  "error": "access_denied",
  "message": "Bu kaynağa erişim izniniz yok."
}
```

---

## Güvenlik Notları

- Bu endpoint'ler yalnızca localhost'a bağlı (127.0.0.1); dışarıya açık değil.
- Response body'de hiçbir zaman `AWS_SECRET_ACCESS_KEY` veya `AWS_ACCESS_KEY_ID` değerleri yer almaz.
- Aksiyon endpoint'leri rate-limit uygulamaz (tek kullanıcı); ileride multi-tenant'a geçişte eklenmeli.
