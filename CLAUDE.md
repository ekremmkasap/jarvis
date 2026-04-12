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
- Durum: TAMAMLANDI
- Tamamlanan: refreshed `OPS/300_AGENTS_AUDIT.md`, `OPS/301_AGENTS_IMPLEMENTATION_PLAN.md`, `OPS/302_AGENTS_ROLLOUT_PLAN.md`; canonical base package; `planner`, `repo_analyst`, `developer`, `reviewer`, `debug`, `release`, `docs`, `voice_narrator`, `mission_control`; bridge `POST /agent` handler + canonical keyword routing; `hey_jarvis.py` narrator hook; `OPS/308_HANDOFF.md`; validation passed with `pytest tests/test_canonical_batch1.py tests/test_canonical_batch2.py tests/test_canonical_batch3.py tests/test_canonical_batch4.py tests/test_hey_jarvis_live_mode.py` (`22 passed`)
- Kalan: Kod tarafinda yok; operasyonel olarak `127.0.0.1:8081` uzerindeki mevcut bridge process'i restart edilmeden canli `POST /agent` endpoint'i gorunmeyecek
- Sonraki Adim: Calisan bridge process'ini restart edip canli `POST /agent` smoke testini tekrar et

### Multi-Codex Control Plane (Tab-2 Codex Sprint)
- Status: In Progress
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
- Remaining:
  - Slice 5-8 bridge/API/UI/worktree/Telegram integration
  - Slice 9 handoff and final validation
- Next Step:
  - Extend `server/bridge.py` with additive `/api/codex/*` operator endpoints on top of the new dispatcher and audit surfaces

### Dijital Ajan Dunyasi — SIMS Vizyon Plani (2026-04-13)

Vizyon: Jarvis altinda calisiran 7 ajanin (Seda/Mert/Buse/Eren/Luna/Sabrican/Sabri) her biri
kendi kimligi, sesi, yetenekleri ve animasyonuyla tam bir dijital dunya olusturur.
Ekrem "Buse ile konus" dediginde Jarvis Buseyi cagirir, animasyonlu gecis olur,
Buse "Merhaba Ekrem, ben Buse, nasil yardimci olabilirim?" der.

Temel Bilesenleri:

1. AGENT SWITCHING (bridge.py)
   - "X ile konus" komutu -> bridge.py agent switcher tetiklenir
   - Aktif ajan state: state/active_agent.json
   - Gecis TTS: "Baglanıyor: Buse..." -> selamlama

2. AGENT GREETING
   - Her ajan ilk aktivasyonda kendi greeting metnini soyler
   - "Merhaba [kullanici], ben [isim]. [rol]. Nasil yardimci olabilirim?"

3. ANIMATED TRANSITIONS (hologram)
   - Ajan gecislerinde fade/glow animasyonu — renderer.js + styles.css
   - Her ajanin rengi: Seda=#00ff88 Mert=#ffdd00 Buse=#ff69b4 Eren=#ff8c00
     Luna=#9b59b6 Sabrican=#95a5a6 Sabri=#e74c3c
   - state/swarm_speaking_state.json polling mevcuttur

4. PER-AGENT SKILLS
   - Seda: kod, debug, PR, git
   - Mert: web arastirma, rakip analizi
   - Buse: pazarlama, landing page, musteri iletisimi
   - Eren: veri analizi, dashboard, KPI
   - Luna: guvenlik tarama, risk, audit
   - Sabrican: deploy, server ops
   - Sabri: wildcard, yaratici fikirler

5. PER-AGENT VOICES (edge_tts)
   - Her ajan farkli ses ve hiz -> personality_voice_config.json
   - Mevcut: EmelNeural / AhmetNeural tr-TR

6. CODEX ACCOUNT BINDING
   - Seda -> forge, Mert -> nexus, Buse -> spark
   - Eren -> shield, Luna -> shield, Sabrican -> nexus, Sabri -> atlas

