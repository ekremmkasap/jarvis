# Feature Specification: CloudManagerSystem — Jarvis Cloud Yönetim Skill'i

**Feature Branch**: `001-cloudmanagersystem-jarvis-entegreli`  
**Created**: 2026-04-12  
**Status**: Draft  
**Input**: CloudManagerSystem — Jarvis entegreli multi-cloud yönetim skill'i. AWS/GCP/Azure için EC2 başlat/durdur, S3 listele, fatura uyarısı, cost tracker, Telegram üzerinden komut. Jarvis bridge.py skill olarak çalışacak, web-ui'da cloud dashboard paneli olacak.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Cloud Kaynaklarını Telegram'dan Yönet (Priority: P1)

Ekrem, Telegram'da Jarvis'e "EC2 sunucularını listele" veya "i-1234abcd'yi başlat" gibi doğal dil komutları yazarak AWS kaynaklarını yönetebilir. Jarvis komutu çözümler, ilgili cloud işlemini gerçekleştirir ve sonucu Telegram mesajıyla bildirir.

**Why this priority**: Ekrem'in ana kontrol kanalı Telegram'dır; mevcut alışkanlığa sıfır sürtünmeyle cloud kontrolü eklemek en yüksek değeri üretir.

**Independent Test**: Yalnızca Telegram botu + cloud_manager_skill çalışır olduğunda EC2 başlatma komutu gönderilip instance'ın durumunun "running" olarak raporlanması test edilebilir.

**Acceptance Scenarios**:

1. **Given** Jarvis Telegram botu çalışıyor ve AWS kimlik bilgileri yapılandırılmış, **When** kullanıcı "EC2 listele" yazar, **Then** Jarvis çalışan/durdurulmuş tüm instance'ları isim ve durum bilgisiyle listeler.
2. **Given** geçerli bir instance ID biliniyor, **When** kullanıcı "i-1234abcd'yi durdur" yazar, **Then** Jarvis instance'ı durdurur ve "Durduruldu: i-1234abcd" yanıtını döner.
3. **Given** yanlış/erişilemeyen bir kaynak ID girildi, **When** komut işlenir, **Then** Jarvis anlaşılır bir hata mesajı döner ve sistem çökmez.

---

### User Story 2 — Fatura ve Maliyet Uyarıları Al (Priority: P2)

Ekrem, mevcut aylık cloud harcamasını sorgulayabilir ve belirli bir eşik aşıldığında Jarvis'ten otomatik Telegram bildirimi alabilir.

**Why this priority**: Kontrolsüz cloud maliyeti SaaS projesinin kârlılığını doğrudan etkiler; erken uyarı kritiktir.

**Independent Test**: Cost tracker tek başına çalışırken aylık harcama sorgusu yapılıp doğru toplam ve provider bazlı dökümün raporlanması test edilebilir.

**Acceptance Scenarios**:

1. **Given** cloud hesapları bağlı, **When** kullanıcı "bu ay ne kadar harcadım" yazar, **Then** Jarvis provider bazında harcama özetini ve toplam tutarı döner.
2. **Given** maliyet eşiği ₺500 olarak ayarlandı, **When** toplam harcama eşiği aşar, **Then** Jarvis kullanıcıya Telegram'dan otomatik uyarı gönderir.
3. **Given** fatura API'si geçici olarak erişilemez, **When** maliyet sorgusu yapılır, **Then** Jarvis son bilinen değeri ve "veri güncel olmayabilir" uyarısını birlikte döner.

---

### User Story 3 — Web UI Cloud Dashboard (Priority: P3)

Ekrem, Jarvis web arayüzünde tüm cloud kaynaklarını ve maliyetleri görsel bir dashboard'da görebilir; başlat/durdur gibi hızlı aksiyonları tek tıkla yapabilir.

**Why this priority**: Telegram yönetimi birincil, dashboard ise görsel doğrulama ve hızlı aksiyon için ikincil kanaldır.

