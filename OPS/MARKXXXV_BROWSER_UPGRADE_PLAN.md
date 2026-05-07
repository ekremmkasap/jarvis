# Mark-XXXV → Mark-XXXXX: Browser Control Upgrade Plan
**Tarih:** 2026-04-14
**Branch hedefi:** `005-markxxxxx-browser-upgrade`
**Repo:** `external-repos/Mark-XXXV/`

---

## Sorun Özeti

| Sorun | Mevcut Durum | İstenen |
|-------|-------------|---------|
| Chrome profili seçimi | Yok — tek context | "Ekrem Kasap'ı seç" → o profille aç |
| WhatsApp Web | Yok — sadece desktop app | "WhatsApp'ı aç" → web.whatsapp.com (misafir sekme) |
| Misafir/temiz sekme | İncognito var ama kullanılmıyor | "WhatsApp aç" → yeni temiz sekme |
| Profil listesi | Yok | "Hangi profiller var?" → listele |
| YouTube açma | URL açılıyor ama profil yok | O an aktif profilde aç |
| Telegram Web | Yok | web.telegram.org profil sekmesinde aç |

---

## Özellik Listesi (Öncelik Sıralı)

### F1 — Chrome Multi-Profile Support ⭐⭐⭐
**Dosya:** `actions/browser_control.py` + yeni `config/chrome_profiles.json`

**Ne yapacak:**
- `config/chrome_profiles.json` içinde profil isim → Chrome user-data-dir path mapping
- `chrome.exe --profile-directory="Profile 1"` ile doğru profili aç
- Playwright `user_data_dir` parametresiyle kalıcı profil oturumu
- İsim veya numara ile seçim

**Komut örnekleri:**
```
"Chrome'u Ekrem olarak aç"      → Profile 1 (Ekrem Kasap)
"2. profili aç"                  → Profile 2
"Hangi Chrome profilleri var?"   → Liste döner
"Misafir modunda aç"             → Incognito / Guest
```

**Config örneği (`config/chrome_profiles.json`):**
```json
{
  "profiles": [
    {"name": "Ekrem Kasap", "aliases": ["ekrem", "ben", "ana"], "profile_dir": "Profile 1", "number": 1},
    {"name": "İş", "aliases": ["is", "work"], "profile_dir": "Profile 2", "number": 2},
    {"name": "Misafir", "aliases": ["misafir", "guest", "temiz"], "profile_dir": "Guest Profile", "number": 0}
  ],
  "chrome_user_data": "C:/Users/sergen/AppData/Local/Google/Chrome/User Data"
}
```

**Uygulama noktaları:**
- `actions/browser_control.py:_launch_browser_if_needed()` → `user_data_dir` + `channel` parametresi
- `actions/browser_control.py:_parse_action()` → `profile` parametresi parse et
- Yeni yardımcı: `utils/chrome_profile_manager.py`

---

### F2 — WhatsApp Web + Desktop Hybrid ⭐⭐⭐
**Dosya:** `actions/send_message.py` + `actions/browser_control.py`

**Ne yapacak:**
- `"WhatsApp'ı aç"` → `web.whatsapp.com` yeni sekmede (varsayılan)
- `"WhatsApp masaüstünü aç"` → mevcut desktop app mantığı
- Mesaj gönderme: hem web hem desktop desteklensin
- Web modunda: kişi arama → tıkla → mesaj yaz → Enter

**Komut örnekleri:**
```
"WhatsApp'ı aç"                  → web.whatsapp.com (yeni sekme, aktif profil)
"WhatsApp masaüstünü aç"         → desktop app
"WhatsApp'ta Ahmet'e merhaba de" → web veya desktop, Ahmet'i bul, mesaj at
"WhatsApp Web'i misafir modunda aç" → incognito sekme
```

**Uygulama:**
- `send_message.py` → `platform` parametresi: `"whatsapp_web"` | `"whatsapp_desktop"` | `"auto"`
- `auto`: Desktop app açıksa onu kullan, yoksa web'e düş
- Web için: `browser_control.go_to("https://web.whatsapp.com")` → smart_click(kişi arama) → type → Enter

---

### F3 — Temiz/Misafir Sekme ile Uygulama Açma ⭐⭐
**Dosya:** `actions/browser_control.py`

**Ne yapacak:**
- `"WhatsApp'ı temiz sekmede aç"` → yeni incognito pencere + web.whatsapp.com
- `"YouTube'u misafir olarak aç"` → incognito + youtube.com
- Mevcut `_get_incognito_page()` kullanılacak, sadece URL binding eklenecek

