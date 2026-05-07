# Persona Voice Smoke

## Amaç

Persona değişiminde hologram rengi ve TTS sesinin birlikte güncellendiğini doğrula.

## Adımlar

1. Jarvis backend, `hey_jarvis.py` ve desktop hologram uygulamasını başlat.
2. Aktif personayı `buse` yap.
3. Hologram glow renginin `#ff69b4` olduğunu doğrula.
4. Persona greeting veya ilk yanıtta `EmelNeural` sesi duyulduğunu doğrula.
5. Aktif personayı `seda` yap.
6. Hologram glow renginin `#00ff88` olduğunu doğrula.
7. Persona greeting veya ilk yanıtta `AhmetNeural` sesi duyulduğunu doğrula.
8. Aynı persona iki kez üst üste seçildiğinde greeting tekrar spam yapmamalı.

## Beklenen Sonuç

- `buse` aktifken hologram pembe glow ile görünür ve kadın ses kullanılır.
- `seda` aktifken hologram yeşil glow ile görünür ve AhmetNeural sesi kullanılır.
- Aynı persona yeniden aktif edilmeden greeting tekrar çalmaz.
