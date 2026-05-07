# LLM Wiki (Karpathy Yöntemi)

Bağlantılar: [[index]] | [[mertdurmaz-videolar]]

## Konsept
Andrej Karpathy'nin viral fikri. Ham veriyi yapay zekaya ver, o organize etsin.
- Vektör DB yok, embedding yok
- Sadece markdown dosyaları
- %95 token tasarrufu
- 383 dosya → compact wiki

## Klasör Yapısı
```
raw/          ← ham veri
wiki/         ← organize edilmiş bilgi
wiki/index.md ← navigasyon
wiki/hot.md   ← 500 kelimelik güncel özet
wiki/log.md   ← işlem geçmişi
```

## Obsidian Entegrasyonu
- wiki/ klasörünü Obsidian vault olarak aç
- Mind map görselleştirme
- Konseptler arası link takibi
- Graph view ile ilişki haritası

## Jarvis'e Bağlantı
CLAUDE.md'de wiki path tanımlı → tüm sohbetlerde otomatik erişim.

## Kaynaklar
- Video: https://youtu.be/WXcIArINefw (Mert Durmaz)
- PDF: karpathy-llm-wiki-rehberi.pdf
