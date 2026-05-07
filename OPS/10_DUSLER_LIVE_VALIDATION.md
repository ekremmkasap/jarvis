# Dusler Live Validation Runbook

**Tarih:** 2026-04-28  
**Branch:** 008-swarm-skills-integration  
**OpenClaw versiyon:** 2026.4.25 (aa36ee6)  
**Dogrulayan:** Claude (Opus 4.7)

## Kapsam

`/dusler-snapshot` ve `/dusler-rapor` komutlari + `OpenClaw memory rem-backfill` icin canli end-to-end dogrulama. Persona capability matrix'inde `dreams.snapshot` ve `dreams.report` action class'lari yeni eklendi.

## Calistirilan komutlar ve sonuclari

### 1. Statik check + unit testler

```
python -m py_compile server/bridge.py server/openclaw_bridge.py \
    server/skills/openclaw_dreams_skill.py \
    server/security/persona_capabilities.py server/security/policy_gate.py
# exit 0

python -m pytest tests/test_persona_capabilities.py tests/test_policy_gate.py -q
# 21 passed in 0.32s
```

Yeni testler `tests/test_persona_capabilities.py`:
- `test_dreams_action_classes_known` — `KNOWN_ACTION_CLASSES` icine eklendigini dogrular
- `test_canonical_matrix_dreams_capabilities` — gercek `config/persona_capabilities.yaml` matrix'i kullanir, sabrican/jarvis allow, sabri/buse/luna/zeynep deny, seda dreams.snapshot deny + dreams.report require_approval, ghost persona require_approval

### 2. Policy gate dry-run

```python
evaluate_operator_action('dreams_snapshot', ..., persona_id='sabrican',
                        action_class='dreams.snapshot')
# allowed=True status='allowed' reason='operator-action-allowed'

evaluate_operator_action('dreams_snapshot', ..., persona_id='sabri',
                        action_class='dreams.snapshot')
# allowed=False status='denied' reason='persona-policy-denied'

evaluate_operator_action('dreams_snapshot', ..., persona_id='jarvis',
                        action_class='dreams.snapshot')
# allowed=True status='allowed' reason='operator-action-allowed' (canonical YAML jarvis blocugu)
```

### 3. Skill izolasyon testi

`capture_dream_snapshot` ve `parse_dream_report` `2026-04-27.md` REM raporu uzerinde:

- 6 tema parse edildi: `gateway`, `gmt`, `heartbeat.md`, `non-interactive`, `config-patch`, `config.patch`
- `lasting_truths`: 0 (raporda "No strong candidate truths surfaced.")
- Test persona `dreamssmoketest` icin `state/agent_memory/dreamssmoketest/memory.jsonl` 6 satir yazildi, sonra silindi

### 4. Bridge handler end-to-end

`server.bridge` import edildi (uzun ilk yukleme: SentenceTransformer + ReMe). Ardindan:

`bridge._handle_openclaw_dreams_report_command(chat_id, 'rem')` ciktisi (kesilmis):
```
Dusler Raporu (rem)
Dosya: C:\Users\sergen\.openclaw\workspace\memory\dreaming\rem\2026-04-27.md

# REM Sleep
### Reflections
- Theme: `gateway` kept surfacing across 12 memories.
  ...
```

`bridge._handle_openclaw_dreams_snapshot_command(chat_id)` ciktisi:
```
Dusler Snapshot
Persona: jarvis
Tema sayisi: 6
Kalici gercek sayisi: 0
Yazilan bellek girdisi: 6
Temalar: gateway, gmt, heartbeat.md, non-interactive, config-patch, config.patch
Rapor: C:\Users\sergen\.openclaw\workspace\memory\dreaming\rem\2026-04-27.md
```

`state/agent_memory/sabrican/memory.jsonl` son 6 satir `[dream-theme] X: N kez` formatinda yazildi.

> Not: bridge `_current_persona_id(chat_id)` test ortaminda `jarvis` dondurdu; gercek Telegram akisinda Sabrican persona'sina gecip ayni komutu calistirmak icin tek dogrulama daha gerek (Ekrem manuel test edebilir).

### 5. OpenClaw rem-backfill

```
"$APPDATA/npm/openclaw.cmd" memory rem-backfill \
    --path ~/.openclaw/workspace/memory/dreaming/rem/

REM Backfill (main)
workspace=~\.openclaw\workspace
sourcePath=~\.openclaw\workspace\memory\dreaming\rem
historicalFiles=4 writtenEntries=4 replacedEntries=0
dreamsPath=~\.openclaw\workspace\DREAMS.md
```

`~/.openclaw/workspace/DREAMS.md` (2693 byte) icinde 24, 25, 26, 27 Nisan icin gunluk REM ozetleri yazildi. UI Dusler panelindeki "uyku sirasinda bellek kopmasi" mesajinin yerini bu dream diary almali.

> Not: 28 Nisan REM raporu henuz uretilmedi; OpenClaw cron'u 03:00 local'de cikartmasi bekleniyor. Yarin tekrar `/dusler-snapshot` calistirinca bugune iliskin temalar Sabrican memory'sine gecer.

## Hala acik konular

- **Cron tetikleme:** OpenClaw'in iceride `0 3 * * *` cron'u dogrulanmadi (calistirma vakti gectikten sonra). `openclaw cron list` ile sonradan dogrulanabilir.
- **Gemini 400 sorunu (`OPS/08:174-178`):** REM lasting truth uretiminde gateway loglari hala 400 atiyor mu, izlenmesi gerekir; aktif bug Jarvis tarafinda degil OpenClaw config'inde.
- **Config drift (`OPS/09`):** `memory-core.dreaming.enabled` flag'inin ileri-geri toggle'lanmasi gozlendi 2026-04-23. Bugun rem-backfill basariyla calistigi icin aktif sorun degil ama OpenClaw tarafinda atomic write kilidi yapilmali.

## Degisen dosyalar

- `server/security/persona_capabilities.py` — `ACTION_DREAMS_SNAPSHOT`, `ACTION_DREAMS_REPORT` constant'lari + KNOWN_ACTION_CLASSES + DEFAULT_MATRIX guncellendi
- `config/persona_capabilities.yaml` — her persona blokuna `dreams.snapshot` + `dreams.report` eklendi; jarvis bloku ilk kez (sadece dreams.* override) acildi
- `tests/test_persona_capabilities.py` — 2 yeni test fonksiyonu + missing-yaml testine 2 assertion
- `OPS/10_DUSLER_LIVE_VALIDATION.md` — bu dosya
