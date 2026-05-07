# JARVIS MISSION CONTROL — CODEX DEVAM PROMPTU
# Hazırlanma tarihi: 2026-04-06
# Kullanım: Bu dosyayı Codex'e yapıştır ve çalıştır.

---

## BAĞLAM: NEREDEYIZ

Sen Jarvis Mission Control projesinin geliştiricisisin.
Proje dizini: C:/Users/sergen/Desktop/jarvis-mission-control

Jarvis = self-hosted, Türkçe, sıfır API maliyetli AI asistan SaaS.
- Omurga: server/bridge.py (Python, Telegram bot + HTTP API, port 8081)
- Web UI: apps/web-ui/ (Next.js 14, Tailwind CSS)
- LLM: Ollama (lokal) + Gemini (cloud fallback)
- Multi-tenant: her müşteri ayrı bot token + soul.md + SQLite bellek

### Son 5 commit'te ne yapıldı:
1. e1cca19 — Semantic memory: server/skills/memory_skill.py'a sentence-transformers + semantic_search() eklendi
2. f40fd5e — TypeScript→Python: src/runtime/skills/BridgeSkill.ts + server/bridge.py'a /command endpoint
3. 8130e28 — Landing page: apps/web-ui/src/app/landing/page.tsx + /api/beta-signup
4. 1e6919e — Stripe webhook: server/skills/stripe_webhook_skill.py + apps/web-ui/src/app/api/stripe-webhook/route.ts
5. abf4900 — Notion MCP: server/skills/notion_skill.py + bridge handler

---

## GÖREV LİSTESİ — SIRAYLA YAP

### GÖREV 1: Dependency Install + Smoke Test
**Amaç:** Yeni eklenen paketlerin kurulu olduğunu doğrula, eksikse kur.

```
Adımlar:
1. pip install -r requirements.txt
   (stripe>=11.6.0 yeni eklendi, diğerleri zaten kuruluydu)

2. cd apps/web-ui && npm install
   (stripe ^18.5.0 yeni eklendi)

3. Python smoke test çalıştır:
   python -m unittest tests.test_stripe_webhook_skill -v

4. Next.js build kontrolü:
   cd apps/web-ui && npm run build

5. Sonuçları raporla — hata varsa düzelt, hata yoksa devam et.
```

---

### GÖREV 2: Gmail + Google Calendar Skill Tamamlama
**Amaç:** Codex önceki sohbette gmail_skill.py ve gcalendar_skill.py dosyalarını oluşturdu ama bunların mevcut olduğunu doğrulamadık. Kontrol et ve eksikleri tamamla.

**Dosyalar:**
- server/skills/gmail_skill.py
- server/skills/gcalendar_skill.py

**Kontrol listesi:**
```python
# gmail_skill.py içinde olması gerekenler:
def handle_gmail(args: str, user_id: str = "") -> str:
    # GMAIL_CREDENTIALS_PATH env yoksa Türkçe kurulum talimatı dönsün
    # Alt komutlar: liste (son 5 mail), gonder [kime] | [konu] | [içerik]
    # google-auth-oauthlib + googleapiclient kullan
    # credentials path: server/config/google_credentials.json
    # token path: server/data/google_token.json

# gcalendar_skill.py içinde olması gerekenler:
def handle_gcalendar(args: str, user_id: str = "") -> str:
    # GOOGLE_CREDENTIALS_PATH env yoksa Türkçe kurulum talimatı dönsün
    # Alt komutlar: liste (bugün), ekle [başlık] tarih:[YYYY-MM-DD] saat:[HH:MM]
    # Aynı credentials dosyasını kullan
```

**Eğer dosyalar eksikse veya hatalıysa:** Yukarıdaki spec'e göre yaz.
**Eğer dosyalar tamam görünüyorsa:** Basit bir unittest yaz (mock ile), çalıştır, commit et.

---

### GÖREV 3: Stripe Webhook Production Hazırlığı
**Amaç:** Stripe webhook flow'unu uçtan uca test et.

**Kritik dosyalar:**
- server/skills/stripe_webhook_skill.py (satır 25, 42, 382 — plan eşleme + Telegram bildirim)
- server/bridge.py satır 1430 ve 2558 — stripe_webhook command handler
- apps/web-ui/src/app/api/stripe-webhook/route.ts

