# Codex MEGA Task — Swarm Production Hardening

> **Tek oturumda tamamlanacak iş paketi.**
> Bu prompt 5 hesaplı Codex swarm'ının "sürekli logout + 24/7 çalışmıyor" sorunlarını kapatır ve autonomous inter-agent kooperasyonunu devreye alır.
> Ekrem 17 gündür bu noktaya takılıyor; **yarım bırakma**.

---

## 0. Hard Constraints (İhlal = Otomatik Red)

1. **Worktree izolasyonu**: Tüm yeni kod ve düzenlemeler repo kökünde çalıştırılmaz. Önce `git worktree add ../jarvis-codex-swarm-hardening 008-swarm-skills-integration` ile izole worktree oluştur, işi orada yap.
2. **Push/Merge yasakları**: `main`, `master`, `release`, `prod` dallarına push, force-push veya merge YOK. Worktree branch'te commit kalacak; merge kararını Ekrem verecek.
3. **Credential dokunma yasağı**: `.env`, `auth.json` içindeki `access_token/refresh_token/id_token` değerlerini loga yazma, UI'a dökme, commit'leme. Redaction gerekiyorsa `account_manager._redact_secrets()` helper'ını kullan.
4. **.env yasağı**: `.env` ve `.env.*` dosyalarına yazma. Yeni config değerleri `config/` altında ayrı dosyada.
5. **Test yazmadan kod yok**: Her fonksiyon/endpoint için testi önce yaz, sonra implementasyonu yaz. Failed test suite ile iş bitmiş sayılmaz.
6. **Validation fail ⇒ durdur + rapor**: Herhangi bir test kırığı veya lint hatası varsa SEN TAMAMLANDI DİYE BİTİRME. Son mesajda `STATUS: FAILED` + kalan işler listesi döndür.
7. **Mevcut API bozma**: `/api/codex/*`, `/api/persona/*`, `/api/swarm-status` endpoint'lerinin payload/request şeması değişmez. Yeni alanlar additive olabilir.

---

## 1. Context Özeti (Tekrar anlatmıyorum, kod zaten içinde)

- **Repo**: `C:/Users/sergen/Desktop/jarvis-mission-control`, branch `008-swarm-skills-integration`
- **5 Codex hesabı**: `atlas, forge, nexus, shield, spark` — her biri `state/codex-accounts/<slot>/.codex/auth.json` içinde izole token ile
- **Mevcut altyapı (DOKUNMA, sadece genişlet)**:
  - `server/account_manager.py` — slot registry + auth yönetimi
  - `server/codex_orchestrator.py` — `_run_codex_task` subprocess spawn (line 567), CODEX_HOME env forwarding zaten doğru (line 578)
  - `server/codex_job_manager.py` — job queue
  - `server/codex_task_router.py` — role → slot routing
  - `server/codex_workspace.py` — worktree isolation
  - `server/multi_account_swarm.py` — `ParallelCodexDispatcher` async dispatch
- **Job queue dosyası**: `state/codex-accounts/<slot>/job_queue.json` (her slot'un kendi kuyruğu)
- **Bridge endpoint'leri**: `/api/codex/slots`, `/api/codex/jobs`, `/api/codex/queue`, `/api/codex/health`, `/api/codex/audit`, `/api/codex/result`, `/api/codex/status`

Kök sorun tanısı:
- **Neden logout**: `state/codex-accounts/atlas/.codex/auth.json` içinde `last_refresh: 2026-04-02`. Bugün 2026-04-18. Access token ~25 gün yaşar, refresh_token ile yenilenmeli ama otomatik refresh worker yok.
- **Neden 24/7 değil**: Job queue'dan sürekli task çeken background runner yok. Her dispatch manual trigger ile olur.
- **Neden agentlar konuşmuyor**: Inter-agent message bus yok. Her job bağımsız subprocess, sonuç sonra merge edilmiyor.

---

## 2. İş Paketi — 5 Faz

### FAZ A1 — Codex Auth Refresh Worker (P0, BLOCKING)

**Problem**: Her slot'un `auth.json` içindeki `access_token` 25 günde expire oluyor. Refresh olmazsa Codex CLI "please login" ekranına düşüyor → Ekrem manuel login yapmak zorunda kalıyor.

**Dosya**: `server/codex_auth_refresher.py` (YENİ)

**Davranış**:
- Her 6 saatte bir çalışan background worker
- 5 slot için sırayla:
  - `state/codex-accounts/<slot>/.codex/auth.json` oku
  - `tokens.access_token` JWT payload'ındaki `exp` claim'ini parse et
  - `exp` mevcut zaman + 48 saat < ise refresh yap
  - Refresh: OpenAI OAuth token endpoint'ine `grant_type=refresh_token` POST (endpoint: `https://auth.openai.com/oauth/token`, client_id `tokens.access_token` JWT'den `client_id` claim'i)
  - Response başarılı ise dosyayı atomik yaz (temp + rename), `last_refresh` alanını güncelle
  - Fail ise `account_manager.set_operator_status(slot, "pending_login")` işaretle, diğer slotlara devam et
- Log: `server/logs/codex_auth_refresher.log` (token değerleri redact edilecek, sadece slot adı + durum)

**Bridge entegrasyonu**:
- `server/bridge.py` startup'ında `codex_auth_refresher.start_background()` çağrısı (mevcut `research_scheduler` ve `instagram_scheduler` pattern'ini örnek al, line ~5700 civarı)
- Yeni endpoint: `GET /api/codex/auth-status` → `[{slot: "atlas", expires_in_hours: 72, last_refresh: "..."}, ...]`

