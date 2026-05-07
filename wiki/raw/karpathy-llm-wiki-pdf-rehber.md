# Karpathy LLM Wiki - PDF Rehberi
Kaynak: karpathy-llm-wiki-rehberi.pdf (Mert Durmaz)
Tarih: 2026-04-08

## Klasör Yapısı
```
raw/          ← ham veri (makale, transkript, not)
wiki/         ← Claude'un organize ettiği bilgi
wiki/index.md ← tüm sayfaların listesi (ana navigasyon)
wiki/log.md   ← işlem geçmişi
wiki/hot.md   ← en son bilginin 500 kelimelik özeti
.claude/claude.md ← Claude'un davranış kuralları
```

## Kurulum Prompt'u
```
You are my LLM wiki agent. Implement Karpathy's LLM wiki idea as my second brain. 
This project is specifically for [AMAÇ]. 
Create the claude.md, the folder structure, the index, and the log.
```

## Kaynak Ekleme Komutları
- Manuel: raw/ klasörüne dosya at → "Ingest this" de
- Web Clipper: Chrome extension ile hızlı clip

## Performans
| Girdi | Claude'un Yarattığı | Süre |
|-------|---------------------|------|
| 1 makale | 10-25 wiki sayfası | ~10 dk |
| 36 YouTube transkripti | Yüzlerce ilişkilendirilmiş sayfa | ~14 dk |
| 5 rakip sitesi | Her rakip için sayfa + karşılaştırma | ~20 dk |

## Sorgulama Prompt'ları
- Genel: "What do all my sources say about [KONU]?"
- Boşluk bul: "Where are the gaps in my knowledge about [KONU]?"
- İlişki: "Which people/concepts appear across multiple sources?"
- Bakım: "Run a lint. Find inconsistencies and interesting connections."

## Bağlantı (claude.md'ye ekle)
```
## Wiki Path
When you need information: 
1. Go to /wiki/wiki/
2. hot.md → most recent info
3. index.md → list of all pages
4. Read wiki pages as needed
Do not read the wiki unless you actually need it.
```

## LLM Wiki vs RAG Karşılaştırması
| | LLM Wiki | Geleneksel RAG |
|--|---------|----------------|
| Altyapı | Sadece markdown | Embedding + vektör DB |
| Kurulum | 5 dakika | Saatler/günler |
| Maliyet | Sadece LLM token | Sürekli compute |
| Arama | Index oku + bağlantı takip | Similarity search |
| İlişki | Derin (linkler) | Yüzeysel |
| En iyi | Yüzlerce sayfa | Milyonlarca doküman |
