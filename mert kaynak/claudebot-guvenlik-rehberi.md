# Claudebot Güvenlik Rehberi: 5 Adımda Agent'ını Güvenli Hale Getir

Claudebot viral oldu ama çoğu kişi güvenlik ayarlarını yapmadan kullanıyor. Bu rehber, Claudebot'u kurmadan ÖNCE yapman gereken 5 güvenlik adımını anlatıyor. ~10 dakika sürer.

---

## Claudebot Nedir?

Açık kaynak bir yazılım. Kendi sunucunda 7/24 çalışan bir AI asistanı. WhatsApp, Telegram veya Slack üzerinden mesaj atabilirsin.

**Erişebildiği şeyler:**
- Dosya sistemi (okuma/yazma)
- Shell komutları (terminal)
- Tarayıcı kontrolü
- Takvim
- Email
- Sen uyurken bile otonom çalışır

**Neden diğerlerinden farklı:**

| Araç | Nasıl Çalışır | Risk Seviyesi |
|------|--------------|---------------|
| Claude/ChatGPT (tarayıcı) | Provider'ın ortamında çalışır, senin makinene erişimi yok | Düşük |
| Claude Code / Codex (CLI) | Dosya sistemine erişir ama sadece sen terminaldeyken | Orta |
| **Claudebot** | 7/24 sunucuda çalışır, shell/dosya/tarayıcı/email erişimi var, sen yokken bile | **Yüksek** |

**Risk neden yüksek:**
- Mesaj atabilen herkes potansiyel olarak yeteneklerini tetikleyebilir
- Prompt injection → birisi bot'a kötü niyetli mesaj/link/doküman gönderirse:
  - Shell komutları çalıştırabilir
  - Veri sızdırabilir
  - GitHub organizasyonunu silebilir
  - Email'lerini kaybedebilir
- Patlama yarıçapı = tüm sunucun + bağlı tüm servisler

**Claudebot'un yaratıcısı Peter Steinberger** bu güvenlik adımlarını kendisi yayınladı ve Burak Eragar'ın uyarı thread'ini repost etti (400K+ görüntülenme).

---

## BAŞLAMADAN ÖNCE: Kurulum Notu

- Çoğu kişi Mac Mini alıp Claudebot çalıştırıyor
- Ama Peter'ın kendisi diyor: Amazon AWS free tier'da da deploy edebilirsin
- Claudebot kurulumu + onboarding'i tamamladıktan sonra bu 5 adımı uygula

---

## Adım 1: Sandbox Modunu Etkinleştir

**Bu ne:** Agent'ın komutlarını doğrudan sunucuda değil, izole Docker container'ında çalıştırır. Bir şey ters giderse patlama yarıçapını sınırlar.

**Varsayılan durum:** Sandbox KAPALI → agent tüm komutları direkt sunucuda tam erişimle çalıştırır. Bu tehlikeli.

### Yapılacaklar:

**1. Claudebot'u durdur:**
```bash
Ctrl + C
```

**2. Yapılandırma dosyasını aç:**
```bash
nano claudebot.json
```

Bu dosya her şeyi kontrol eder: model seçimi, agent davranışları, workspace, gateway.

**3. Sandbox bloğunu ekle:**

`agents.default` bölümünün içine şunu ekle:

```json
{
  "agents": {
    "default": {
      "sandbox": {
        "mode": "all",
        "scope": "session",
        "workspaceAccess": "none"
      }
    }
  }
}
```

### Her Ayarın Anlamı:

| Ayar | Değer | Ne Yapar |
|------|-------|----------|
| `mode` | `"all"` | Tüm oturumlar Docker container'ında çalışır (en güvenli) |
| `mode` | `"non-main"` | Sadece kişisel DM sandbox dışı, grup chatler izole (daha az güvenli) |
| `scope` | `"session"` | Her konuşma kendi izole container'ını alır (en güçlü izolasyon) |
| `scope` | `"agent"` | Agent başına bir container |
| `scope` | `"shared"` | Tek container herkes için (en zayıf) |
| `workspaceAccess` | `"none"` | Sandbox araçları workspace dizinine hiç erişemez (en kısıtlayıcı) |
| `workspaceAccess` | `"ro"` | Sadece okuma erişimi |
| `workspaceAccess` | `"rw"` | Okuma + yazma erişimi |

