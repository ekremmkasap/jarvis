# Contract: Telegram Commands — MARK-XXXXVI

## Sesli Mesaj (Otomatik)

Kullanıcı herhangi bir sesli mesaj gönderir → otomatik işlenir.

**Trigger**: Telegram `voice` message type  
**Handler**: `telegram_voice_handler.py::handle_voice_message()`

**Flow**:
```
voice note → download .ogg → STT → intent → [persona switch] → process → TTS → send_voice
```

**Error Reply**: `"Sesi anlayamadım, yazarak tekrar eder misin?"`

---

## PC Kontrol Komutları

| Komut | Format | Eylem |
|-------|--------|-------|
| `/pc-durum` | `/pc-durum` | CPU%, RAM MB, Disk GB döner |
| `/ekran-goruntusu` | `/ekran-goruntusu` | Screenshot → Telegram photo |
| `/ac <app>` | `/ac chrome` | Whitelist'teki uygulama açar |
| `/dosya-gonder <path>` | `/dosya-gonder Desktop/rapor.pdf` | Dosyayı Telegram'a gönderir |
| `/jarvis-baslat` | `/jarvis-baslat` | master_launcher.py tetikler |
| `/jarvis-kapat` | `/jarvis-kapat` | Tüm Jarvis processleri kapatır |

**Error format**: `"❌ Bu komuta izin verilmiyor: {command}"`  
**Success format**: `"✅ {eylem} tamamlandı"`

---

## Agent Hafıza Komutları

| Komut | Format | Yanıt |
|-------|--------|-------|
| `/hafiza <persona>` | `/hafiza seda` | Son 5 mesaj numaralı liste |
| `/hafiza` | `/hafiza` | Aktif persona'nın son 5 mesajı |
| `/ajanlarin-ozeti` | `/ajanlarin-ozeti` | 7 ajan: son not tarihi veya "not yok" |
| `/kim-aktif` | `/kim-aktif` | Aktif persona adı + ne zamandır aktif |

**Empty memory format**: `"{persona_name}: henüz konuşma geçmişi yok"`

---

## Codex Dispatch Güncellemesi

| Komut | Önceki Davranış | Yeni Davranış |
|-------|----------------|--------------|
| `/codex-dispatch <görev>` | Slot parametresi gerekir | Aktif persona → slot otomatik |
| `/codex-durum` | Slot listesi | Slot + persona eşleşmesi de gösterir |

**Auto-dispatch format**: `"🔀 {persona_name} → {slot}: {görev}"`  
**Slot meşgul format**: `"⏳ {slot} meşgul, sıraya alındı (tahmini: {wait}dk)"`

---

## Wiki Intent Komutları (Doğal Dil)

Explicit komut gerekmez — intent classifier algılar:

| Mesaj Örneği | Eylem |
|-------------|-------|
| `"bu konuyu wiki'ye ekle"` | `wiki/` altında sayfa oluştur |
| `"wiki'yi güncelle: ..."` | Mevcut sayfayı güncelle |
| `"wiki'de {konu} var mı?"` | `wiki/index.md` ara, sonuç döner |

Explicit komut: `/wiki ekle {başlık} | {içerik}` (mevcut, değişmez)
