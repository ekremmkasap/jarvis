# Hot Cache — En Güncel Bilgi (500 kelime özet)

Son güncelleme: 2026-04-08

## Bu Hafta Ne Yapıldı?
- LLM Wiki sistemi Jarvis'e entegre edildi
- Karpathy yöntemi ile wiki klasör yapısı oluşturuldu
- Mert Durmaz videosu ve PDF'i ham veri olarak eklendi
- gemma4:e2b model değişikliği bridge.py'ye uygulandı (GTX 1650 4GB VRAM yetmediği için dikkatli olunacak)

## Aktif Sistem Durumu
- Jarvis repo: C:/Users/sergen/Desktop/jarvis-mission-control/
- Model: gemma4:e2b (bridge.py'de aktif)
- Wiki: /wiki/ klasöründe kurulu

## LLM Wiki Konsepti (Özet)
Karpathy'nin fikri: ham veriyi raw/ klasörüne at, Claude Code organize edip wiki/ klasörüne yazar. Vektör DB yok, embedding yok. %95 token tasarrufu. Obsidian ile görselleştirilebilir.

## Sonraki Adımlar
1. Obsidian indir ve wiki/ klasörünü vault olarak aç
2. Jarvis hologramını restore et
3. Stripe webhook'u tamamla
