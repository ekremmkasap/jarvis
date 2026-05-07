# Codex Accounts

Yerel `~/.codex/auth.json` dosyasini snapshot alarak birden fazla Codex hesabini yonetmek icin:

## Komutlar

```powershell
cd C:\Users\sergen\Desktop\jarvis-mission-control

.\codex-accounts.ps1 current
.\codex-accounts.ps1 add atlas --note "Mimari hesap"
.\codex-accounts.ps1 add forge --note "Core dev hesap"
.\codex-accounts.ps1 list
.\codex-accounts.ps1 switch atlas
```

## Akis

1. Codex App/CLI ile istedigin hesaba giris yap.
2. `add <slot>` ile aktif hesabi kaydet.
3. Sonraki hesaba gec ve tekrar `add`.
4. Tum slotlar dolunca `switch <slot>` ile aktif hesabi degistir.

## Notlar

- Snapshot dosyalari `C:\Users\sergen\Desktop\jarvis-mission-control\state\codex-accounts\` altina yazilir.
- Aktif hesap degistiginde acik Codex pencerelerini kapatip yeniden ac.
- Bu arac tokenlari gostermek yerine yalnizca kisa `account_id` ozeti yazar.

## Source Of Truth

Codex hesaplari icin tek dosya yerine iki sorumluluk katmani vardir:

- `state/codex-accounts/`
  - execution truth
  - CODEX_HOME izolasyonu, aktif auth snapshotlari, runtime-secim verisi
  - primary readers: `server/account_manager.py`, `server/codex_orchestrator.py`
- `config/account_registry.json`
  - metadata and status truth
  - label, rol, operator notu, kota ozeti, gorunen durum
  - primary owner: `server/skills/account_monitor.py`

## Rules

1. Yeni bir `account_registry_v2.json`, `codex_registry.json` veya benzeri ucuncu kaynak ekleme.
2. Execution secimi `state/codex-accounts/` tarafindan yapilir.
3. UI veya operator raporlama `config/account_registry.json` tarafindan yapilir.
4. `/admin` ve `/codex-accounts` surface'leri bu iki kaynaktan ozet okur; yeni storage katmani olmaz.
5. Bu iki katman gerekiyorsa senkronize edilir, ama ayni seyin ikinci kopyasi uretilmez.