**Test dosyası**: `tests/test_codex_auth_refresher.py`
- JWT exp parse doğrulama (sabit örnek token ile)
- `should_refresh(slot)` fonksiyonu: 48h içinde expire olacaksa True
- Atomic write doğrulaması: monkeypatch'li temp dizin
- Redaction testi: log çıktısında token görünmemeli
- HTTP refresh mock (requests_mock veya pure monkeypatch)

**Exit criteria**: `pytest tests/test_codex_auth_refresher.py -q` → all pass. `/api/codex/auth-status` GET çağrısı 5 slotu dönüyor.

---

### FAZ A2 — CODEX_HOME Subprocess Env Doğrulama

**Problem**: `codex_orchestrator.py:578` CODEX_HOME env'i doğru geçiyor görünse de, gerçek multi-slot paralel dispatch'te process tree'de doğrulanmadı. `multi_account_swarm.py` içindeki async dispatcher'ın `_call_codex_api` (line 326) metodu farklı bir path kullanıyor olabilir.

**Dosya**: `server/codex_orchestrator.py`, `server/multi_account_swarm.py` (edit)

**Yapılacak**:
1. `multi_account_swarm.py:_call_codex_api` içinde de `env={**os.environ, "CODEX_HOME": slot_codex_home}` ayarla. Eğer aşağıda `subprocess` veya `asyncio.create_subprocess_exec` çağrısı varsa env forward'ını doğrula.
2. Her spawn öncesi debug log: `logger.info(f"[codex-dispatch] slot={slot} codex_home={codex_home} cwd={cwd}")`
3. `codex_orchestrator._run_codex_task` içinde timeout'u 300s → 600s'ye çıkar (5 dakika büyük task'larda yetmiyor).
4. Subprocess timeout olursa `SIGTERM` → 10s bekle → `SIGKILL`. Bu davranışı `tests/test_codex_subprocess_timeout.py` içinde doğrula.

**Test dosyası**: `tests/test_codex_env_isolation.py`
- `_run_codex_task` monkeypatch'li `subprocess.Popen` çağrısında `env['CODEX_HOME']` beklenen slot path'ini içermeli
- 5 slot için paralel çağrıda 5 farklı CODEX_HOME değeri üretilmeli (dict-ile doğrula)

**Exit criteria**: Testler geçer. 5 slot aynı anda dispatch edildiğinde her subprocess kendi `.codex/auth.json`'ını okur (log ile kanıt).

---

### FAZ A3 — Autonomous 24/7 Runner

**Problem**: Job queue'da bekleyen task'lar var ama onları otomatik dispatch eden bir background loop yok.

**Dosya**: `server/codex_autonomous_runner.py` (YENİ)

**Davranış**:
- `AutonomousRunner` class, `start_background()` metodu
- Ana loop: her 10 saniyede bir:
  1. `job_manager.list_pending_jobs()` → pending job'ları al
  2. Her job için `task_router.route(job)` → hedef slot belirle
  3. `orchestrator.dispatch(job, slot)` → uygun slotu varsa gönder, yoksa bir sonraki iterasyonda tekrar dene
  4. `in_flight` job'ların durumunu kontrol et, done/failed → kuyruktan çıkar
- **Auto-approve rules** (Ekrem onay istemediği güvenli task'lar için):
  - `config/autonomous_allowlist.yml` (YENİ) — glob pattern ve task type bazlı allow list
  - Örnek: `read_file, list_files, grep, run_tests, check_format, docstring_generation` auto-approve
  - `git_commit, git_push, env_edit, deploy, .env, state/codex-accounts/*/auth.json` HARD BLOCK (onay zorunlu, Telegram bildirimi)
- Kill switch: `state/autonomous_runner.disabled` dosyası varsa loop duraklar (file-based kill switch)
- Loglama: her dispatch kararı `server/logs/autonomous_runner.jsonl` append-only

**Bridge entegrasyonu**:
- Startup'ta `codex_autonomous_runner.start_background()`
- Yeni endpointler:
  - `GET /api/autonomous/status` → `{enabled, in_flight, pending, last_tick, recent_decisions: [...]}`
  - `POST /api/autonomous/pause` → kill switch dosyası yarat
  - `POST /api/autonomous/resume` → kill switch dosyasını sil
- Telegram komutları (bridge içinde, yeni): `/otonom-durum`, `/otonom-durdur`, `/otonom-baslat`

**Test dosyası**: `tests/test_codex_autonomous_runner.py`
- Kill switch testi: disabled dosyası varsa tick yapmaz
- Allowlist pozitif: `read_file` task'ı auto-approve olur
- Allowlist negatif: `.env edit` task'ı BLOCK + audit log'a yazar
- 5 slot full-load: pending=10 job, 5 slot mevcut → 5 paralel dispatch edilir, 5 bekler

**Exit criteria**: Testler geçer. Bridge açılınca runner çalışmaya başlar, `/api/autonomous/status` doğru döner. 10 pending job ile 5 slot'ta paralel dispatch smoke test edilir.

---

### FAZ A4 — Inter-Agent Message Bus

**Problem**: 5 slot birbirinden habersiz çalışıyor. Atlas `refactor X dosyasını` yaptıysa, Nexus aynı dosyayı tekrar inceliyor olabilir. Collaboration yok.

**Dosya**:
- `server/codex_bus.py` (YENİ)
- `state/codex-accounts/_bus.jsonl` (runtime, gitignore'a ekle)

**Davranış**:
- `CodexBus` class:
  - `post(slot, event_type, payload)` → append-only JSONL yazar, kritik alanlar: `{ts, slot, event_type, job_id, payload}`
  - `read_since(after_ts, limit)` → cursor bazlı okuma
  - `read_for_slot(slot, limit)` → belirli slota yönlendirilmiş mesajlar (`payload.target_slot` varsa)
- Event types:
  - `job_started` — dispatch anında
  - `job_completed` — başarılı, payload: `{files_touched: [...], summary: "..."}`
  - `job_failed` — payload: `{error, retry_possible}`
  - `peer_ask` — bir slot başka slottan bilgi isterse (`payload.question`, `payload.target_slot`)
  - `peer_reply` — soruya cevap (`payload.in_reply_to_event_id`)
  - `lock_claim` / `lock_release` — aynı dosyaya paralel edit önleme (`payload.path`)
- **Bus'ın task context'e enjeksiyonu**: `orchestrator._run_codex_task` içinde prompt oluşturulurken, son 10 bus event'i `full_prompt`'un başına `# Peer Context` bölümü olarak eklenir. Böylece her Codex çağrısı diğerlerinin ne yaptığını bilir.

**Bridge entegrasyonu**:
- `GET /api/codex/bus?since=<ts>&limit=50` → event listesi
- `POST /api/codex/bus` → admin-only event post (debugging için)

**Test dosyası**: `tests/test_codex_bus.py`
- Append idempotent (aynı event 2 kez yazılınca de-dup)
- Concurrent write safety (threading + 10 paralel post)
- Peer context inject: `build_peer_context_block(slot, limit=5)` doğru formatlı string döner
- Lock claim/release mantığı

**Exit criteria**: Testler geçer. Bridge `/api/codex/bus` dönüyor. Orchestrator smoke: 2 slot paralel çalıştır, bus'a job_started + job_completed event'leri yazılmış olmalı, ikinci slot başlarken peer_context içerir.

---

### FAZ A5 — Octogent Fix (Önceki Oturumdan Yarım Kalan)

**Problem**:
1. `tests/test_external_framework_aliases.py::test_bridge_octogent_alias_returns_status` kırık: literal `external-repos/octogent` string bekliyor ama `build_octogent_health_snapshot()` absolute path döndürüyor.
2. `server/octogent_bridge.py:_resolve_octogent_command()` repo-local `octogent.cmd` wrapper'ını gerçek CLI sanıyor. `%APPDATA%\npm\octogent.cmd` yoksa `command-missing` dönmeli.

**Yapılacak**:
1. `tests/test_external_framework_aliases.py:136-140` → assertion'u `os.path.join("external-repos", "octogent")` veya `Path` tabanlı yap. Hem relative hem absolute path eşleşsin.
2. `server/octogent_bridge.py:_resolve_octogent_command()`:
   - Önce `%APPDATA%\npm\octogent.cmd` (Windows) veya `~/.npm-global/bin/octogent` (Linux) kontrol et
   - Yoksa `command-missing` status dön, repo-local `octogent.cmd` wrapper'ını HEALTHY sayma
   - Snapshot'a `command_source: "global" | "repo-wrapper" | "missing"` alanı ekle
3. `/octogent` komutlarını Sabrican persona skill'ine explicit bağla: `config/agents.yaml` Sabrican bölümünde `skills: [..., octogent_helper]` zaten var, bunun `server/skills/octogent_skill.py` handler'ına kablolandığını doğrula.

**Test dosyası**: mevcut `tests/test_octogent_bridge.py` genişlet + `tests/test_external_framework_aliases.py` fix.

**Exit criteria**: `pytest tests/test_octogent_bridge.py tests/test_external_framework_aliases.py -q` → 12+ passed, 0 failed.

---

## 3. Paralel Çalışma Stratejisi (Sana Özel)

Sende 5 Codex hesabı var. Bu mega task'ı tek hesapla bitirmek yerine paralelleştir:

| Slot | Görev |
|------|-------|
| `atlas` | FAZ A1 (auth refresher) — en kritik, ilk biten |
| `forge` | FAZ A2 (env doğrulama) + FAZ A5 (octogent fix) — küçük, hızlı |
| `nexus` | FAZ A3 (autonomous runner) — orta yoğunluk |
| `shield` | FAZ A4 (inter-agent bus) — bağımsız, başlayabilir |
| `spark` | Test yazımı + validation orchestrator — diğer 4'ün testlerini koordine eder, final `pytest tests/ -q` komple çalıştırır |

**Koordinasyon dosyası**: `state/swarm_hardening_status.md` — her slot başlama/bitirme ts'sini + dosya listesini append eder. Git commit'e gerek yok, runtime state.

---

## 4. Validation & Exit Criteria (TAMAMINI DOĞRULAMADAN TESLİM ETME)

1. **Syntax**: `python -m py_compile server/codex_auth_refresher.py server/codex_autonomous_runner.py server/codex_bus.py server/codex_orchestrator.py server/multi_account_swarm.py server/octogent_bridge.py server/bridge.py` → OK
2. **Lint**: `ruff check server/codex_auth_refresher.py server/codex_autonomous_runner.py server/codex_bus.py` → 0 error
3. **Tests**: `python -m pytest tests/test_codex_auth_refresher.py tests/test_codex_env_isolation.py tests/test_codex_autonomous_runner.py tests/test_codex_bus.py tests/test_octogent_bridge.py tests/test_external_framework_aliases.py -q` → all pass
4. **Mevcut test suite bozulmamalı**: `python -m pytest tests/ -q` → baseline kadar pass sayısı (regression yok)
5. **Smoke**: Bridge başlat, sırayla çağır:
   - `GET /api/codex/auth-status`
   - `GET /api/autonomous/status`
   - `GET /api/codex/bus?limit=5`
   - `GET /api/codex/slots`
   Hiçbiri 500 dönmez, şema valid.
6. **Redaction**: `grep -ri "eyJ" server/logs/` → boş (JWT token sızıntısı yok)
7. **Worktree temiz**: Final commit sadece worktree branch'te, `git log main..HEAD` değişiklik listesi.

---

## 5. Teslim Formatı

Son mesajında şunları ver:

```
STATUS: OK
BRANCH: 008-swarm-hardening-<slotname>  (worktree içinde)
COMMITS: <n>
FILES ADDED: [...]
FILES MODIFIED: [...]
TEST RESULTS:
  test_codex_auth_refresher: X passed
  test_codex_env_isolation: X passed
  test_codex_autonomous_runner: X passed
  test_codex_bus: X passed
  test_octogent_bridge: X passed
  test_external_framework_aliases: X passed
BASELINE REGRESSION: 0 tests broken
SMOKE: /api/codex/auth-status=200, /api/autonomous/status=200, /api/codex/bus=200
OPEN RISKS: [...]
NEXT STEPS FOR MERGE: [...]
```

Fail durumunda:

```
STATUS: FAILED
COMPLETED FAZES: [A1, A5]
FAILED FAZES: [A3]
FAILURE REASON: <short explanation>
REMAINING WORK: [...]
WORKTREE STATE: <branch, uncommitted files>
```

---

## 6. Hatırlatmalar

- Ekrem Türkçe konuşuyor, ama kod/commit mesajları İngilizce/sade Türkçe karışık olabilir — mevcut stile uy.
- `CLAUDE.md` ve `.claude/CLAUDE.md`'deki kurallara uy (özellikle "bridge.py additive", "persona gating", "redaction").
- Bu task kritik — yarım bırakma. Eğer bir faza takılırsan o faz'ı geçici olarak pending işaretle, diğerlerini tamamla, son raporda net belirt.
- **Auth refresher (FAZ A1) SIFIR NUMARA PRIORITY.** O bitmezse diğerleri anlamsız.

İyi çalışmalar kanka. Ekrem bunu 17 gündür bekliyor.
