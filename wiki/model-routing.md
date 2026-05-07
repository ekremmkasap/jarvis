# Jarvis — Model Routing

## Routing Tablosu

| Chain | Birincil Model | Fallback |
|-------|---------------|---------|
| `code` | `claude-sonnet-4-6` via OpenRouter | `deepseek/deepseek-v3.2` |
| `reasoning` | `claude-opus-4.6` via OpenRouter | `z-ai/glm-5-turbo` |
| `chat` | `minimax/minimax-m2.7` via OpenRouter | `stepfun/step-3.5-flash:free` |
| `default` | `qwen3:8b` via Ollama | `deepseek/deepseek-v3.2` |

## Ollama Modelleri (Lokal)

| Model | Boyut | Kullanım |
|-------|-------|---------|
| llama3.2:latest | 2.0GB | Genel, varsayılan (~5sn yanıt) |
| qwen2.5-coder:7b | 4.7GB | Kod (code route) |
| qwen3:4b | 2.5GB | Genel alternatif |
| deepseek-r1:8b | 5.2GB | Derin akıl yürütme (reasoning) |
| moondream:latest | 1.7GB | Görsel analiz |

## Performans Notu
- llama3.2 CPU'da ~3 tok/sn → yavaş
- Marketing komutları: /reklam ~78sn, /analiz ~53sn
- Çözüm: Daha küçük model denemeleri (deepseek-coder:776MB)

## İlgili Sayfalar
- [[ajanlar]]
- [[mimari-genel-bakis]]
