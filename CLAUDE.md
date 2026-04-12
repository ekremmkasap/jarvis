# jarvis-mission-control Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-04-12

## Active Technologies

- Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui) + boto3 (AWS SDK), python-dotenv (hâlihazırda mevcut), requests (mevcut) (001-cloudmanagersystem-jarvis-entegreli)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

cd src; pytest; ruff check .

## Code Style

Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui): Follow standard conventions

## Recent Changes

- 001-cloudmanagersystem-jarvis-entegreli: Added Python 3.11 (skill + bridge), TypeScript / Next.js 14 (web-ui) + boto3 (AWS SDK), python-dotenv (hâlihazırda mevcut), requests (mevcut)

<!-- MANUAL ADDITIONS START -->
### AGENTS.md 9-Agent Canonical (Tab-3 Codex Sprint)
- Durum: IN PROGRESS (production hardening)
- Tamamlanan: refreshed `OPS/300_AGENTS_AUDIT.md`, `OPS/301_AGENTS_IMPLEMENTATION_PLAN.md`, `OPS/302_AGENTS_ROLLOUT_PLAN.md`; canonical base package; `planner`, `repo_analyst`, `developer`, `reviewer`, `debug`, `release`, `docs`, `voice_narrator`, `mission_control`; initial bridge `POST /agent` handler + canonical keyword routing; initial `OPS/308_HANDOFF.md`
- Slice A: `hey_jarvis.py` VoiceNarratorAgent hook dogrulandi; `pytest tests/test_hey_jarvis_live_mode.py -v --tb=short` gecti (`2 passed`)
- Slice B-D: `server/bridge.py` icine `_run_canonical_agent`, `_detect_agent_from_text`, wrapped `/agent` fallback, `GET /api/agents/health` ve Telegram canonical keyword hardening eklendi; `pytest tests/test_canonical_batch4.py tests/test_canonical_telegram.py -v --tb=short` gecti (`9 passed`); planner smoke `POST /agent` wrapper dogrulandi
- Slice E-F: `server/agents/canonical/base.py` icine `remember/recall/memory_summary` eklendi; run bazli `last_task` + `last_run` persistence aktif; `state/agent_memory/` canonical hale geldi; `OPS/308_HANDOFF.md` gercek davranisa gore yenilendi; `pytest tests/test_canonical_batch1.py tests/test_canonical_batch2.py tests/test_canonical_batch3.py tests/test_canonical_batch4.py tests/test_agent_memory.py -v --tb=short` gecti (`25 passed`)
- Kalan: full suite + final smoke + final production-ready kaydi
- Sonraki Adim: canonical suite'in tamamini ve final bridge smoke testini calistirip sprinti production-ready olarak kapat