7. AGENT WORLD STATE
   - state/agent_world.json: tum ajanlar son aktivasyon + gorev gecmisi
   - server/agents/clones/[ajan]/memory/ — her ajanin hafizasi

Uygulama Sirasi:
  Faz 1: Agent switching + greeting TTS (bridge.py + hey_jarvis.py)
  Faz 2: Hologram animated transitions (renderer.js + styles.css)
  Faz 3: Per-agent skill routing (skill_registry.py + agent context)
  Faz 4: Codex account binding per agent
  Faz 5: Agent world state + cross-agent memory

Tetikleyici komutlar:
  "Buse ile konus" / "Buseyi cagir" / "Buseye gec"
  "Mert arastirsin" / "Sedaya sor"
  "Herkesi topla" -> swarm modu
  "Kim aktif?" -> aktif ajan durumu

Durum: PLANLANDII — implementasyon bekliyor
Oncelik: Yuksek — Faz 1 Anti veya Codex Tab-2 ile yapilabilir

### CloudManagerSystem + Skill Registry (Tab-3 Codex)
- Durum: PART A TAMAMLANDI
- Completed:
  - Slice A1 complete: `server/skills/aws_common.py` and `server/skills/aws_ec2_skill.py`
  - Added `tests/test_aws_ec2_skill.py`
  - Validation passed with `pytest tests/test_aws_ec2_skill.py` (`4 passed`)
  - Slice A2 complete: `server/skills/aws_s3_skill.py`
  - Added `tests/test_aws_s3_skill.py`
  - Validation passed with `pytest tests/test_aws_s3_skill.py` (`5 passed`)
  - Slice A3 complete: `server/skills/aws_cost_skill.py`
  - Added `tests/test_aws_cost_skill.py`
  - Validation passed with `pytest tests/test_aws_cost_skill.py` (`5 passed`)
  - Slice A4 complete: `/cloud-*` Telegram commands in `server/bridge.py`
  - Added `tests/test_cloud_bridge_commands.py`
  - Validation passed with `pytest tests/test_cloud_bridge_commands.py` (`2 passed`) and `python -m py_compile server/bridge.py`
  - Slice A5 complete: `/api/cloud/*` endpoints in `server/bridge.py`
  - Added `apps/web-ui/src/app/cloud/page.tsx`
  - Added `tests/test_cloud_http_surface.py`
  - Validation passed with `pytest tests/test_cloud_http_surface.py` (`2 passed`), `python -m py_compile server/bridge.py`, `cmd /c npx tsc --noEmit`
  - Slice A6 complete: Part A integration validation
  - Validation passed with `pytest tests/test_aws_ec2_skill.py tests/test_aws_s3_skill.py tests/test_aws_cost_skill.py` (`14 passed`)
  - Smoke passed with standalone imports from `server/skills`
  - Slice B1 complete: `server/skill_registry.py`
  - Added `tests/test_skill_registry.py`
  - Validation passed with `pytest tests/test_skill_registry.py` (`5 passed`)
  - Slice B2 complete: `/cloud-*` commands migrated to `SkillRegistry`
  - Added `server/cloud_command_handlers.py` and `server/skills/registry_entries/cloud_entries.py`
  - Validation passed with `pytest tests/test_skill_registry.py tests/test_cloud_bridge_commands.py` (`7 passed`)
  - Slice B3 complete: `/yardim` registered via `SkillRegistry`
  - Added `server/help_command_handlers.py` and `server/skills/registry_entries/help_entries.py`
  - Validation passed with `pytest tests/test_skill_registry.py tests/test_cloud_bridge_commands.py` (`8 passed`)
- Remaining:
  - Slice B4-B5 (incremental command migration, Part B integration)
  - Final handoff doc: `OPS/408_CLOUDMANAGER_HANDOFF.md`
- Next Step:
  - Slice B4: migrate 5 more high-traffic commands to `SkillRegistry`
<!-- MANUAL ADDITIONS END -->
