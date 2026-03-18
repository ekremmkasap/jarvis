# Jarvis — Komut & Workflow Bilgisi
# Jarvis bu dosyayı kendi yetenekleri ve iş akışları için referans alır.

## Sunucu Bilgileri
- **IP:** 192.168.1.109 (yerel ağ)
- **OS:** Kali Linux (VirtualBox VM)
- **Kullanıcı:** userk
- **Ana dizin:** /opt/jarvis/
- **Log:** /home/userk/.jarvis/jarvis.log

## Servisler
- `jarvis.service` → Ana AI gateway (systemd, auto-restart)
- `ollama.service` → AI model sunucusu
- Web Dashboard: http://192.168.1.109:8080

## Jarvis Komutları
| Komut | Açıklama |
|-------|----------|
| `/help` | Tüm komutlar |
| `/status` | CPU, RAM, servis durumu |
| `/models` | Yüklü Ollama modelleri |
| `/reset` | Konuşma geçmişini sil |
| `/ebay [ürün]` | eBay pazar analizi |
| `/trendyol [ürün]` | Trendyol TR analizi |
| `/code [görev]` | Kod yaz (deepseek-coder) |
| `/plan [proje]` | Proje planla (deepseek-r1) |
| `$ [komut]` | Sunucu komutu çalıştır |

## AI Model Routing
| Kelimeler | Model |
|-----------|-------|
| kod, python, bug, fix, script | deepseek-coder |
| neden, analiz, planla, strateji | deepseek-r1 |
| ebay, trendyol, ürün, fiyat | llama3.2 |
| sistem, sunucu, servis, cpu | Shell |
| Her şey else | llama3.2 |

## Skill Dosyaları
- `/opt/jarvis/skills/heartbeat.py` → Sabah 08:00 brief
- `/opt/jarvis/skills/ebay_research.py` → eBay analiz
- `/opt/jarvis/skills/trendyol_skill.py` → Trendyol analiz
- `/opt/jarvis/skills/whisper_skill.py` → Ses transkripsiyonu
- `/opt/jarvis/skills/wa_skill.py` → WhatsApp API

## Ollama Model Listesi
- `llama3.2:latest` — Genel konuşma, hızlı cevap
- `deepseek-r1:latest` — Akıl yürütme, planlama
- `deepseek-coder:latest` — Kod yazma
- `qwen2.5-coder:7b` — Alternatif coder
- `mistral:latest` — Analiz ve yazma

## Günlük Sabah Briefingi (08:00)
Her sabah otomatik Telegram mesajı:
- Sistem durumu (CPU/RAM/disk)
- Ollama model durumu
- 3 eBay/ticaret fırsatı önerisi
- Motivasyon cümlesi

## Gelecek Eklemeler
- [ ] WhatsApp entegrasyonu (wa_bridge.js npm install gerekiyor)
- [ ] Whisper ses tanıma (pip install bekleniyor)
- [ ] Etsy API entegrasyonu
- [ ] Instagram DM botu
- [ ] Google Sheets senkronizasyonu