**Independent Test**: Web UI ayrı olarak çalışırken cloud kaynakları listesi ve maliyet özeti kartları görüntülenebilir; başlat/durdur butonu durumu değiştirir.

**Acceptance Scenarios**:

1. **Given** web UI açık ve cloud bağlantısı sağlıklı, **When** kullanıcı Cloud sekmesine gider, **Then** sağlayıcı bazında kaynak sayısı, durumu ve günlük maliyet özeti kartları görünür.
2. **Given** bir EC2 instance listede görünüyor, **When** kullanıcı "Durdur" butonuna tıklar, **Then** instance durumu 30 saniye içinde "stopped" olarak güncellenir ve bildirim gösterilir.
3. **Given** hiçbir cloud hesabı henüz bağlanmamış, **When** kullanıcı Cloud dashboard'u açar, **Then** "Cloud hesabı ekle" rehber adımları gösterilir.

---

### User Story 4 — S3 / Cloud Storage Sorgulama (Priority: P3)

Ekrem, S3 bucket'larını listeleyebilir ve belirli bir bucket'taki dosya sayısı/boyutunu sorgulayabilir.

**Why this priority**: Depolama maliyetleri ve içerik doğrulama için faydalıdır ancak birincil operasyonel kontrol değildir.

**Independent Test**: Yalnızca S3 listele komutu çalıştırılıp bucket isimlerinin ve toplam boyutlarının raporlanması test edilebilir.

**Acceptance Scenarios**:

1. **Given** AWS kimlik bilgileri yapılandırılmış, **When** "S3 bucket'larımı listele" komutu verilir, **Then** Jarvis bucket adı, bölge ve toplam nesne sayısını listeler.
2. **Given** belirli bir bucket adı belirtildi, **When** "my-bucket içindeki dosyaları göster" komutu girilir, **Then** Jarvis son değiştirilen 20 dosyayı isim ve boyutuyla listeler.

---

### Edge Cases

- EC2 başlatma komutu verildiğinde instance zaten çalışıyorsa? → Jarvis "Zaten çalışıyor" mesajı döner, hata fırlatmaz.
- Birden fazla cloud provider yapılandırılmışsa maliyet toplamı nasıl sunulur? → Her provider ayrı satırda, altta genel toplam gösterilir.
- Kullanıcı izin sahibi olmadığı bir kaynağa erişmeye çalışırsa? → "Yetki hatası: bu kaynağa erişim izniniz yok" mesajı döner.
- Kimlik bilgileri süresi dolmuş veya geçersizse? → Jarvis yapılandırma yenileme adımlarını Telegram üzerinden bildirir.
- Ağ zaman aşımı durumunda? → 30 saniye bekler, başarısız olursa kullanıcıya retry seçeneği sunar.
- Komut belirsizse (örn. "sunucuyu kapat" — hangi sunucu?)? → Jarvis listeler ve hangisini kastettiğini sorar.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistem MUST AWS, GCP ve Azure cloud sağlayıcılarına bağlanabilmeli; her sağlayıcı bağımsız olarak etkinleştirilebilmeli/devre dışı bırakılabilmelidir (v1: yalnızca AWS zorunlu).
- **FR-002**: Kullanıcı MUST Telegram üzerinden doğal dil komutlarıyla EC2 instance'larını başlatabilmeli, durdurabilmeli ve listeleyebilmelidir.
- **FR-003**: Sistem MUST S3 bucket listesini ve içerik özetini (nesne sayısı, toplam boyut) döndürebilmelidir.
- **FR-004**: Sistem MUST mevcut aya ait toplam cloud harcamasını provider bazında raporlayabilmelidir.
- **FR-005**: Kullanıcı MUST bir maliyet uyarı eşiği tanımlayabilmeli; eşik aşıldığında Telegram bildirimi otomatik olarak gönderilmelidir.
- **FR-006**: Sistem MUST Jarvis `bridge.py` üzerinden `cloud_manager_skill` olarak kayıtlı olmalı ve HTTP komut endpoint'i aracılığıyla tetiklenebilmelidir.
- **FR-007**: Web UI MUST cloud kaynaklarını ve maliyet özetini görüntüleyen bir dashboard bölümü içermelidir.
- **FR-008**: Dashboard üzerinden MUST EC2 başlat/durdur aksiyonları tek tıkla gerçekleştirilebilmelidir.
- **FR-009**: Sistem MUST tüm cloud işlemlerini (komut, sonuç, timestamp) log dosyasına kaydetmelidir.
- **FR-010**: Sistem MUST kimlik bilgilerini şifreli/güvenli biçimde saklamalı; açık metin olarak loglara yazılmamalıdır.
- **FR-011**: Maliyet uyarısı kontrolü MUST en az her 15 dakikada bir otomatik olarak çalışmalıdır.

