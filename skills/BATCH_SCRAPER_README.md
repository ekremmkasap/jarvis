# Batch Scraper

`server/skills/batch_profile_scraper_codex.py` toplu Instagram ve YouTube profil cekimi icin bridge-uyumlu bir beceri sunar.

## Giris

- CSV: `hesap,platform` kolonlariyla `@leadgenman,instagram`
- Liste: `["@leadgenman", "@alexlindai", "https://youtube.com/c/Channel"]`

## Komut

```text
/batch-scrape handles.csv
/batch-scrape @leadgenman,@alexlindai
/batch-scrape @leadgenman
@alexlindai
```

## API

```python
from server.skills.batch_profile_scraper_codex import BatchProfileScraper

scraper = BatchProfileScraper(max_concurrent=5, timeout=30, max_retries=2)
result = await scraper.scrape_batch(["@leadgenman", "@alexlindai"])
```

CSV icin:

```python
result = await scraper.batch_scrape_from_csv("handles.csv")
```

## Cikti

Varsayilan klasor: `outputs/batch_scrapes/<timestamp>_profiller/`

Olusan dosyalar:

- Profil bazli `*.json`
- `ozet_rapor.json`
- `engagement_analizi.json`
- `monetization_tahminleri.json`
- `hata_log.json`

## Sonuc Alani

Onemli alanlar:

- `toplam`
- `basarili`
- `basarisiz`
- `output_path`
- `report_path`
- `saved_files`
- `analysis`
- `monetization`
- `summary`

## Notlar

- Bridge wrapper hem async handler hem `BatchProfileScraper` sinifi ile calisir.
- Test kolayligi icin `BatchProfileScraper(scraper=...)` ile fake scraper enjekte edilebilir.
- Rate limiting ihtiyaci varsa `request_spacing_seconds` degeri yukseltilmelidir.
- Gercek Instagram smoke icin `INSTAGRAM_USERNAME` ve `INSTAGRAM_PASSWORD` ayarlanmasi onerilir; login olmadan Instagram GraphQL 403 donebilir.
- Gercek YouTube smoke icin `YOUTUBE_API_KEY` ayarlanmalidir; scraper bu env degerini otomatik okur.

## Gercek Smoke Komutlari

Paket/env kontrolu:

```powershell
python -c "import importlib.util, os, json; print(json.dumps({'instaloader': importlib.util.find_spec('instaloader') is not None, 'googleapiclient': importlib.util.find_spec('googleapiclient') is not None, 'YOUTUBE_API_KEY': bool(os.environ.get('YOUTUBE_API_KEY')), 'INSTAGRAM_USERNAME': bool(os.environ.get('INSTAGRAM_USERNAME')), 'INSTAGRAM_PASSWORD': bool(os.environ.get('INSTAGRAM_PASSWORD'))}, ensure_ascii=False))"
```

Tek profil smoke:

```powershell
python -c "import asyncio, json; from server.services.universal_profile_scraper import scrape_profile_handler; print(json.dumps(asyncio.run(scrape_profile_handler('@leadgenman','instagram')), ensure_ascii=False, indent=2))"
```

Batch smoke:

```text
/batch-scrape C:\Users\sergen\Desktop\jarvis-mission-control\tmp\handles.sample.csv
```
