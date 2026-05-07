# Jarvis — Öz-Öğrenme Sistemi

## Mimari

```
Her Telegram komutu
        │
        ▼
ConversationLearner.log_command()
        │ (conversations.jsonl)
        ▼
/ogren komutu → Ollama analiz
        │
        ▼
insights.md + wiki/hot.md güncelleme
        
Ayrı: SkillAutoTuner (Karpathy döngüsü)
  prompt → test → skor → varyasyon → skor → en iyi tut
```

## Dosyalar

| Dosya | Görev |
|-------|-------|
| `server/agents/conversation_learner.py` | Komut loglama + Ollama analiz |
| `server/agents/skill_auto_tuner.py` | Karpathy döngüsü — prompt optimizasyon |
| `server/agents/self_learning_agent.py` | Pattern analiz + self-improvement loop |
| `server/logs/learning/conversations.jsonl` | Ham komut logları |
| `server/logs/learning/insights.md` | Öğrenilen bilgiler |
| `server/logs/tuning/tuning_log.jsonl` | Tuning geçmişi |

## Telegram Komutları

| Komut | Açıklama |
|-------|---------|
| `/ogren` | Son 300 komutu analiz et, pattern çıkar, öğren |
| `/rapor` | Son öğrenme raporunu göster |
| `/tune [skill]` | Bir skill'in promptunu Karpathy döngüsüyle optimize et |

## Nasıl Çalışır

### 1. Otomatik Loglama
Her `/komut` çalıştığında `ConversationLearner` şunu kaydeder:
- Komut adı
- Girdi/çıktı uzunluğu
- Süre (ms)
- Başarı/hata durumu

### 2. `/ogren` Analizi
- Son 300 komutu okur
- İstatistik hesaplar (en çok kullanılan, en çok hata veren, ortalama süre)
- Ollama'ya gönderir: "Ne öğrenmeli?"
- Sonucu `insights.md` ve `wiki/hot.md`'ye yazar

### 3. SkillAutoTuner (Karpathy Döngüsü)
```
mevcut_prompt → skor(test_inputs)
    │
    ▼
LLM → varyasyon_prompt
    │
    ▼
skor(test_inputs) → varyasyon_skoru
    │
    ├── varyasyon > mevcut → kabul et
    └── varyasyon ≤ mevcut → geri al
    │
    ▼
tekrar (N iterasyon)
```

## İlgili Sayfalar
- [[mimari-genel-bakis]]
- [[model-routing]]
- [[telegram-komutlari]]