**Önerilen:** `mode: "all"` + `scope: "session"` + `workspaceAccess: "none"`

**4. Kaydet ve çık:**
```bash
Ctrl + X → Y → Enter
```

**5. Gateway'i yeniden başlat:**
```bash
claudebot gateway restart
```

**ÖNEMLİ:** Sandbox için Docker kurulu olmalı. Yoksa:
- Docker'ı kur
- Claudebot repo'sundaki sandbox setup script'ini çalıştır
- Dokümantasyon: Claudebot repo → Sandbox Setup

**Sandbox ne yapmaz:**
- Her saldırıyı engellemez (bulletproof değil)
- Ama bir şey ters giderse → hasar sunucun yerine izole container'da kalır
- Ciddi şekilde patlama yarıçapını azaltır

---

## Adım 2: Araç Kısıtlamaları (Tool Whitelist)

**Bu ne:** Agent'ın hangi araçları kullanabileceğini sınırlar. Sandbox "nerede çalışır" sorusunu çözer, tool policy "ne yapabilir" sorusunu çözer. İkisi birlikte = katmanlı koruma.

**Varsayılan durum:** Agent geniş bir araç setine erişebilir → dosya okuma/yazma, shell çalıştırma, tarayıcı kontrolü, ve daha fazlası.

### Yapılacaklar:

**1. claudebot.json'u aç:**
```bash
nano claudebot.json
```

**2. Allow list ve deny list tanımla:**

Yapılandırma dosyasında araçları kısıtla. Genel prensip:

**İzin ver (allow list):**
- Dosya okuma ✅
- Web arama ✅
- Takvim okuma ✅

**Engelle (deny list):**
- Shell komutu çalıştırma ❌
- Tarayıcı kontrolü ❌
- Dosya yazma ❌ (gerekmedikçe)
- Email gönderme ❌ (gerekmedikçe)

**3. Kaydet ve gateway'i restart et:**
```bash
claudebot gateway restart
```

**Temel Prensip:**
- Sandbox = bir şey ters giderse hasarı sınırlar
- Tool policy = ilk başta nelerin olabileceğini sınırlar
- İkisini birlikte kullan → en güçlü koruma

**Detaylı yapılandırma:** Claudebot docs → "Multi-agent Sandbox and Tools" bölümü

---

## Adım 3: Güvenlik Audit'ini Çalıştır

**Bu ne:** Claudebot'un yerleşik güvenlik taraması. Tüm yapılandırmanı kontrol eder ve yaygın sorunları bulur.

### 3 Kritik Komut:

**Komut 1 - Temel güvenlik taraması:**
```bash
claudebot security audit
```

**Ne bulur (örnek çıktı):**
- 🔴 KRİTİK: Credentials dizini izinleri çok açık → başka kullanıcılar erişebilir
- ⚠️ UYARI: Reverse proxy yapılandırması eksik
- ℹ️ BİLGİ: Saldırı yüzeyi özeti:
  - Kaç grup açık vs whitelist'te
  - Yükseltilmiş araçlar etkin mi
  - Tarayıcı kontrolü açık mı

**Komut 2 - Derin tarama (ağ probeleri dahil):**
```bash
claudebot security audit --deep
```

Gateway'in canlı problarını yapar. Dışa açık erişim varsa özellikle faydalı.

**Komut 3 - Otomatik düzeltme (EN ÖNEMLİSİ):**
```bash
claudebot security audit --fix
```

**Ne yapar:**
- Güvenli düzeltmeleri otomatik uygular
- Credentials dizini izinlerini 700'e çeker (sadece senin kullanıcın erişebilir)
- Sessions dizini izinlerini düzeltir
- Kritik sorunları otomatik kapatır

**Örnek çıktı:**
```
✅ Fixed: credentials directory permissions → 700
✅ Fixed: sessions directory permissions → 700
🔴 Critical issues: 0 (was 1)
⚠️ Warnings: 1 (trusted proxies - OK for local setup)
```

**Ne zaman çalıştırmalısın:**
- İlk kurulumdan sonra (şimdi)
- Config değiştirdiğinde
- Ağ yüzeyini açtığında
- Düzenli olarak (haftalık kontrol)

---

## Adım 4: Token'ları Kısıtla (İnsanların %99'u Bunu Yanlış Yapıyor)

