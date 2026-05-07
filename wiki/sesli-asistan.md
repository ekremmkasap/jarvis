# Jarvis — Sesli Asistan (Hey Jarvis)

## Mod: HOLOGRAM COMPUTER MODE (Aktif)
- Ses efekti: Ring Modülasyon (80Hz) + Echo (38ms + 75ms) + Pitch Shift (x1.08 derin)
- Başlangıç: "Hologram bilgisayar modu aktif. Ekrem, sizi dinliyorum."
- Terminal: Cyan ASCII art banner

## Genel Bilgi
- Ana dosya: `C:/Users/sergen/Desktop/jarvis-mission-control/hey_jarvis.py`
- Başlatma: `C:/Users/sergen/Desktop/JARVIS_BASLAT.bat` (tek tıkla)
  - bridge.py → pythonw.exe (arka planda, görünmez)
  - hey_jarvis.py → ön pencerede

## Bileşenler

| Bileşen | Teknoloji | Detay |
|---------|----------|-------|
| STT | RealtimeSTT (faster-whisper) | input_device_index=9 = Logitech G733 |
| TTS | Piper tr_TR-dfki-medium | `C:/Users/sergen/AppData/Local/piper-models/` |
| LLM | minimax-m2.7:cloud | OLLAMA_KEY ile cloud erişim |
| PC Kontrol | pyautogui | — |

## PC Kontrol Komutları
- `##KOMUT:##` — shell komutu çalıştır
- `##TIKLA:##` — mouse tıklama
- `##YAZ:##` — klavye yazma
- `##TUS:##` — tuş basma
- `##EKRANGÖR##` — ekran görüntüsü

## AnyDesk Kabul
- Script: `C:/pinokio/api/ekrem/app/anydesk_kabul.ps1`
- Tam yol gerekli (relative path çalışmıyor)

## Konuşma Kaydı
- Dosya: `jarvis_konusmalar.txt` (Desktop/jarvis-mission-control/ altında)

## Python Ortamı
- Python311: faster-whisper, RealtimeSTT, pyautogui, piper, sounddevice

## İlgili Sayfalar
- [[mimari-genel-bakis]]
- [[model-routing]]
