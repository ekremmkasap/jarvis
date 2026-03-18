# Jarvis Minimal Runbook

## 1) Hizli Saglik Kontrolu
```bash
python stabilize_and_report.py
```

Rapor yolu:
- `holding_merkezi/outputs/sistem_durum_raporu.md`

## 2) Kritik Kontrol Basliklari
- Kopya dosya uyarilari (`bridge.py`, `jarvis_router.py`, `DEVLOG.md`)
- Secret taramasi uyari sayisi
- Holding input/output durumlari

## 3) Calisma Prensibi
- Kod degisikligi yaparken sadece `server/SOURCE_OF_TRUTH.md` icindeki resmi hat kullanilir.
- Legacy dosyalar referans icin tutulur, uretim kaynagi degildir.

## 4) Onerilen Siralama
1. Secret temizligi (dosyadan env/secret file modeline gecis)
2. Kopya dosya arsivleme (legacy klasoru)
3. Log standardizasyonu