**Bu ne:** Claudebot'a harici servisleri (GitHub, Google Calendar, Gmail, API'ler) bağlarken verdiğin erişim token'larını minimum düzeyde tutmak.

**Burak Eragar'ın uyarısı:** "İnsanların %99'u bunu yanlış yapacak."

### Temel Prensip: Minimum İzin (Minimum Permissions)

Her entegrasyon sadece gerçekten ihtiyaç duyduğu erişime sahip olmalı, fazlası değil.

### GitHub Örneği:

**YAPMA:**
```
Token scope: repo (tüm repolara tam erişim)
```
Bu token ile agent manipüle edilirse → tüm repolarını silebilir, özel kodunu okuyabilir, push yapabilir.

**YAP:**
```
Token scope: public_repo (sadece public repolar, readonly)
```
Agent manipüle edilse bile → sadece zaten herkese açık kodu okuyabilir, hiçbir şey silemez/değiştiremez.

**GitHub Token Oluşturma:**
1. GitHub → Settings → Developer Settings → Personal Access Tokens
2. **Fine-grained tokens** seç (eski "classic" değil)
3. "Public repositories only" seç
4. Ek izinleri EKLEME (email, SSH keys, profile → hepsi gereksiz)
5. Token oluştur → Claudebot'a ver

### Google Örneği:

| İhtiyaç | Doğru İzin | Yanlış İzin |
|---------|-----------|-------------|
| Takvim okuma | Calendar readonly | Full account access |
| Email okuma | Gmail readonly | Gmail full (send + delete dahil) |
| Drive dosya okuma | Drive readonly | Drive full access |

### Genel Kural:

Her servis bağlamadan önce kendine sor:
```
"Bu agent'ın bu serviste yapması gereken minimum şey ne?"
```

- Sadece okuma yeterliyse → readonly token ver
- Belirli repo/klasör yeterliyse → sadece ona scope et
- Email göndermesi gerekmiyorsa → send izni verme
- Tam hesap erişimi ASLA verme

**Neden önemli:**
- Agent prompt injection ile manipüle edilirse → sadece token'ın izin verdiğini yapabilir
- Readonly token → repo silemez
- Calendar-only token → email gönderemez
- Minimum izin = minimum hasar

---

## Adım 5: Gizli Tut (Grup Chat'lere EKLEME)

**Bu ne:** Bot'una kimlerin mesaj atabilceğini kontrol etmek.

**Burak'ın uyarısı:**
> "Kişisel Claudebot'unu asla WhatsApp veya Telegram grup chat'ine ekleme. O gruptaki herkes etkin olarak bot üzerinden sunucuna shell erişimine sahip olur."

**Peter'ın tavsiyesi:**
> "Kişisel bot'unsa grup chat'lere ekleme."

### Neden:

- Bot'una mesaj atabilen herkes potansiyel olarak onu manipüle edebilir
- Kötü niyetli link, gizli talimat içeren doküman, veya akıllıca yazılmış prompt
- Erişen kişi sayısı arttıkça → saldırı yüzeyin büyür
- Claudebot'u "pseudo terminal" (sanal terminal) gibi düşün → terminale kimleri alırsın?

### Kurallar:

**Kişisel asistan olarak kullanıyorsan:**
- Sadece sen mesaj at ✅
- Veya güvendiğin çok az kişi ✅
- Grup chat'lere EKLEME ❌

**Grup ortamında kullanman gerekiyorsa:**
1. Sandbox modu açık olsun (Adım 1) ✅
2. Tool kısıtlamaları aktif olsun (Adım 2) ✅
3. Group policy'yi "allow list" yap → sadece onaylı kullanıcılar etkileşime geçebilsin ✅

### Yapılandırma:

```bash
nano claudebot.json
```

Group policy'yi allow list olarak ayarla:
```json
{
  "messages": {
    "groupPolicy": "allowList",
    "allowedUsers": ["senin_kullanici_adin"]
  }
}
```

```bash
claudebot gateway restart
```

---

## BONUS: Model Seçimi

**Peter'ın resmi önerisi:**
> "Herhangi bir model destekleniyor ama Anthropic Pro Max planını Opus 4.5 ile şiddetle öneriyorum - uzun context gücü ve daha iyi prompt injection direnci için."

