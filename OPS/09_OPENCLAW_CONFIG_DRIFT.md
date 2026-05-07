# OpenClaw Config Drift Report

Tarih: 2026-04-24
Hazirlayan: Codex
Kapsam: `~/.openclaw/openclaw.json`, `*.clobbered*`, `*.bak*`

## Ozet

Bugun itibariyla mevcut canonical dosya ile en son iki `clobbered` kopya byte-for-byte ayni.
Yani aktif config su anda bozuk degil.

Asil sinyal, 2026-04-23 boyunca ayni saniye icinde ikili `clobbered` dosyalarinin tekrar tekrar uretilmesi:

- `2026-04-23T16-15-40` cift dosya
- `2026-04-23T16-34-12` cift dosya
- `2026-04-23T16-40-05` cift dosya
- `2026-04-23T16-58-58` cift dosya
- `2026-04-23T21-40-37` cift dosya

Her cift dosya kendi icinde ayni SHA-256 ozetine sahip. Bu, "iki farkli writer ayni anda farkli state yaziyor"dan cok "tek save akisi duplicate clobber artifact birakiyor" ihtimalini guclendiriyor.

## Kanit

- Toplam `clobbered` dosyasi: 13
- En yeni `clobbered`:
  `openclaw.json.clobbered.2026-04-23T21-40-37-222Z`
  `openclaw.json.clobbered.2026-04-23T21-40-37-254Z`
- Bu iki dosya ile canonical `openclaw.json` ayni hash'te:
  `beb30d026e9d`

## Gozlenen Schema Drift

Canonical ile en yeni `clobbered` arasinda fark yok.

Canonical ile `openclaw.json.bak` arasinda yalnizca 2 fark var:

1. `meta.lastTouchedAt`
   Canonical daha yeni bir timestamp tasiyor.
2. `plugins.entries.memory-core.config.dreaming.enabled`
   - Canonical: `true`
   - `openclaw.json.bak`: `false`

Eski `clobbered` timeline'i de bunu destekliyor:

- `2026-04-23T16-15-40` hash grubu:
  `memory-core` plugin girdisi yok
- `2026-04-23T16-34-12` hash grubu:
  `memory-core.dreaming.enabled = true`
- `2026-04-23T16-40-05` hash grubu:
  `memory-core.dreaming.enabled = false`
- `2026-04-23T16-51-39` hash grubu:
  `memory-core.dreaming.enabled = true`
- `2026-04-23T16-58-58` hash grubu:
  `memory-core.dreaming.enabled = false`
- `2026-04-23T21-40-37` hash grubu:
  `memory-core.dreaming.enabled = true`

## Yorum

Bu pattern "genel config corruption"dan cok "ayni alanin birden fazla save path tarafindan ileri-geri toggle edilmesi" goruntusu veriyor.

En guclu adaylar:

1. `memory-core` plugin activation/save akisi
   `dreaming.enabled` alani bir path'te aciliyor, baska bir path'te eski state geri yaziliyor.
2. Gateway restart veya plugin sync sonrasi stale config write
   Ozellikle ayni timestamp'e cok yakin ikili dosyalar bunu destekliyor.
3. Legacy backup/restore veya hot-reload write yarisi
   `openclaw.json.bak` ile `clobbered` timeline'i ayni feature flag uzerinde donuyor.

## Etki

- Auth profile drift gozlenmedi.
- Provider listesi drift gozlenmedi.
- Plugin allow-list drift gozlenmedi.
- Secret alanlarda bu incelemede yapisal churn yakalanmadi.
- Risk daha cok `memory-core` davranisinin acik/kapali kalmasi ve UI/doctor durumunun tutarsizlasmasi.

## Oneri

1. `memory-core` dreaming ayarini tek writer'a indir.
2. Config save sirasinda atomic write + single-flight kilidi kontrol et.
3. `clobbered` olustugunda sadece dosya atmak yerine sebep log'u da yaz:
   writer, source command, PID, previous hash, next hash.
4. `doctor --fix` veya benzeri bir path varsa config storage normalizasyonu icin sonradan denenebilir.
5. Kisa vadede rollback referansi olarak en guvenli aday:
   mevcut canonical `openclaw.json`
   Cunku en yeni clobbered ile birebir ayni ve `dreaming.enabled = true`.

## Sonuc

Bugunku durum bir "aktif bozuk config" degil.
Sorun, 2026-04-23 gunu boyunca tekrarlayan duplicate clobber artifact ve `memory-core.dreaming.enabled` alaninin gidip gelmesi.
Kod fix'i OpenClaw tarafinda yapilmali; Jarvis repo tarafinda sadece gozlem ve raporlama onerilir.
