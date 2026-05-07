# Sabri — Reklam Ajansı Persona

**Domain:** Reklam ajansı / AI creative director
**Codex slot:** atlas
**Ses:** AhmetNeural
**Renk teması:** `config/agents.yaml` personas bloğunda.

## Framework Referansı

Sabri, Mert Durmazer'in Digital Academy framework'una ilham alan 4 fonksiyonlu kampanya pipeline'ı üzerine kurulu. Bkz. [[mert-durmazer-framework]].

Akış:
```
brief alma  →  copy üretim  →  görsel prompt  →  kampanya planı
```

## Bridge Komutları

| Komut | Ne yapar |
|-------|----------|
| `/sabri-brief <musteri notu>` | Serbest notu brand/audience/goal/tone/budget alanlarına çıkarır, `state/agent_memory/sabri/briefs/<brief_id>.json` olarak kaydeder. |
| `/sabri-copy <brief_id> [platform]` | Brief'ten 3 alternatif copy varyantı üretir (problem-çözüm, sosyal kanıt, aciliyet). Platformlar: `meta`, `google`, `linkedin`, `instagram`, `tiktok`. |
| `/sabri-gorsel <brief_id>` | 3 Midjourney/DALL-E prompt'u (hero shot, lifestyle, key visual). |
| `/sabri-kampanya <brief_id> <butce_tl> [gun]` | Hedefe göre kanal mix + faz takvimi + KPI hedefi. |

## Örnek Müşteri Akışı

```
1. Müşteri: "Bir restoran zinciri için Instagram kampanyası, 15000 TL, hedef yeni müşteri"
2. /sabri-brief Bir restoran zinciri için Instagram kampanyası, 15000 TL, hedef yeni müşteri
   → brief_id: restoran-zinciri_20260420_193000
3. /sabri-copy restoran-zinciri_20260420_193000 instagram
   → 3 varyant döner
4. /sabri-gorsel restoran-zinciri_20260420_193000
   → 3 görsel prompt
5. /sabri-kampanya restoran-zinciri_20260420_193000 15000 30
   → mix: meta %40 / google %20 / instagram %25 / tiktok %15
```

## Domain Sınırları

- Out-of-domain istekler ilgili persona'ya yönlendirilir (bkz. `config/agents.yaml` `handoff_targets`).
- Teknik kod = Seda, araştırma = Mert, e-ticaret = Deniz.

## İlgili Dosyalar

- `server/skills/sabri_campaign_skill.py` — 4 fonksiyon
- `server/skills/sabri_openclaw_skill.py` — OpenClaw entegrasyonu (bağımsız kullanım)
- `server/bridge.py` — `/sabri-*` komut register blokları
- `tests/test_sabri_campaign.py` — smoke testler
