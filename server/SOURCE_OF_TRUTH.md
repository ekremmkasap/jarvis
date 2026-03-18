# Jarvis Source of Truth

Bu dokuman, daginik kopya riskini azaltmak icin resmi calisma hattini tanimlar.

## Resmi Hat
- Uygulama cekirdegi: `server/openclaw/bridge.py`
- Tenancy ayarlari: `server/tenants/*/config.json`
- Operasyon notlari: `server/DEVLOG.md`

## Legacy Olarak Degerlendirilecekler
- `server/bridge.py`
- `src/runtime/dev/bridge.py`
- `faz2a/jarvis_router.py`
- Klasor kokundeki deneysel deploy/fix scriptleri

## Kural
1. Uretim degisikligi sadece resmi hat dosyalarinda yapilir.
2. Legacy dosyalarda bug fix uygulanmaz.
3. Deploy oncesi `holding_merkezi/outputs/sistem_durum_raporu.md` kontrol edilir.