**Adımlar:**
```
1. server/skills/stripe_webhook_skill.py dosyasını oku

2. Şunu kontrol et:
   - handle_stripe_webhook(data) fonksiyonu var mı?
   - checkout.session.completed event'i handle ediliyor mu?
   - STRIPE_STARTER_PRICE_ID, STRIPE_PRO_PRICE_ID, STRIPE_AGENCY_PRICE_ID env'lerden okunuyor mu?
   - server/data/customers/{email}/ klasörü oluşturuluyor mu?
   - config.json + soul.md yazılıyor mu?
   - Telegram bildirimi: TELEGRAM_BOT_TOKEN + ADMIN_CHAT_ID kullanılıyor mu?

3. Eksik varsa tamamla.

4. tests/test_stripe_webhook_skill.py dosyasına şu test case'leri ekle (yoksa yaz):
   - test_valid_checkout_completed: geçerli event ile müşteri klasörü oluşturuluyor mu?
   - test_invalid_signature: imza doğrulama hatası doğru handle ediliyor mu?
   - test_unknown_plan: bilinmeyen price_id gelince ne oluyor?
   - test_missing_env: STRIPE_WEBHOOK_SECRET yoksa ne oluyor?

5. Testleri çalıştır: python -m unittest tests.test_stripe_webhook_skill -v

6. Commit et.
```

---

### GÖREV 4: Multi-Tenant Müşteri Yönetimi
**Amaç:** Her müşteri için izole Jarvis instance hazırlayan onboarding sistemi.

**Yeni dosya: server/skills/tenant_manager.py**

```python
"""
Jarvis Multi-Tenant Manager
Her müşteri için izole config + bellek + kişilik yönetimi
"""

class TenantManager:
    BASE_DIR = "server/data/customers/"
    SOUL_TEMPLATE = "server/config/soul_template.md"
    
    def create_tenant(self, email: str, plan: str) -> dict:
        """
        Yeni müşteri için:
        - server/data/customers/{email}/ klasörü oluştur
        - config.json yaz: {email, plan, created_at, status: "active", bot_token: null}
        - soul.md oluştur (soul_template.md'den kopyala, {CUSTOMER_EMAIL} placeholder'ını değiştir)
        - memory.db SQLite dosyası oluştur (boş, memory_skill init ile)
        - Dön: {"ok": True, "tenant_dir": "...", "config": {...}}
        """
        pass
    
    def get_tenant(self, email: str) -> dict | None:
        """Müşteri config'ini oku, yoksa None döndür"""
        pass
    
    def list_tenants(self) -> list:
        """Tüm aktif müşterileri listele"""
        pass
    
    def deactivate_tenant(self, email: str) -> bool:
        """Müşteri status'unu inactive yap"""
        pass
    
    def get_tenant_stats(self) -> dict:
        """
        Admin dashboard için:
        - Toplam müşteri sayısı
        - Plan dağılımı (starter/pro/agency)
        - Bu ay eklenenler
        """
        pass
```

