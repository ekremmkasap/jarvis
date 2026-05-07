# OpenClaw Cron / Manual Backup Notes

Tarih: 2026-04-24
Hazirlayan: Codex

## Mevcut Durum

`openclaw cron list` sonucuna gore aktif 1 job var:

- `Memory Dreaming Promotion`
- Schedule: `cron 0 3 * * *`
- Status: `ok`

Yani 03:00 slotu zaten Düşler / memory-core tarafinda kullaniliyor.

## Neden Otomatik `cron add` Yerine Manual Block Hazirlandi

Handoff notuna gore Codex sandbox'inda `openclaw cron add` EPERM riski var.
Ayrica CLI help'te backup icin dogrudan belgelenmis cron payload ornegi yok.

Bu nedenle en guvenli operator yolu:

- mevcut cron state'i oldugu gibi birakmak
- backup'i simdilik exact manual command ile calistirmak

## Exact Manual Run Block

PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.openclaw\backups" | Out-Null
& "$env:APPDATA\npm\openclaw.cmd" backup create --output "$env:USERPROFILE\.openclaw\backups" --verify
Get-ChildItem "$env:USERPROFILE\.openclaw\backups" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 3 Name, LastWriteTime, Length
```

## Operator Notu

Eger Ekrem bunu scheduler ile disaridan baglamak isterse, en mantikli pencere `03:15` veya sonrasi.
Boylece `03:00` Memory Dreaming Promotion job'i ile cakisma riski azalir.

## Sonuc

Task 6 icin su anki sonuc:

- cron state okundu
- cron help okundu
- exact manual backup command block hazirlandi

OpenClaw tarafinda documented backup cron payload bulunmadigi icin sandbox icinde `cron add` zorlanmadi.
