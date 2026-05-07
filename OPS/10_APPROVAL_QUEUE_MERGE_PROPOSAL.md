# Approval Queue Merge Proposal

Tarih: 2026-04-24
Hazirlayan: Codex
Kapsam: Jarvis `approval_skill` ile OpenClaw `exec-approvals`

## Ozet

Iki sistem ayni seyi yapmiyor.

- Jarvis tarafi: insan-kararli is akis kuyrugu
- OpenClaw tarafi: host exec policy ve allowlist state

Bu nedenle "tek queue dosyasina merge" dogru hedef degil.
Dogru hedef: Jarvis insan-facing source of truth olsun, OpenClaw ise execution-policy sink olsun.

## Mevcut Jarvis Semasi

Dosya:
`server/agent_workspace/approval_state/approval_queue.json`

Alanlar:

- `id`
- `title`
- `summary`
- `source`
- `risk`
- `status` (`pending`, `approved`, `rejected`)
- `created_at`
- `decision_at`
- `decision_note`

Ek state dosyalari:

- `claude_resume.json`
- `autopilot.json`

Yetenekler:

- manuel onay/red
- autopilot ile risk bazli auto-approve
- insan okuyabilir queue semasi
- policy gate tarafindan dogrudan kullaniliyor

## Mevcut OpenClaw Semasi

Dosya:
`~/.openclaw/exec-approvals.json`

Mevcut icerik:

- `version`
- `socket.path`
- `socket.token`
- `defaults`
- `agents`

`openclaw approvals get` cikarisimi:

- Target: `local`
- Defaults: `none`
- Agents: `0`
- Allowlist: `0`
- Effective policy: `security=full`, `ask=off`

Bu dosya bir pending-request queue degil.
Bu daha cok "host hangi exec policy'yi ve hangi allowlist'i kabul ediyor" snapshot'i.

## Kritik Fark

Jarvis:

- olay bazli
- her istek icin satir aciyor
- insan karari ve audit notu tutuyor

OpenClaw:

- durum bazli
- per-agent / default policy tasiyor
- allowlist pattern'lari ve host merge mantigi tasiyor

Yani biri "ticket queue", digeri "policy document".

## Onerilen Mimari

Tek source of truth:

- Jarvis approval queue

Sekonder projection:

- OpenClaw exec policy / allowlist

Akis:

1. Riskli istek policy_gate'e gelir.
2. Jarvis `approval_skill` queue kaydi olusturur.
3. Onay verilirse gerekirse OpenClaw'a projection yapilir:
   - `openclaw exec-policy set ...`
   - veya `openclaw approvals allowlist add ...`
4. Is bittikten sonra projection geri alinabilir veya TTL ile temizlenebilir.

## Neden Bu Daha Dogru

1. Jarvis zaten `risk`, `source`, `decision_note`, `autopilot` semantigini biliyor.
2. OpenClaw approvals dosyasi su an pending item saklamiyor.
3. OpenClaw dosyasina queue semantiigi gommek host policy ile insan karari kavramlarini karistirir.
4. Geri donus ve audit daha net olur.

## Uygulanabilir Minumum Plan

1. Jarvis queue item'ina opsiyonel projection alanlari ekle:
   - `projection.target = openclaw`
   - `projection.kind = exec_policy|allowlist`
   - `projection.applied_at`
   - `projection.reverted_at`
2. Onaylandiginda OpenClaw projection helper cagir.
3. Red veya expiry durumunda projection geri al.
4. UI tarafinda "Jarvis queue / OpenClaw host policy" ayrimini net goster.

## Merge YapilMAMASI Gerekenler

- Tek JSON dosyasinda hem pending queue hem host socket token tutmak
- OpenClaw `exec-approvals.json` icine insan karar log'u yazmak
- Jarvis queue'yu OpenClaw allowlist dosyasindan turetmek

## Sonuc

"Iki approval queue" tanimi teknik olarak tam dogru degil.
Jarvis queue + OpenClaw policy ayrimi korunmali.

Oneri:

- Jarvis insan-facing approval source of truth
- OpenClaw host-policy projection target

Bu model audit, rollback, autopilot ve operator UX icin en temiz yol.
