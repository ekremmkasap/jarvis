---
tags: [knowledge, voice, tts, asr, microsoft, open-source]
date: 2026-04-16
source: github,instagram
---

# VibeVoice (Microsoft)

Open-source voice AI — **60 dakikalık audio transcription**, speaker diarization, 50+ dil desteği.

## Özellikler
- ASR + TTS + streaming tek pakette
- Speaker diarization (kim konuşuyor tespiti)
- 50+ dil — Türkçe dahil
- Uzun form: 60 dk tek pass
- Open source (GitHub)

## Repo
https://github.com/microsoft/VibeVoice

## Neden Önemli
Jarvis şu an **Piper tr_TR-dfki-medium** (TTS) + **RealtimeSTT** (Logitech G733 STT) kullanıyor. VibeVoice ikisini birleştiriyor + uzun form + diarization ekliyor.

## Jarvis İçin Değerlendirme
**Aday entegrasyon — `hey_jarvis.py` STT katmanı için**
- Avantaj: tek kütüphane, uzun form, multi-speaker
- Dezavantaj: Ollama gibi lokal mi yoksa cloud mu? Kaynak kullanımı?
- Test ederken: mevcut Piper/RealtimeSTT'yi bozma (fallback kalsın)

## Kaynaklar
- https://github.com/microsoft/VibeVoice
- https://www.instagram.com/p/DW5QgSBEyM6/

## İlgili
- [[02-Projects/jarvis-mission-control]] — mevcut voice stack
- [[05-Resources/github-repos]]
