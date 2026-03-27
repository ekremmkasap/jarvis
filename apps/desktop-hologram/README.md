# Jarvis Desktop Hologram

Electron tabanli, always-on-top, transparent overlay asistan.

## Bagimliliklari Kur
```
cd apps/desktop-hologram
npm install
```

## Baslat
```
npm start
```

## Kullandigi Endpointler
- `http://127.0.0.1:8081/api/desktop-assistant` — aktif agent durumu
- `http://127.0.0.1:8081/api/office/presence` — presence feed

## State Fazlari
- `idle` — beklemede
- `listening` — sesi dinliyor
- `thinking` — cevap uretiliyor
- `speaking` — sesli yanit veriyor
- `offline` — backend baglanamadi