**Neden önemli:**
- Daha yetenekli modeller → manipüle edildiğini fark etme olasılığı daha yüksek
- Ucuz model → dokümandaki gizli talimatları sorgulamadan takip edebilir
- Güçlü model → kötü niyetli prompt'u yakalama olasılığı daha yüksek
- Gerçek sistem erişimi olan bir agent'ta → API token maliyetinden kısma

**Varsayılan yapılandırmada:**
```json
{
  "agents": {
    "default": {
      "model": "opus-4.5"
    }
  }
}
```

---

## 5 ADIMLIK GÜVENLİK KONTROL LİSTESİ

```
□ Adım 1: Sandbox modu AÇ
  → claudebot.json → sandbox.mode: "all", scope: "session", workspaceAccess: "none"
  → claudebot gateway restart

□ Adım 2: Araç kısıtlamalarını ayarla
  → Allow list: sadece gereken araçlar
  → Deny list: shell, browser control (gerekmiyorsa)
  → claudebot gateway restart

□ Adım 3: Güvenlik audit'ini çalıştır
  → claudebot security audit
  → claudebot security audit --deep
  → claudebot security audit --fix

□ Adım 4: Token'ları minimum izinle oluştur
  → GitHub: fine-grained, public_repo only, readonly
  → Google: sadece gereken servis, readonly
  → Hiçbir servise full account access verme

□ Adım 5: Gizli tut
  → Grup chat'lere ekleme
  → Group policy: allowList
  → Sadece güvendiğin kişiler erişsin
```

---

## HIZLI BAŞLANGIÇ (10 Dakika)

```
Dakika 0-1:   Claudebot kurulumu tamamla → Ctrl+C ile dur
Dakika 1-3:   nano claudebot.json → sandbox bloğunu ekle → kaydet
Dakika 3-4:   claudebot gateway restart
Dakika 4-5:   claudebot security audit → sorunları gör
Dakika 5-6:   claudebot security audit --fix → otomatik düzelt
Dakika 6-8:   Harici servis token'larını minimum izinle oluştur
Dakika 8-9:   Group policy'yi allowList yap → kaydet → restart
Dakika 9-10:  claudebot security audit → son kontrol → temiz mi?
```

**Sırasıyla çalıştıracağın komutlar:**

```bash
# 1. Durur ve config'i aç
Ctrl + C
nano claudebot.json

# 2. Sandbox bloğunu ekle (yukarıdaki JSON), kaydet
Ctrl + X → Y → Enter

# 3. Restart
claudebot gateway restart

# 4. Güvenlik taraması
claudebot security audit

# 5. Derin tarama
claudebot security audit --deep

# 6. Otomatik düzeltme
claudebot security audit --fix

# 7. Token'ları oluştur (GitHub/Google → minimum izin)
# → Bu tarayıcıda yapılır, terminal komutu değil

# 8. Group policy ayarla
nano claudebot.json
# allowList ekle, kaydet

# 9. Son restart
claudebot gateway restart

# 10. Son kontrol
claudebot security audit
```

---

## ÖNEMLİ KAYNAKLAR

- **Peter Steinberger'ın guardrails listesi** → Claudebot repo README
- **Burak Eragar'ın güvenlik thread'i** → X (400K+ görüntülenme)
- **Claudebot Security Docs** → Repo içinde security dokümantasyonu
- **Sandbox Setup Script** → Claudebot repo → Docker sandbox kurulumu
- **Tool Policies Docs** → Multi-agent Sandbox and Tools bölümü

---

## ÖZET

| Adım | Ne Yapıyor | Neden Önemli |
|------|-----------|-------------|
| Sandbox | Agent'ı Docker container'ında çalıştırır | Ters giderse hasar izole kalır |
| Tool Whitelist | Agent'ın yapabileceklerini sınırlar | İlk başta nelerin olabileceğini kontrol eder |
| Security Audit | Config'i tarar, sorunları bulur, düzeltir | Açık bırakılan şeyleri yakalar |
| Token Scoping | Harici servislere minimum izin verir | Manipülasyon durumunda hasar sınırlı |
| Gizlilik | Kimlerin bot'la konuşabileceğini kontrol eder | Saldırı yüzeyini küçültür |

**Altın kural:** Bu 5 adımı yapmadan Claudebot'u KULLANMA. 10 dakika sürer ama seni saatler sürecek felaketlerden kurtarır.
