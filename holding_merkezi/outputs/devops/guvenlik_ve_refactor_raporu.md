# Uygulamam Gereken %100 Garantili Terminal Komutları ve Python Kod Refactor Önerileri

## 1) Sistem Röntgeni (Yerel Elde Edilen Kanıtlar)
- openclaw logunda `Standard output type syslog is obsolete` uyarısı var.
- openclaw gateway logu boş: `-- No entries --`
- startup log değeri: `NO_LOG`
- bridge tarafında kritik hata izi mevcut: `_get_best_model` tanımlanmadan çağrılmış.

## 2) Doğrudan Uygulanabilir Terminal Komutları
```bash
# 1) Servis dosyasında eski syslog çıktısını kaldır
sudo cp /etc/systemd/system/openclaw.service /etc/systemd/system/openclaw.service.bak
sudo sed -i '/StandardOutput=syslog/d;/StandardError=syslog/d' /etc/systemd/system/openclaw.service

# 2) systemd yenile ve servisleri yeniden başlat
sudo systemctl daemon-reload
sudo systemctl restart openclaw.service
sudo systemctl restart jarvis.service

# 3) Son 200 satır logu doğrula
sudo journalctl -u openclaw.service -n 200 --no-pager
sudo journalctl -u jarvis.service -n 200 --no-pager

# 4) Python sözdizimi kontrolü
python3 -m py_compile /opt/jarvis/openclaw/bridge.py
```

## 3) Python Refactor (Çökme Önleme)
- `MODEL_ROUTES` içinde fonksiyon çağrısı kullanılacaksa `_get_best_model` tanımı önce gelmeli.
- Tüm API çağrıları `try/except` içinde kalmalı; hata durumunda fallback model dönmeli.
- Uzun süren model çağrılarını kuyrukla sınırla (aynı anda max 2 istek).

## 4) Fail-Safe Standardı
- Dosya okuma/yazma: try/except + varsayılan değer.
- Ağ çağrısı: timeout + fallback + log.
- Kritik dosyada yedek: `.bak` kuralı zorunlu.

## 5) Ham Hata İzleri
```
Feb 28 17:48:49 userk systemd[1]: /etc/systemd/system/openclaw.service:12: Standard output type syslog is obsolete, automatically updating to journal. Please update your unit file, and consider removing the setting altogether.
Feb 28 17:48:49 userk systemd[1]: /etc/systemd/system/openclaw.service:13: Standard output type syslog is obsolete, automatically updating to journal. Please update your unit file, and consider removing the setting altogether.
Feb 28 17:48:49 userk systemd[1]: Started openclaw.service - OpenClaw AI Orchestrator Service.
Feb 28 17:59:09 userk systemd[1]: /etc/systemd/system/openclaw.service:12: Standard output type syslog is obsolete, automatically updating to journal. Please update your unit file, and consider removing the setting altogether.
Feb 28 17:59:09 userk systemd[1]: /etc/systemd/system/openclaw.service:13: Standard output type syslog is obsolete, automatically updating to journal. Please update your unit file, and consider removing the setting altogether.
Feb 28 17:59:10 userk systemd[1]: /etc/systemd/system/openclaw.service:12: Standard output type syslog is obsolete, automatically updating to journal. Please update your unit file, and consider rem

--- bridge_err ---
RC:1
STDERR:
2026-03-01 23:05:35,368 [INFO] Bilgi bankasi yuklendi: ['jarvis_komutlar', 'ebay_strateji', 'jarvis_mimari', 'agentclaw_mimari', 'trendyol_strateji', 'ai_icerik_araclari', 'profil', 'agentclaw_ajans']
2026-03-01 23:05:35,368 [INFO] ✅ soul.md yuklendi
Traceback (most recent call last):
  File "/opt/jarvis/openclaw/bridge.py", line 112, in <module>
    "model": _get_best_model("general"),
             ^^^^^^^^^^^^^^^
NameError: name '_get_best_model' is not defined

STDOUT:

```