**Komut örnekleri:**
```
"WhatsApp'ı temiz sekmede aç"   → incognito + web.whatsapp.com
"YouTube'u misafir olarak aç"   → incognito + youtube.com
"Telegram'ı ayrı pencerede aç"  → yeni normal pencere
```

---

### F4 — Sekme ve Oturum Yönetimi ⭐⭐
**Dosya:** `actions/browser_control.py` + `actions/computer_settings.py`

**Mevcut:** Ctrl+W / Ctrl+T / Ctrl+Tab var ama komut entegrasyonu eksik

**Eklenecekler:**
- `"Şu anki sekmeyi kapat"` → Ctrl+W
- `"Yeni sekme aç"` → Ctrl+T
- `"Bir önceki sekmeye geç"` → Ctrl+Shift+Tab
- `"WhatsApp sekmesine geç"` → açık sekmeleri tara, WhatsApp başlığını bul, focus et

**Sekme arama:**
- Playwright: tüm `context.pages()` içinde `page.title()` veya `page.url()` ile eşleştir

---

### F5 — Telegram Web ⭐⭐
**Dosya:** `actions/browser_control.py`

**Ne yapacak:**
- `"Telegram'ı aç"` → `web.telegram.org` aktif profil sekmesinde
- `"Telegram'da X'e mesaj at"` → web.telegram.org → kişi arama → mesaj

**Not:** Desktop Telegram varsa önce onu dene, yoksa web'e düş (F2 ile aynı pattern)

---

### F6 — Profil Bazlı URL Bookmark ⭐
**Dosya:** yeni `config/app_profiles.json`

**Ne yapacak:**
- Hangi uygulama hangi profilde açılacağını tanımla
- `"YouTube'u aç"` → her zaman Ekrem profili ile
- `"WhatsApp'ı aç"` → her zaman Ekrem profili ile
- `"İş mailini aç"` → İş profili ile

**Config örneği:**
```json
{
  "app_profile_bindings": {
    "youtube": "Ekrem Kasap",
    "whatsapp_web": "Ekrem Kasap",
    "gmail": "Ekrem Kasap",
    "telegram_web": "Ekrem Kasap"
  }
}
```

---

## Uygulama Sırası

```
F1 (Chrome profil) → F2 (WhatsApp hybrid) → F3 (Temiz sekme) → F4 (Sekme mgmt) → F5 (Telegram web) → F6 (Bookmark)
```

F1 olmadan F2, F5, F6 tam çalışmaz — bloker.

---

## Kritik Dosyalar

| Dosya | Değişiklik Türü |
|-------|----------------|
| `external-repos/Mark-XXXV/actions/browser_control.py` | Profil desteği, incognito URL binding, sekme arama |
| `external-repos/Mark-XXXV/actions/send_message.py` | WhatsApp Web hybrid |
| `external-repos/Mark-XXXV/utils/chrome_profile_manager.py` | YENİ — profil okuma/eşleştirme |
| `external-repos/Mark-XXXV/config/chrome_profiles.json` | YENİ — profil config |
| `external-repos/Mark-XXXV/config/app_profiles.json` | YENİ — uygulama-profil binding |
| `external-repos/Mark-XXXV/agent/executor.py` | Yeni action routing |

---

## Doğrulama Senaryoları

1. `"Chrome'u Ekrem olarak aç"` → Chrome Profile 1 ile açılır
2. `"WhatsApp'ı aç"` → web.whatsapp.com Ekrem profilinde açılır
3. `"WhatsApp masaüstünü aç"` → desktop app açılır
4. `"YouTube'u misafir modunda aç"` → incognito + youtube.com
5. `"Hangi Chrome profilleri var?"` → liste döner
6. `"Telegram'ı aç"` → web.telegram.org aktif profilde

---

## Notlar

- Playwright `persistent_context` ile Chrome user data dir kullanımı → oturum kalıcı
- Misafir profil için `--guest` flag veya incognito — oturum saklanmaz (WhatsApp QR her seferinde çıkar, beklenen davranış)
- WhatsApp Web QR gereksinimi: ilk açılışta kullanıcı QR okutmalı, sonraki açılışlar profil oturumundan devam eder
- `chrome_profiles.json` hassas veri değil — Windows path içeriyor, .env gerektirmez
