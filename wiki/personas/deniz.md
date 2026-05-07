# Deniz — E-ticaret / Pazaryeri Persona

**Domain:** E-ticaret operasyonu, pazaryeri analizi
**Codex slot:** nexus
**Ses:** AhmetNeural

## Kapsam

3 pazaryeri + 1 print-on-demand entegrasyonu:
- **eBay** — satılmış fiyat analizi, fırsat taraması
- **Trendyol** — arama sonuçları + ollama ile yorum
- **Printify** — shop/ürün/sipariş özetleri (token gerekli)

## Bridge Komutları

| Komut | Ne yapar |
|-------|----------|
| `/deniz-ebay <urun>` | eBay'de satılmış fiyatları analiz eder. |
| `/deniz-trendyol <urun>` | Trendyol araması + fiyat/rekabet yorumu. |
| `/deniz-printify overview` | Shop + ürün + son siparişler özeti. |
| `/deniz-printify firsat <niche>` | Niche bazlı fırsat analizi. |
| `/deniz-rakip <urun>` | eBay + Trendyol'da ortalama fiyat karşılaştırma. |

## Environment

- `PRINTIFY_TOKEN` — `.env`'de. Yoksa `/deniz-printify` uyarı döner.
- eBay / Trendyol — public endpoint, token gerekmez (ebay_research.py, trendyol_skill.py).

## İlgili Dosyalar

- `server/skills/ebay_research.py`
- `server/skills/trendyol_skill.py`
- `server/skills/printify_skill.py`
- `server/bridge.py` — `/deniz-*` komut register blokları
- `tests/test_deniz_bridge_commands.py`
