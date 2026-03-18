# Jarvis Sistem Durum Raporu

- Uretim zamani: 2026-03-03T20:21:00
- Klasor: C:\Users\sergen\Desktop\jarvis-mission-control

## Bulgu Ozeti
- [UYARI] Kopya Kontrolü: bridge.py: bridge.py için 3 kopya bulundu: server\bridge.py, server\openclaw\bridge.py, src\runtime\dev\bridge.py
- [UYARI] Kopya Kontrolü: jarvis_router.py: jarvis_router.py için 2 kopya bulundu: jarvis_router.py, faz2a\jarvis_router.py
- [OK] Kopya Kontrolü: telegram_gateway_v2.py: telegram_gateway_v2.py için çakışma riski görülmedi
- [UYARI] Kopya Kontrolü: DEVLOG.md: DEVLOG.md için 2 kopya bulundu: DEVLOG.md, server\DEVLOG.md
- [UYARI] Secret Taraması: 48 potansiyel iz bulundu
- [BILGI] Secret Örnekleri: server\bridge.py:23 [telegram_token] 8295...Dt-k | server\bridge_server.py:21 [telegram_token] 8295...Dt-k | server\DEVLOG.md:51 [telegram_token] 8295...Dt-k | server\ROADMAP.md:30 [telegram_token] 8295...Dt-k | server\agent_prompts\wshobson\plugins\backend-development\skills\api-design-principles\SKILL.md:429 [api_key_like] pass...word
- [OK] Holding Input Kontrol: Temel input dosyaları mevcut
- [BILGI] Holding Output Durumu: Toplam çıktı dosyası: 16

## Onerilen Sirali Aksiyonlar
1. Tek resmi çalışma hattını `server/` olarak sabitle ve diğer kopyaları `legacy/` altında arşivle.
2. Token/secret değerlerini dosyalardan kaldır, sadece ortam değişkeni veya secret dosyasıyla oku.
3. Bridge için tek dosya politikası uygula: deploy yalnızca `server/openclaw/bridge.py` üzerinden yürüsün.
4. Servis log standardını netleştir: systemd syslog uyarılarını kaldır, startup log üretimini zorunlu kıl.
5. Holding akışında HITL adımını zorunlu tut: görsel seçimi olmadan video aşamasına geçme.

## Sonuc
- Sistem calisabilir durumda, ancak kopya dosya ve secret hijyeni nedeniyle operasyonel risk devam ediyor.
- Sonraki odak: tek kaynak hatti + secret temizligi + log standardizasyonu.