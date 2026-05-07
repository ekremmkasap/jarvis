# Research: CloudManagerSystem

**Phase**: 0 — Unknowns & Decisions
**Date**: 2026-04-12

---

## Decision 1: AWS SDK Seçimi

**Decision**: `boto3` (AWS resmi Python SDK)
**Rationale**: Jarvis Python tabanlı; boto3 EC2/S3/Cost Explorer için native destek sağlar, geniş belgeleme ve topluluk desteği var. Proje zaten `requests` ve `openai` SDK kullanıyor — boto3 aynı pattern'e uyar.
**Alternatives considered**:
- `aws-cli` subprocess çağrısı — daha yavaş, çıktı parse etmek kırılgan
- `httpx` + AWS Signature v4 manuel imzalama — gereksiz karmaşıklık
- `aioboto3` (async) — bridge.py sync threading kullanıyor, async gereksiz

---

## Decision 2: Kimlik Bilgisi Yönetimi

**Decision**: `.env` dosyasında `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION` değişkenleri; boto3 bunları otomatik okur.
**Rationale**: Jarvis hâlihazırda `.env` tabanlı credential yönetimi kullanıyor (OPENAI_API_KEY, TELEGRAM_TOKEN vb.). Aynı pattern, sıfır ek altyapı.
**Alternatives considered**:
- AWS IAM Role (EC2 instance profile) — Jarvis bare-metal Windows'ta çalışıyor, EC2'de değil
- AWS SSO / assume-role — tek kullanıcı için aşırı karmaşık
- Ayrı `cloud_config.yaml` — gereksiz, .env yeterli

---

## Decision 3: Maliyet Veri Kaynağı

**Decision**: AWS Cost Explorer API (`boto3` → `ce.get_cost_and_usage`)
**Rationale**: En doğru resmi kaynak; aylık/günlük dönem filtresi, servis bazında döküm destekler. Ücretsiz limit: ilk 12 ay + sonrasında $0.01/istek (düşük kullanım).
**Alternatives considered**:
- CloudWatch Billing Alarms — push tabanlı ama sadece toplam; servis bazlı döküm yok
- Billing Dashboard scraping — kırılgan ve TOS riski
- Budgets API — threshold notification için kullanılabilir ama polling daha basit

**Cost polling stratejisi**: `cloud_cost_cache.json` günde bir kez güncellenir (her 24 saatte bir); eşik kontrolü her 15 dakikada bir cache'den okur. AWS API çağrı sayısı minimumda tutulur.

---

## Decision 4: Bridge Entegrasyon Noktası

**Decision**: `handle_command` fonksiyonuna `elif command == "/cloud"` bloğu eklenir; HTTP API için `/api/cloud/resources` ve `/api/cloud/costs` endpoint'leri `do_GET`'e eklenir.
**Rationale**: Mevcut bridge.py pattern tam olarak bu; notion_skill, stripe_webhook_skill, gmail_skill aynı şekilde entegre edilmiş. Backward-safe: mevcut komutlar dokunulmaz.
**Alternatives considered**:
- Ayrı microservice (FastAPI port 5002) — gereksiz altyapı, tek kullanıcı senaryosunda fazla
- WebSocket event olarak cloud komutları — Telegram handler zaten sync HTTP, uyumsuz

---

## Decision 5: Web UI Veri Akışı

**Decision**: Next.js `/cloud` sayfası, bridge.py'daki `/api/cloud/resources` ve `/api/cloud/costs` endpoint'lerini `fetch` ile polling yapar (30 saniyede bir); başlat/durdur için POST.
**Rationale**: Mevcut web UI (StatsBar, useWebSocket) aynı pattern kullanıyor. SSE veya WebSocket gereksiz; cloud state değişimi nadirdir.
**Alternatives considered**:
- WebSocket üzerinden cloud event'leri — Jarvis WS zaten var ama cloud state events eklemek scope büyütür
- React Query / SWR — Next.js projesine ek bağımlılık; basit fetch yeterli

---

## Decision 6: Hata ve Redaction Stratejisi

**Decision**: Skill içinde tüm `logging.info/warning/error` çağrıları `_redact(text)` yardımcısından geçer; bu fonksiyon `AWS_SECRET_ACCESS_KEY` ve `AWS_ACCESS_KEY_ID` değerlerini `***` ile maskeler.
**Rationale**: Constitution Prensip III zorunlu kılar. Diğer skill'lerde (stripe_webhook_skill.py) benzer pattern mevcut.
**Alternatives considered**:
- logging.Filter sınıfı — daha sağlam ama her logger'a attach etmek gerekir; tek fonksiyon daha basit
- Yapılandırılmış log (JSON) — overkill tek kullanıcı için

---

## Resolved Unknowns

| Unknown | Resolution |
|---------|------------|
| GCP/Azure v1'de var mı? | HAYIR — v1 yalnızca AWS |
| Cost Explorer ücreti? | İlk 12 ay ücretsiz; sonrası $0.01/istek — günde 1 çağrı = ~$0.30/yıl |
| boto3 kurulu mu? | Kontrol edilmeli; `requirements.txt`'e eklenmeli |
| Para birimi? | USD (Cost Explorer); isteğe bağlı TRY dönüşümü gösterim için |
| EC2 dışı kaynaklar? | v1 dışı: RDS, Lambda, EKS — kapsam dışı |