### Key Entities

- **CloudProvider**: AWS / GCP / Azure; bağlantı durumu, kimlik bilgisi referansı, aktif/pasif bayrağı.
- **CloudResource**: Instance/VM/Bucket; provider, kaynak ID, tip, bölge, mevcut durum (running/stopped/unknown).
- **CostRecord**: Provider, dönem (yıl-ay), toplam tutar, para birimi, son güncellenme zamanı.
- **CostAlert**: Kullanıcı tanımlı eşik tutarı, provider kapsamı (tek/tüm), bildirim kanalı (Telegram).
- **CloudCommand**: Kaynak komut metni, çözümlenen aksiyon, hedef kaynak ID, sonuç, timestamp.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Telegram'dan gönderilen bir cloud komutu 10 saniye içinde sonuç bildirimi alır.
- **SC-002**: EC2 başlat/durdur başarı oranı %95 ve üzerinde olur (geçerli kimlik bilgileri ve erişim izni varsayımıyla).
- **SC-003**: Maliyet uyarısı, eşik aşıldıktan sonra en geç 15 dakika içinde Telegram'a iletilir.
- **SC-004**: Web UI cloud dashboard'u 3 saniye içinde yüklenir ve en az 50 kaynağı listeleyebilir.
- **SC-005**: Desteklenmeyen veya hatalı bir komut girildiğinde sistem %100 oranında anlaşılır hata mesajı döner; sessizce başarısız olmaz.
- **SC-006**: İlk kurulum (kimlik bilgisi yapılandırması) 5 dakika içinde tamamlanabilir.

---

## Assumptions

- Kullanıcı (Ekrem) cloud sağlayıcı hesaplarına sahip ve API/IAM erişim anahtarlarını temin edebilir.
- v1 kapsamı yalnızca AWS'dir; GCP ve Azure ikinci aşamada eklenir.
- Maliyet verileri cloud sağlayıcıların resmi Billing API'leri üzerinden çekilir; gerçek zamanlı değil, günlük güncellenen verilerdir.
- Telegram botu hâlihazırda çalışıyor (mevcut Jarvis altyapısı); bu skill yeni bir bot gerektirmez.
- Web UI, mevcut Jarvis web arayüzüne (Next.js, port 8081) yeni bir sekme/rota olarak eklenir.
- Kimlik bilgileri `.env` dosyasında standart AWS ortam değişken isimleriyle saklanır.
- İlk sürümde yalnızca EC2 (compute) ve S3 (storage) kaynak tipleri desteklenir; RDS, Lambda, EKS vb. kapsam dışıdır.
- Multi-tenant kullanım (birden fazla müşteri cloud hesabı) v2 kapsamındadır; v1 tek kullanıcı (Ekrem) içindir.
- Maliyet para birimi varsayılan olarak USD'dir; Türk Lirası dönüşümü gösterim amaçlı yapılabilir.
