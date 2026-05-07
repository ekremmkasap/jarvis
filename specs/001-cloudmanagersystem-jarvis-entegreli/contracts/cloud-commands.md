# Contract: Telegram Cloud Komut Şeması

**Version**: 1.0 | **Date**: 2026-04-12

Tüm komutlar `/cloud` prefix'iyle başlar ve Jarvis `handle_command` tarafından `cloud_manager_skill.handle(args)` fonksiyonuna yönlendirilir.

---

## Komut Listesi

### EC2 İşlemleri

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `/cloud ec2 listele` | Tüm EC2 instance'larını listeler | `/cloud ec2 listele` |
| `/cloud ec2 baslat <id>` | Instance başlatır | `/cloud ec2 baslat i-0abc1234` |
| `/cloud ec2 durdur <id>` | Instance durdurur | `/cloud ec2 durdur i-0abc1234` |
| `/cloud ec2 durum <id>` | Tek instance durumu | `/cloud ec2 durum i-0abc1234` |

### S3 İşlemleri

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `/cloud s3 listele` | Tüm bucket'ları listeler | `/cloud s3 listele` |
| `/cloud s3 dosyalar <bucket>` | Bucket içindeki son 20 dosya | `/cloud s3 dosyalar my-bucket` |

### Maliyet & Uyarılar

| Komut | Açıklama | Örnek |
|-------|----------|-------|
| `/cloud maliyet` | Bu aylık toplam harcama | `/cloud maliyet` |
| `/cloud uyari-ayarla <usd>` | Maliyet uyarı eşiği ayarla | `/cloud uyari-ayarla 500` |
| `/cloud uyari-goster` | Mevcut eşik ve durum | `/cloud uyari-goster` |

### Yardım

| Komut | Açıklama |
|-------|----------|
| `/cloud yardim` | Tüm komutları listeler |

---

## Yanıt Formatı

### Başarılı yanıt

```
✅ EC2 Instance Listesi (3 kaynak)
─────────────────────────────
i-0abc1234 | web-server | 🟢 running | us-east-1
i-0def5678 | db-backup  | 🔴 stopped | us-east-1
i-0ghi9012 | staging    | 🔴 stopped | eu-west-1
```

### Hata yanıtı

```
❌ Hata: i-0abc1234 bulunamadı veya erişim izni yok.
Komut: /cloud ec2 baslat
```

### Maliyet yanıtı

```
💰 AWS Maliyet Özeti — Nisan 2026
─────────────────────────────────
Amazon EC2:   $12.50
Amazon S3:     $0.32
─────────────────────
Toplam:       $14.82
─────────────────────
⚠️ Veri: 2026-04-12 08:00 UTC (güncel)
```

### Maliyet uyarı bildirimi (otomatik)

```
🚨 Jarvis Maliyet Uyarısı!
AWS harcaması $14.82 oldu — eşik $15.00'a yaklaşıyor.
Detay için: /cloud maliyet
```

---

## Hata Kodları

| Durum | Mesaj |
|-------|-------|
| Kimlik bilgisi eksik | "AWS kimlik bilgileri eksik. .env dosyasına AWS_ACCESS_KEY_ID ve AWS_SECRET_ACCESS_KEY ekleyin." |
| boto3 kurulu değil | "boto3 kurulu değil. `pip install boto3` ile kurun." |
| Yetki hatası | "Yetki hatası: bu kaynağa erişim izniniz yok." |
| Instance bulunamadı | "Instance bulunamadı: <id>" |
| Zaten çalışıyor | "Instance zaten çalışıyor: <id>" |
| Zaten durdurulmuş | "Instance zaten durdurulmuş: <id>" |
| API zaman aşımı | "AWS bağlantısı zaman aşımına uğradı. Tekrar deneyin: /cloud <komut>" |
| Bilinmeyen komut | "Bilinmeyen komut. Yardım için: /cloud yardim" |
