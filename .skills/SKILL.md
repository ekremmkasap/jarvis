---
name: jarvis-bridge
description: Jarvis Mission Control ve Telegram gateway yönetimi için skill. SSH olmadan WSL üzerinde dosya deploy etme, servis restart, Telegram /cmd ile terminal işlemleri, AnyDesk bağlantı isteği onaylama (/kabul), gateway güncelleme ve Jarvis sistem yönetimi görevlerinde MUTLAKA bu skill'i kullan. "Jarvis'e ekle", "gateway'i güncelle", "servisi yeniden başlat", "WSL'e kopyala", "Telegram'dan çalıştır", "onayla", "kabul et", "AnyDesk'i kabul et" gibi ifadelerde tetikle.
---

# Jarvis Bridge Skill

Ekrem'in Jarvis Mission Control sistemini yönetmek için tam referans. SSH yoktur.

---

## Sistem Mimarisi

```
[Telegram] ←→ [telegram_gateway_v2.py] ←→ [JarvisRouter] ←→ [CoreAgent]
                        ↓                          ↓
               /opt/jarvis/ (WSL)         Claude / Ollama Agents

[Claude Chat] → trigger dosyası → anydesk_watcher.bat → anydesk_kabul.ps1
```

**Sunucu:** WSL (Ubuntu) — Windows içinde, Pinokio tarafından yönetiliyor
**Jarvis kök:** `/opt/jarvis/`
**Masaüstü geliştirme:** `C:\Users\sergen\Desktop\jarvis-mission-control\`
**WSL'den masaüstüne:** `/mnt/c/Users/sergen/Desktop/`
**SSH:** ❌ Kapalı — BAT veya Telegram /cmd kullan

---

## AnyDesk Bağlantı İsteği Onaylama

### Yöntem 1 — Telegram'dan (Ekrem dışardayken)
```
/kabul
```
Jarvis, `anydesk_kabul.ps1`'i çalıştırır → AnyDesk Accept butonuna basar.

### Yöntem 2 — Claude Sohbeti Üzerinden
Kullanıcı "onayla", "kabul et" veya "AnyDesk'i kabul et" dediğinde:

1. Masaüstüne trigger dosyası yaz:
```python
# Bu kodu çalıştır (Bash tool ile):
with open('/sessions/wonderful-adoring-fermat/mnt/Desktop/.anydesk_trigger', 'w') as f:
    f.write('accept')
```
2. Kullanıcıya bildir: "AnyDesk bağlantısı kabul ediliyor."
3. Arka planda `anydesk_watcher.bat` çalışıyorsa otomatik halleder.

**NOT:** `anydesk_watcher.bat`'ın arka planda açık olması gerekir. Kullanıcıya bilgisayar açılışında bir kez çalıştırmasını öner.

### anydesk_kabul.ps1 Mantığı
- AnyDesk penceresini UI Automation ile bulur
- "Accept" / "Kabul Et" butonunu arar ve tıklar
- Bulamazsa pencereyi öne alıp Enter gönderir
- Masaüstünde: `C:\Users\sergen\Desktop\anydesk_kabul.ps1`

---

## SSH Olmadan Deploy — BAT Yöntemi

**Şablon:**
```bat
@echo off
wsl cp /mnt/c/Users/sergen/Desktop/jarvis-mission-control/<dosya> /opt/jarvis/<dosya>
if errorlevel 1 ( echo HATA! & pause & exit /b 1 )
wsl pkill -f <servis_adi>
timeout /t 2 /nobreak >nul
wsl bash -c "nohup python3 /opt/jarvis/<servis>.py > /opt/jarvis/logs/<servis>.log 2>&1 &"
pause
```

**Kurallar:**
- `wsl <komut>` — tek Linux komutu
- `wsl bash -c "cmd1 && cmd2"` — zincirleme
- Şifre gerekmez (WSL Windows'tan doğrudan erişir)

---

## Telegram /cmd ile Deploy (Gateway Çalışıyorken)

```
/cmd cp /mnt/c/Users/sergen/Desktop/jarvis-mission-control/<dosya> /opt/jarvis/<dosya>
/cmd pkill -f telegram_gateway_v2.py && sleep 2 && nohup python3 /opt/jarvis/telegram_gateway_v2.py > /opt/jarvis/logs/gateway.log 2>&1 &
```

---

## Mevcut Telegram Komutları

| Komut | Açıklama |
|-------|----------|
| `/status` | Sunucu CPU/RAM/disk durumu |
| `/memory` | Son konuşmalar |
| `/tasks` | Son görevler |
| `/cmd <komut>` | Terminal komutu çalıştır (60s timeout) |
| `/kabul` | AnyDesk bağlantı isteğini kabul et |
| `/onayla` | /kabul ile aynı |
| `/accept` | /kabul ile aynı |
| `/help` | Komut listesi |

---

## Temel Dosya Yolları

| Amaç | Yol |
|------|-----|
| Gateway | `/opt/jarvis/telegram_gateway_v2.py` |
| Router | `/opt/jarvis/jarvis_router.py` |
| Core agent | `/opt/jarvis/core/agent.py` |
| Skills | `/opt/jarvis/skills/` |
| Logs | `/opt/jarvis/logs/` |
| Memory | `/opt/jarvis/memory/` |
| Soul | `/opt/jarvis/soul.md` |
| AnyDesk script | `C:\Users\sergen\Desktop\anydesk_kabul.ps1` |
| AnyDesk watcher | `C:\Users\sergen\Desktop\anydesk_watcher.bat` |
| Deploy script | `C:\Users\sergen\Desktop\deploy_gateway.bat` |

---

## Servis Yönetimi

### Gateway Restart (BAT ile)
```bat
wsl cp /mnt/c/Users/sergen/Desktop/jarvis-mission-control/telegram_gateway_v2.py /opt/jarvis/telegram_gateway_v2.py
wsl pkill -f telegram_gateway_v2.py
timeout /t 2 /nobreak >nul
wsl bash -c "nohup python3 /opt/jarvis/telegram_gateway_v2.py > /opt/jarvis/logs/gateway.log 2>&1 &"
```

### Durum Kontrolü
```bash
ps aux | grep -E "telegram_gateway|bridge.py" | grep -v grep
tail -20 /opt/jarvis/logs/gateway.log
```

---

## Gateway'e Yeni Komut Ekleme

```python
@bot.message_handler(commands=["yeni_komut"])
def cmd_yeni(message):
    if not is_authorized(message):
        return
    bot.send_chat_action(message.chat.id, "typing")
    # İşlem
    send(message.chat.id, "Sonuç")
```
Sonra: `deploy_gateway.bat` çalıştır.

---

## Yeni Skill Ekleme

```python
"""Skill: <isim> | Kategori: execution|cognitive|governance|io"""
MANIFEST = {"name": "<isim>", "version": "1.0", "category": "<kategori>",
            "inputs": {}, "outputs": {}, "permissions": []}

def run(**kwargs) -> dict:
    try:
        return {"result": "...", "success": True, "error": None}
    except Exception as e:
        return {"result": None, "success": False, "error": str(e)}
```

---

## Önemli Notlar

- **SSH kapalı** — tüm işlemler BAT veya /cmd üzerinden
- **Pinokio**, Jarvis'i WSL'de yönetir — Claude doğrudan kontrol edemez
- **RAM:** Yaklaşık %94 kullanımda — çok model açma
- **AnyDesk watcher** bilgisayar açılışında bir kez başlatılmalı
- Geliştirme masaüstü klasöründe yapılır → WSL'e kopyalanır
- `AUTHORIZED_CHAT_ID` değiştirilmez (güvenlik)
