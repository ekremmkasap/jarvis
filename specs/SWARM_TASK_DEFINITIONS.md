# Swarm Task Definitions

Bu dokuman `/swarm` bridge entegrasyonu icin cekirdek gorev kontratini tanimlar.
Bridge entegrasyonu ayrica yapilacak; bu dosya sadece `SwarmCoordinator` tarafinin
bekledigi slot, state ve rapor semasini sabitler.

## State Machine

Tek bir swarm hedefi su sirayla ilerler:

1. `NEW`: Hedef olusturuldu, henuz task atanmadı.
2. `RUNNING`: En az bir task logical slot'a atandi.
3. `COLLECTING`: Slot ciktilari coordinator tarafindan toplanıyor.
4. `REPORTING`: Toplanan ciktilar tek rapora donusturuluyor.
5. `DONE`: Nihai rapor hazir.

Gecisler sadece ileri yonludur:

```text
NEW -> RUNNING -> COLLECTING -> REPORTING -> DONE
```

## Logical Slots

`SwarmCoordinator` bes logical slot kullanir. `spark_buse` ve `spark_eren`
ayni gercek Codex slot ailesine (`spark`) baglanir ama farkli persona ve
gorev hattı olarak ayrilir.

| Slot ID | Execution Slot | Persona | Role | Sorumluluk |
| --- | --- | --- | --- | --- |
| `forge` | `forge` | Seda | `code_debug` | Batch scraper, backend fix, smoke verification |
| `nexus` | `nexus` | Sabrican | `ops_automation` | Swarm coordination, automation, runbook hardening |
| `spark_buse` | `spark` | Buse | `content_analysis` | Reel analizi, creator positioning, CTA pattern |
| `spark_eren` | `spark` | Eren | `data_analysis` | Engagement scoring, KPI extraction, benchmark |
| `atlas` | `atlas` | Sabri | `strategy` | CEO synthesis, priority, 48h buildout strategy |

## Python Contract

```python
from server.orchestrator.swarm_coordinator import SwarmCoordinator

coordinator = SwarmCoordinator("Build Jarvis Instagram account in 48 hours")

task_a = coordinator.assign_task("Run batch scraper smoke", role="code")
task_b = coordinator.assign_task("Analyze Reel 021-030", role="content")

coordinator.collect_results({
    task_a.task_id: {"success": True, "output": {"profiles": 5}},
    task_b.task_id: {"success": True, "output": "Top pattern: comment CTA"},
})

report = coordinator.aggregate_reports()
```

## assign_task

Required:

- `description`: Operator-facing task text.

Optional routing hints:

- `slot_id`: Exact logical slot (`forge`, `nexus`, `spark_buse`, `spark_eren`, `atlas`).
- `role`: Role affinity (`code`, `ops`, `content`, `data`, `strategy`, etc.).
- `persona`: Persona affinity (`seda`, `sabrican`, `buse`, `eren`, `sabri`).
- `metadata`: JSON-safe extra context.

Rules:

- First assignment moves state from `NEW` to `RUNNING`.
- Each logical slot has capacity `1`.
- Assignment after `COLLECTING`, `REPORTING`, or `DONE` is rejected.

## collect_results

Accepted result formats:

```python
{
  "task_001": {"success": True, "output": "...", "metrics": {"views": 1000}},
  "task_002": {"status": "error", "error": "rate limited"}
}
```

or iterable `SwarmResult` objects.

Rules:

- First collection moves state from `RUNNING` to `COLLECTING`.
- Unknown task IDs are rejected.
- `success=False`, `status=error`, `status=failed`, or `status=timeout` maps to `FAILED`.
- Other result values map to `COMPLETED`.

## aggregate_reports

`aggregate_reports()` moves through `REPORTING` and finishes at `DONE`.

Returned report shape:

```json
{
  "goal_id": "swarm_xxx",
  "goal": "Build Jarvis Instagram account in 48 hours",
  "state": "DONE",
  "summary": {
    "total_tasks": 5,
    "successful": 4,
    "failed": 1,
    "pending": 0,
    "slots": 5
  },
  "slot_reports": [],
  "outputs": {},
  "errors": {},
  "narrative": "Swarm tamamlandi: 4 basarili, 1 hatali, 0 bekleyen.",
  "state_history": []
}
```

## Bridge Integration Notes

Parent bridge entegrasyonu `/swarm <goal>` komutunda su sirayi izlemeli:

1. `SwarmCoordinator(goal)` olustur.
2. Goal'a gore 1-5 task uret.
3. Her task icin `assign_task(...)` cagir.
4. Gercek Codex runner veya job manager ciktilarini bekle.
5. Ciktilari `collect_results(...)` ile ver.
6. `aggregate_reports()` sonucunu operator'a Turkce ozetle.

Bu implementasyon bridge'e dokunmaz ve gercek Codex process'i baslatmaz.