### Multi-Codex Control Plane (Tab-2 Codex Sprint)
- Status: TAMAMLANDI
- Completed:
  - OPS audit and rollout artifacts (`OPS/200-204`)
  - Slice 1 complete: `server/account_manager.py` hardened as the single slot read surface
  - Slot/operator metadata matching now tolerates blank `execution_slot` by using slot-role heuristics
  - Added stricter recursive redaction for auth/token/secret-like keys before operator reads
  - Expanded `tests/test_account_manager.py` to cover heuristic matching and nested redaction
  - Slice 2 complete: `server/codex_task_router.py` aligned to canonical role affinity and slot keyword routing
  - Voice/video dispatch now resolves to `spark`; overflow/reserve keywords now resolve to `nexus`
  - Expanded `tests/test_codex_task_router.py` and updated route expectations in `tests/test_codex_management.py`
  - Slice 3 complete: `server/codex_job_manager.py` validated as the canonical JSONL queue owner
  - Flat bridge/orchestrator payloads now normalize into canonical `task={description,type,payload}` records
  - Expanded `tests/test_codex_job_manager.py` to cover flat payload normalization and filtered job listing
  - Slice 4 complete: `server/codex_orchestrator.py` now owns queue-first dispatch, persisted cooldowns, slot failover, and dispatch audit logging
  - Added `state/codex_cooldowns.json` semantics plus audit records in `server/logs/codex_dispatch_audit.jsonl`
  - Expanded quota/account hooks so availability checks now include dispatcher cooldown state
  - Added `tests/test_codex_orchestrator.py`
  - Slice 5 complete: `server/bridge.py` now exposes additive `/api/codex/slots`, `/jobs`, `/queue`, `/dispatch`, `/control`, `/health`, and `/audit` endpoints
  - Operator payload builders now redact slot/job/audit responses through `account_manager`
  - Expanded `tests/test_codex_management.py` to cover the new bridge control-plane payloads and control actions
  - Slice 6 complete: `apps/web-ui/src/app/codex-accounts/page.tsx` replaced with a dedicated live operator surface
  - UI now polls slot/queue/health/audit surfaces and exposes dispatch, retry, drain, pause, disable, and clear-cooldown controls
  - Frontend validation passed with `apps/web-ui/node_modules/.bin/tsc.cmd --noEmit`
  - Slice 7 complete: `server/codex_workspace.py` now creates and reuses canonical per-slot git worktrees under `worktrees/`
  - Added top-level helpers `ensure_worktree`, `get_worktree_path`, `cleanup_worktree`, `list_worktrees` and wired `worktrees/` into `.gitignore`
  - Added `tests/test_codex_workspace.py`
  - Slice 8 complete: Telegram `/codex-*` operational commands wired in `server/bridge.py`
  - Added `/codex-durum`, `/codex-kuyruk`, `/codex-saglik`, `/codex-baslat`, `/codex-durdur`, `/codex-cooldown-temizle`
  - Added `_handle_codex_slots_command`, `_handle_codex_stop_command`, and cooldown-clear routing backed by the operator control plane
  - Expanded `tests/test_codex_management.py` with `test_codex_telegram_commands`
  - Validation passed with `python -m pytest tests/test_codex_management.py -v --tb=short` (`12 passed`)
  - Slice 9 complete: `OPS/209_MULTI_CODEX_HANDOFF.md` added with slot architecture, Telegram commands, API endpoint table, and skill extension notes
  - Final validation passed with `python -m pytest tests/test_account_manager.py tests/test_codex_task_router.py tests/test_codex_job_manager.py tests/test_codex_orchestrator.py tests/test_codex_management.py tests/test_codex_workspace.py -v --tb=short` (`47 passed`)
- Remaining:
  - Kod tarafinda kalan is yok
- Next Step:
  - Canli bridge process'ini restart edip yeni Telegram `/codex-*` komutlarini runtime'da yukle

### Dijital Ajan Dunyasi V2 — 3 Katmanli Mimari (2026-04-13)

Vizyon: Ekrem "Buse ile konus" dediginde Jarvis Buseyi aktif eder, animasyonlu hologram
gecisi olur, Buse kendi sesiyle karsilar. Tek bridge / tek TTS / tek hologram — 7 lazy persona.
Persona = state + profil. Execution = Codex slotu. Bunlar ayri katmanlar.

---

KATMAN 1 — PERSONA PLANE (kimlik + durum)
  state/active_agent.json       — aktif persona
  config/agents.yaml            — 7 persona profili (isim, rol, renk, ses, skills)
  state/agent_world.json        — son aktivasyon + gorev gecmisi
  server/agents/clones/[ajan]/memory/ — per-agent hafiza

  Personalar (lazy, surekli process degil):
    Seda   = kod/debug/PR     renk=#00ff88  ses=AhmetNeural
    Mert   = arastirma/rakip  renk=#ffdd00  ses=AhmetNeural
    Buse   = pazarlama/landing renk=#ff69b4 ses=EmelNeural
    Eren   = veri/dashboard   renk=#ff8c00  ses=AhmetNeural
    Luna   = guvenlik/audit   renk=#9b59b6  ses=EmelNeural
    Sabrican = deploy/ops     renk=#95a5a6  ses=AhmetNeural
    Sabri  = wildcard/yaratici renk=#e74c3c ses=AhmetNeural

---