**Ayrıca bridge.py'a şu komutları ekle (diğer handler'larla aynı pattern):**
```
/admin_musteriler → TenantManager.list_tenants() çağır, tabloyu göster
/admin_stats → get_tenant_stats() çağır
```
(Not: bu komutlar sadece ADMIN_CHAT_ID'den çalışsın)

**Sonra test yaz ve commit et.**

---

### GÖREV 5: Landing Page İyileştirmeleri
**Amaç:** apps/web-ui/src/app/landing/page.tsx'i production-ready yap.

**Mevcut durum:** Temel landing page var (commit 8130e28).

**Eklenecekler:**

```
1. apps/web-ui/src/app/landing/page.tsx dosyasını oku

2. Şunları ekle/düzelt:
   a. SEO meta tags: title, description, og:image
      → apps/web-ui/src/app/landing/layout.tsx oluştur
   
   b. Fiyatlandırma kartlarına "En Popüler" badge ekle (Pro pakete)
   
   c. SSS (Sık Sorulan Sorular) bölümü ekle (en alta, accordion değil düz liste):
      - Jarvis internet bağlantısı gerektiriyor mu? → Hayır, tamamen lokal çalışır.
      - Telegram botu nasıl kurulur? → Kurulumda sana adım adım yol gösteriyoruz.
      - Verilerim nerede saklanır? → Kendi bilgisayarında, hiçbir yere gönderilmez.
      - İptal edebilir miyim? → Evet, istediğin zaman.
      - Kaç kişi kullanabilir? → Paketlere göre 1-sınırsız bot.
   
   d. Footer: © 2026 Jarvis AI • Tüm hakları saklıdır

3. apps/web-ui/src/app/page.tsx'i kontrol et — eğer default Next.js sayfasıysa landing'e redirect ekle:
   import { redirect } from 'next/navigation'
   export default function Home() { redirect('/landing') }

4. npm run build ile kontrol et, hata varsa düzelt.

5. Commit et.
```

---

### GÖREV 6: Admin Dashboard (Web UI)
**Amaç:** Ekrem'in müşterileri, beta başvurularını ve sistem durumunu görebileceği basit bir admin sayfası.

**Yeni dosya: apps/web-ui/src/app/admin/page.tsx**

```
Bölümler (Tailwind, server-side rendering):
1. Sistem Durumu: bridge.py'a GET /health isteği at, sonucu göster
2. Beta Başvuruları: server/data/beta_signups.json'ı oku, tablo göster
3. Müşteriler: server/data/customers/ dizinini tara, aktif müşterileri listele
4. Hızlı Aksiyonlar: "Stripe Test Webhook Gönder" butonu

Not: Bu sayfa şimdilik auth olmadan çalışabilir (localhost only).
Veri okuma için yeni API route'lar gerekecek:
- apps/web-ui/src/app/api/admin/stats/route.ts → beta_signups.json + customers/ okur
- apps/web-ui/src/app/api/admin/health/route.ts → bridge.py /health endpoint'ine proxy atar
```

**Commit et.**

---

### GÖREV 7: Notion Skill Test + Hata Düzeltme
**Amaç:** server/skills/notion_skill.py'ı doğrula.

**Dosyayı oku ve şunları kontrol et:**
```
1. handle_notion(args, user_id) fonksiyonu var mı?
2. Alt komutlar: liste, ara [sorgu], ekle [başlık] | [içerik]
3. NOTION_API_KEY veya NOTION_DATABASE_ID yokken Türkçe kurulum talimatı dönüyor mu?
4. requests kütüphanesi import guard ile mi? (try/except ImportError)
5. Notion API endpoint'leri doğru mu?
   - Arama: POST https://api.notion.com/v1/search
   - Database query: POST https://api.notion.com/v1/databases/{id}/query
   - Sayfa oluştur: POST https://api.notion.com/v1/pages
   - Header: Notion-Version: 2022-06-28

6. Eksik/hatalı bir şey varsa düzelt.

7. tests/test_notion_skill.py yaz:
   - test_no_credentials: env yokken kurulum talimatı dönüyor mu?
   - test_liste_command: mock requests ile liste komutu
   - test_ara_command: mock requests ile arama
   - test_ekle_command: mock requests ile sayfa oluşturma
   - test_invalid_command: bilinmeyen komut

8. Testleri çalıştır ve commit et.
```

---

### GÖREV 8: BridgeSkill TypeScript Test
**Amaç:** src/runtime/skills/BridgeSkill.ts'i doğrula ve test et.

**Dosyayı oku:**
- src/runtime/skills/BridgeSkill.ts
- src/runtime/contracts/BridgeCommand.ts

**Kontrol listesi:**
```typescript
// BridgeSkill.ts içinde olması gerekenler:
// 1. BRIDGE_URL env variable (default: http://127.0.0.1:8081)
// 2. POST /command endpoint'ine istek atar
// 3. { command, args, chatId } payload gönderir
// 4. Hata durumunda anlamlı mesaj döner
// 5. Timeout var mı? (önerilir: 10 saniye)

// Eksikleri tamamla.
```

**Test yaz: src/runtime/skills/BridgeSkill.test.ts**
```
- fetch mock ile başarılı istek testi
- HTTP hata kodu testi (500)
- Timeout testi
- BRIDGE_URL env override testi
```

**npm test veya npx jest ile çalıştır, commit et.**

---

### GÖREV 9: Tüm Testleri Çalıştır ve Rapor Ver

```bash
# Python testleri
cd C:/Users/sergen/Desktop/jarvis-mission-control
python -m pytest tests/ -v --tb=short 2>&1

# Next.js build
cd apps/web-ui && npm run build 2>&1

# TypeScript tip kontrolü
cd C:/Users/sergen/Desktop/jarvis-mission-control && npx tsc --noEmit 2>&1
```

**Sonuçları şu formatta raporla:**
```
## Test Sonuçları

### Python Tests
- Toplam: X test
- Geçen: X
- Başarısız: X
- Başarısız testler: [liste]

### Next.js Build
- Durum: ✅ Başarılı / ❌ Hatalı
- Hatalar: [varsa liste]

### TypeScript
- Durum: ✅ Temiz / ❌ Hata var
- Hatalar: [varsa liste]
```

**Başarısız testler varsa düzelt, tekrar çalıştır.**

---

### GÖREV 10: DEVLOG Güncelle

**Dosya: DEVLOG.md (yoksa oluştur)**

```markdown
# Jarvis Mission Control — Geliştirme Günlüğü

## 2026-04-06 — Büyük Sprint

### Tamamlananlar
- ✅ Semantic memory (sentence-transformers, fallback-safe) [e1cca19]
- ✅ TypeScript → bridge.py HTTP bağlantısı (BridgeSkill) [f40fd5e]  
- ✅ Gmail MCP skill [server/skills/gmail_skill.py]
- ✅ Google Calendar MCP skill [server/skills/gcalendar_skill.py]
- ✅ Notion MCP skill [abf4900]
- ✅ SaaS Landing page (TR, Tailwind) [8130e28]
- ✅ Stripe webhook + otomatik onboarding [1e6919e]
- ✅ Multi-tenant müşteri yönetimi [TenantManager]
- ✅ Admin dashboard (web UI)

### Aktif Komutlar (Telegram)
/mail, /takvim, /notion, /admin_musteriler, /admin_stats

### Env Variables Eklendi
STRIPE_WEBHOOK_SECRET, STRIPE_*_PRICE_ID, NOTION_API_KEY, NOTION_DATABASE_ID
GOOGLE_CREDENTIALS_PATH (gmail + calendar için)

### Bir Sonraki Sprint
- [ ] Stripe production webhook URL kayıt (dashboard.stripe.com)
- [ ] Google OAuth credentials kurulumu (cloud.google.com/console)
- [ ] Notion integration kurulumu (notion.so/my-integrations)
- [ ] Beta müşteri outreach başlat
- [ ] Multi-tenant bot token yönetimi (her müşteri kendi bot'u)
- [ ] Monitoring: uptime + hata alertleri
```

**Commit et: `docs: DEVLOG güncelle — 2026-04-06 sprint özeti`**

---

## TAMAMLANMA KRİTERLERİ

Tüm görevler bittiğinde şunu kontrol et:

```
✅ pip install -r requirements.txt → hatasız
✅ npm install (apps/web-ui) → hatasız  
✅ python -m pytest tests/ → en az %90 geçiyor
✅ npm run build → hatasız
✅ npx tsc --noEmit → hatasız
✅ git log --oneline -15 → her görev için ayrı commit
```

---

## KRİTİK DOSYALAR (okumadan dokunma)

```
server/bridge.py          — Ana router (1400+ satır) — sadece handler ekle
server/skills/            — Skill'ler (her biri bağımsız)
apps/web-ui/src/app/      — Next.js sayfaları
src/runtime/              — TypeScript runtime
tests/                    — Test dosyaları
```

## KIRILMAZ KURALLAR

1. bridge.py'a dokunurken sadece yeni elif blokları ekle, var olanları değiştirme
2. Her skill'de credentials/env yoksa hata verme, Türkçe kurulum talimatı döndür
3. Import'ları try/except ile guard'la (kurulu olmayan paketler için)
4. Her görev bitince commit at — büyük tek commit yapma
5. Test yoksa görev bitmemiş sayılır

---

## NOTLAR

- Codex hesabı: bdlo7840
- Kota yenileme: 8 Nisan 2026 saat 20:03
- Pinokio'ya dokunmuyoruz — masaüstü repo = geliştirme ortamı
- bridge.py Pinokio'daki canlı sisteme deploy.py ile push edilir (Ekrem yapar)
- Web UI localhost:3000 üzerinde çalışır (Ekrem çalıştırır)