KATMAN 2 — RUNTIME PLANE (tek calisan sistem)
  server/bridge.py              — tek komut router (backward-safe)
  hey_jarvis.py                 — tek TTS/STT (persona sesini yukler)
  apps/desktop-hologram/        — tek hologram (renk/animasyon persona'ya gore degisir)

  Persona switching akisi:
    "Buse ile konus" -> bridge.py -> state/active_agent.json = "buse"
    -> hey_jarvis.py EmelNeural yukler -> "Baglaniyor: Buse..."
    -> hologram rengi #ff69b4 -> Buse greeting soyler

---

KATMAN 3 — EXECUTION PLANE (Codex slot binding)
  config/persona_execution_map.json — persona -> Codex slotu
    Seda->forge, Mert->nexus, Buse->spark
    Eren->shield, Luna->shield, Sabrican->nexus, Sabri->atlas
  server/codex_orchestrator.py  — slot scheduler (Tab-2 Codex urunu)

---

FAZ SIRASI (BLOKERLARA GORE):

  Faz 0 — Bridge Recovery (BLOKER — hicbir sey Faz 0 olmadan calismiyor)
    bridge.py cevrimici olmali, /health 200 donmeli
    hey_jarvis.py bridge ile konusabilmeli

  Faz 1 — Persona Switching + Greeting
    "X ile konus" -> active_agent.json guncelleme
    Greeing TTS per persona
    Tetikleyiciler: "Buse ile konus" / "Buseyi cagir" / "Sedaya sor"

  Faz 2 — Hologram Animated Transitions
    renderer.js persona rengine gore glow/fade
    state/swarm_speaking_state.json polling mevcut

  Faz 3 — Per-Persona Skill Routing
    skill_registry.py + persona context inject
    "Kim aktif?" -> aktif ajan ve yetenekleri

  Faz 4 — Codex Account Binding
    persona_execution_map.json aktif
    codex_orchestrator.py slot secimi

  Faz 5 — Cross-Agent Memory + World State
    agent_world.json: son aktivasyon + gorev gecmisi
    Ajanlar arasi mesaj/hafiza paylasimi

---

TASARIM KURALLARI:
  - Ikinci ana hologram yok — tek hologram persona rengine boyaniyor
  - Persona state != account state (ayri katmanlar)
  - Personalar lazy: "Buse" aktif edilene kadar process yok
  - Faz 0 bitmeden Faz 1'e gecilmez

Durum: PLANLANDII — Faz 0 (bridge recovery) bloker
Oncelik: Cok Yuksek — Codex Tab-2 ile paralel yapilabilir

### CloudManagerSystem + Skill Registry (Tab-3 Codex)
- Durum: TAMAMLANDI
- EC2/S3/Cost: `server/skills/aws_ec2_skill.py`, `server/skills/aws_s3_skill.py`, `server/skills/aws_cost_skill.py`
- Cloud UI: `/cloud` route at `apps/web-ui/src/app/cloud/page.tsx`
- Telegram: `/cloud-durum`, `/cloud-ec2-liste`, `/cloud-maliyet`, `/yardim`
- Registry: `server/skill_registry.py` - 12 commands migrated
- Tests: `pytest` combined suite `19 passed`
- Handoff: `OPS/408_CLOUDMANAGER_HANDOFF.md`

### CloudManagerSystem + Skill Registry (Tab-4 Codex Faz2)
- Durum: IN PROGRESS
- Slice A: `server/skills/aws_ec2_skill.py` icine `get_instance_metrics()` ve `reboot_instance()` eklendi
- Tests: `python -m pytest tests/test_aws_ec2_skill.py -v --tb=short` (`7 passed`)
- Slice B: `server/skills/aws_s3_skill.py` icine `generate_presigned_url()` ve `get_object_metadata()` eklendi
- Tests: `python -m pytest tests/test_aws_s3_skill.py -v --tb=short` (`8 passed`)
- Slice C: `server/skills/aws_cost_skill.py` icine `check_cost_alerts()` ve `get_cost_summary_text()` eklendi
- Tests: `python -m pytest tests/test_aws_cost_skill.py -v --tb=short` (`8 passed`)
- Sonraki Adim: SkillRegistry icine 5 yeni cloud komutu
<!-- MANUAL ADDITIONS END -->
