# OpenClaw Update + Düşler + Optimizasyon — Codex Handoff

**Tarih:** 2026-04-24  
**Kaynak:** Claude Code (Opus 4.7) → Codex (gpt-5.4 xhigh)  
**Repo:** `C:\Users\sergen\Desktop\jarvis-mission-control`  
**Branch:** `008-swarm-skills-integration`  
**Owner persona:** Sabrican (operasyon/altyapı, OpenClaw canonical owner)

---

## 0 — Bu handoff neden var

Ekrem (kullanıcı) OpenClaw UI'ından bir Düşler (Dreams) paneli gösterdi:
> "Uyku sırasında bellek kopması. Güncelleme mevcut: v 2026.4.22 (şu anda v 2026.4.14 çalışıyor). Güncelleniyor…"

3 adımlı plan istedi:
1. OpenClaw'ı 2026.4.14 → 2026.4.22 güncelle
2. Düşler özelliğini anla + Jarvis'e entegre et
3. OpenClaw'ı daha iyi kullanma önerilerini somut kodla

Kullanıcının kotası dolmak üzere. Bu handoff'u Codex alıp ilerletecek.

---

## 1 — Bu session'da Claude'un yaptıkları (context)

### Biten iş: Persona/Subagent Capability Matrix → Policy Gate
Codex'in önceki turunda eklediği `evaluate_pc_action`, `evaluate_operator_action`, `pc_control_gateway` entegrasyonu üstüne **persona-aware gate** kondu. Matrix baseline policy'yi gevşetmez, üstüne deny/approval kuralı ekler.

**Dokunulan/eklenen dosyalar:**
- `config/persona_capabilities.yaml` (yeni) — 9 persona + default için 8 action class'lı matrix
- `server/security/persona_capabilities.py` (yeni) — YAML loader + `resolve_capability(persona_id, action_class)` + cache/reload
- `server/security/policy_gate.py` — `evaluate_shell_command`, `evaluate_openclaw_task`, `evaluate_operator_action`, `evaluate_pc_action` hepsi `persona_id` alıyor; `_apply_persona_matrix` helper baseline + matrix birleştiriyor; tek log noktasına indirildi
- `server/bridge.py` — `_chat_id_to_lane`, `_current_persona_id` helper'ları; `run_shell_full`/`run_command_safe`/`/kabul` artık persona-aware
- `server/openclaw_bridge.py` — `run_agent_task` varsayılan `persona_id="sabrican"` geçiyor
- `tests/test_persona_capabilities.py` (yeni, 6 test) + `tests/test_policy_gate.py` (6 yeni test eklendi)

**Doğrulama:** `python -m pytest tests/test_persona_capabilities.py tests/test_policy_gate.py tests/test_pc_control_gateway.py tests/test_openclaw_bridge.py -q` → **29 passed**. `py_compile` + `ruff check` temiz.

**Plan dosyası:** `C:\Users\sergen\.claude\plans\openclaw-2026-4-14-imperative-cherny.md`

### Yan iş: Sabri için içerik kaynağı
YouTube video (Mert Durmazer — Paperclip + Agentic, https://youtu.be/2srOFknmCnM) transkript edilip Sabri'ye 3 yerden bağlandı:
- `knowledge/sabri_mert_durmazer_ai_ajans.md`
- `server/bridge.py:get_relevant_knowledge` → reklam/ajans/sabri/mert durmazer/paperclip/agentic tetikleyicileri
- `state/agent_memory/sabri/memory.jsonl` → 7 high-signal girdi

OpenClaw ile doğrudan ilgisi yok, sadece tamamlandı bilgisi.

---

## 2 — OpenClaw mevcut durumu (kanıt)

### Kurulum
- Global npm: `%APPDATA%\npm\openclaw.cmd` → `C:\Users\sergen\AppData\Roaming\npm\node_modules\openclaw`
- Paket manager: `pnpm` (ama lockfile missing — update öncesi not)
- Config home: `C:\Users\sergen\.openclaw\`
- Gateway port: 18789 (dashboard http://127.0.0.1:18789/)
- Canvas: `~/.openclaw/canvas/index.html` var
- Memory: `~/.openclaw/memory/main.sqlite`
- **Uyarı:** `~/.openclaw/openclaw.json.clobbered.*` 5+ dosya birikmiş (2026-04-15, 2026-04-23) — config self-corruption sinyali

### Update dry-run çıktısı (Claude çalıştırdı)
```json
{
  "currentVersion": "2026.4.14",
  "targetVersion": "2026.4.22",
  "channel": "stable",
  "downgradeRisk": false,
  "actions": [
    "Run global package manager update with spec openclaw@latest",
    "Run plugin update sync after core update",
    "Refresh shell completion cache (if needed)",
    "Restart gateway service and run doctor checks"
  ]
}
```

### Düşler hakkında not
- `openclaw docs "düşler"` → `_No results._`
- `openclaw docs "dream"` → `_No results._`
- Yani 2026.4.14 CLI docs'ında Düşler yok. Muhtemelen **2026.4.22 ile geliyor** ya da **UI-side konsept** (memory + sessions + system/presence kompozisyonu).
- Description "uyku sırasında bellek kopması" → OpenClaw'ın idle/session-timeout davranışı olması muhtemel.

### Jarvis ↔ OpenClaw mevcut bağ
`server/openclaw_bridge.py`:
- `run_agent_task(task_desc, deliver=True, persona_id="sabrican")` → `openclaw.cmd agent --channel telegram ...`
- `build_openclaw_health_snapshot()` → gateway + auth durum
- `_load_openclaw_runtime_snapshot(profile)` → `openclaw.json` + `auth-profiles.json` okur
- Yeni policy_gate matrix zaten Sabrican için `openclaw.helper=allow`, `openclaw.deliver=require_approval` tanımlı

---

## 3 — Sıralı görev listesi (Codex'e)

### Görev 1 — OpenClaw update (blocking sonraki adımları)

**Niye:** 2026.4.22'e geçmeden Düşler'i inceleyemeyiz (CLI'da yok).

**Adımlar:**
```bash
# 1. Önce uncommitted changes varsa stash (isteğe bağlı, Codex karar versin)
git status -s | head -20

# 2. Güncelleme
"$APPDATA/npm/openclaw.cmd" update --yes --json 2>&1 | tee /tmp/openclaw-update.log

# 3. Yeni versiyon doğrula
"$APPDATA/npm/openclaw.cmd" --version

# 4. Gateway sağlık
"$APPDATA/npm/openclaw.cmd" doctor --json 2>&1 | tee /tmp/openclaw-doctor.log

# 5. Jarvis bridge smoke
python -c "from server.openclaw_bridge import build_openclaw_health_snapshot; import json; print(json.dumps(build_openclaw_health_snapshot(), indent=2))" 2>&1 | head -60
```

**Beklenen:** Versiyon `2026.4.22`, doctor'da red flag yok, bridge snapshot provider listesi boş gelmiyor.

**Başarısız olursa:**
- `openclaw.json` bozulduysa `~/.openclaw/openclaw.json.bak` veya `.bak.1..4` rollback adayı
- Gateway restart çakılıyorsa `openclaw gateway --force`
- Auth profili gittiyse `openclaw configure` elle koşulmalı → Ekrem'e pas

### Görev 2 — Düşler'i araştır

**Adımlar:**
```bash
"$APPDATA/npm/openclaw.cmd" --help | grep -iE 'dream|düş|idle|sleep' || echo "no hit in top-level"
"$APPDATA/npm/openclaw.cmd" memory --help 2>&1 | head -40
"$APPDATA/npm/openclaw.cmd" sessions --help 2>&1 | head -40
"$APPDATA/npm/openclaw.cmd" system --help 2>&1 | head -40
"$APPDATA/npm/openclaw.cmd" tasks --help 2>&1 | head -40
"$APPDATA/npm/openclaw.cmd" docs "düşler" 2>&1 | head -30
"$APPDATA/npm/openclaw.cmd" docs "dream" 2>&1 | head -30
"$APPDATA/npm/openclaw.cmd" docs "idle" 2>&1 | head -30
"$APPDATA/npm/openclaw.cmd" docs "sleep" 2>&1 | head -30
# Canvas UI source (Düşler muhtemelen UI-side)
rg -iC2 'düş|dream|sleep|idle' ~/.openclaw/canvas/ 2>&1 | head -80
# Gateway event feed (idle transition var mı?)
"$APPDATA/npm/openclaw.cmd" system events --limit 50 --json 2>&1 | head -80
```

**Çıktı:** `OPS/08_DUSLER_FEATURE_MAP.md` diye yeni dosya oluştur, bulguları özetle:
- Düşler = hangi CLI komutu/event'i?
- State nerede tutuluyor? (`memory.sqlite` mi, ayrı sqlite mi?)
- Trigger koşulu ne? (idle timeout, explicit komut, cron?)
- Persona/session-aware mı?

### Görev 3 — Düşler → Jarvis persona memory köprüsü

**Niye:** Ekrem "uyku sırasında bellek kopması" dedi — OpenClaw idle olduğunda aktif persona'nın memory'sine snapshot atarsak, bellek kopması artık "hibernate" olur.

**Uygulama:**
- Yeni skill: `server/skills/openclaw_dreams_skill.py`
- Fonksiyon 1: `capture_dream_snapshot(persona_id: str) -> dict` → `openclaw memory --json` çıktısını alır, `persona_manager.remember(persona_id, ...)` ile en son N girdiyi JSONL'e düşer
- Fonksiyon 2: `restore_from_dream(persona_id: str) -> int` → aktif persona için `recall()` yapıp OpenClaw session'a geri yükler (opsiyonel, Görev 2 bulgusuna göre)
- Bridge'e komut: `/dusler-snapshot` (Sabrican sahipli). Policy: `evaluate_operator_action("dreams_snapshot", ..., require_approval=False, persona_id=...)` — capability matrix'te yeri yok, default allow.
- Test: `tests/test_openclaw_dreams_skill.py` — `openclaw memory --json` mocklanmış bir fixture ile `capture_dream_snapshot("sabri")` → Sabri memory.jsonl'a beklenen satır yazıldı mı.

**Integration point:** `server/bridge.py` command router içinde `/dusler-snapshot` (veya `/dreams-save`) branch'i.

### Görev 4 — Clobbered config regression'ı araştır

**Niye:** `~/.openclaw/openclaw.json.clobbered.2026-04-23T16-*.json` aynı günde iki kere oluştu — race condition sinyali.

**Adımlar:**
```bash
ls -la ~/.openclaw/*.clobbered* ~/.openclaw/*.bak* | head -30
# Clobbered vs canonical fark
diff <(jq -S . ~/.openclaw/openclaw.json.clobbered.2026-04-23T16-34-12-386Z) <(jq -S . ~/.openclaw/openclaw.json) 2>&1 | head -60
# Update sırasında yeniden oluşuyor mu kontrol
ls -lat ~/.openclaw/*.clobbered* | head -5
```

**Çıktı:** `OPS/09_OPENCLAW_CONFIG_DRIFT.md` — farklar, olası root cause, remediation. Gerçek fix bu görevde opsiyonel (çünkü OpenClaw tarafı).

### Görev 5 — Persona color canvas publisher (opsiyonel, hologram + OpenClaw sync)

**Niye:** Hologram persona rengi gösteriyor ama OpenClaw kendi canvas'ı var — tek kaynak olsun.

**Uygulama:**
- `server/openclaw_bridge.py` içinde `publish_persona_color_to_canvas(persona_id: str) -> None`
- Persona değişince (`switch_persona` callback) çağrılır, `~/.openclaw/canvas/persona-state.json` dosyasına `{id, color, activated_at}` yazar
- Canvas HTML zaten dosya sistemi okuyorsa 3 saniyelik polling yeterli

### Görev 6 — Daily backup cron (basit)

**Uygulama:**
```bash
"$APPDATA/npm/openclaw.cmd" cron list --json
"$APPDATA/npm/openclaw.cmd" cron add --name "jarvis-daily-backup" --schedule "0 3 * * *" --command "backup create" --json
```

Eğer `openclaw cron add` syntax'ı farklıysa, `openclaw cron --help` okunup uyarlanacak.

### Görev 7 — Exec-approvals ↔ policy_gate merge (araştırma)

**Niye:** İki ayrı approval queue var şu an:
- Jarvis: `server/skills/approval_skill.py` + `create_approval_request`
- OpenClaw: `~/.openclaw/exec-approvals.json`

**Çıktı:** `OPS/10_APPROVAL_QUEUE_MERGE_PROPOSAL.md` — iki sistemin şemasını karşılaştır, tek source of truth için öneri yaz (kod yazma, öneri raporla — karar Ekrem'in).

---

## 4 — Kritik kurallar (Codex'e)

1. **`server/bridge.py`** — sadece additive değişiklik. Mevcut route'ları kırma. 
2. **`master_launcher.py`** — dokunma. Process lifecycle fragile.
3. **`.env`** — asla logla, UI'ya sızdırma.
4. **`config/agents.yaml`** — sadece `personas:` bloğu canonical, sadece okuma.
5. **Luna persona'sı** — canlı hedef / izinsiz saldırı isteklerini reddet (matrix zaten enforce ediyor, senin tarafta ek koruma gerekmez).
6. **Otonom loop** — yoksa sadece bu handoff'taki görevleri yap, git push yapma, main'e merge etme.
7. **Secret redaction** — OpenClaw `openclaw.json` içinde token/key varsa log satırlarında redact et.
8. **Destructive ops** — `git reset --hard`, `--force` push, `--no-verify` → ASLA sormadan.

---

## 5 — Doğrulama checklist (Codex bitince Claude/Ekrem bakacak)

Her görev için bitmeden önce:
```bash
python -m pytest tests/ -q 2>&1 | tail -20
python -m py_compile server/bridge.py server/openclaw_bridge.py server/skills/openclaw_dreams_skill.py server/security/policy_gate.py server/security/persona_capabilities.py
python -m ruff check server/security/ server/skills/ server/openclaw_bridge.py 2>&1 | tail -10
```

Smoke test (isteğe bağlı):
```bash
python -c "from server.persona_manager import switch_persona, recall; switch_persona('sabrican'); print(recall('sabrican', 'dream dusler', top_k=3))"
```

---

## 6 — İlk okunması gereken dosyalar

Codex session başında mutlaka şu dosyalar Read edilmeli (başka grep yapmadan):

1. `CLAUDE.md` — repo kök
2. `.claude/CLAUDE.md` — ek davranış kuralları
3. `server/openclaw_bridge.py` — mevcut OpenClaw entegrasyonu
4. `server/security/policy_gate.py` — yeni persona-aware gate (bu session'da yazıldı)
5. `server/security/persona_capabilities.py` — yeni loader (bu session'da yazıldı)
6. `config/persona_capabilities.yaml` — matrix (bu session'da yazıldı)
7. `server/persona_manager.py` — `remember/recall/get_active_persona/switch_persona`
8. `config/agents.yaml` satır 424-492 — Sabrican persona spec (openclaw helper + secondary_runtimes)
9. `openclaw.cmd`, `openclaw_web_only.cmd` — launcher'lar
10. `~/.openclaw/openclaw.json` — OpenClaw global config (okuma, secret redact)
11. `C:\Users\sergen\.claude\plans\openclaw-2026-4-14-imperative-cherny.md` — önceki plan

---

## 7 — Çıktı beklentisi

Codex bu handoff'u tamamladığında:
- `OPS/08_DUSLER_FEATURE_MAP.md` (Görev 2)
- `OPS/09_OPENCLAW_CONFIG_DRIFT.md` (Görev 4)
- `OPS/10_APPROVAL_QUEUE_MERGE_PROPOSAL.md` (Görev 7)
- `server/skills/openclaw_dreams_skill.py` + test (Görev 3)
- `server/bridge.py` içinde `/dusler-snapshot` komutu (Görev 3)
- (opsiyonel) `server/openclaw_bridge.py:publish_persona_color_to_canvas` (Görev 5)
- Tüm testler yeşil, `py_compile` + `ruff` temiz

Commit stratejisi: her görevi ayrı commit. Main'e merge yok.

Kanka bol şans.

---

## 8 — GÜNCELLEME (2026-04-24, 2. tur)

Codex'in 1. turunda `spawn EPERM` nedeniyle Görev 1 çakıldı (sandbox npm global dizinine yazamıyor). Claude update'i kendi Bash'inden tamamladı:

### Görev 1 — BİTTİ ✅
- `openclaw update --yes --json` → 2026.4.14 → **2026.4.22 (00bd2cf)**
- Plugin sync: `openclaw-web-search 0.2.2` up-to-date
- Ne var ne yok detay: `/tmp/openclaw-update.log` yok, ama update output exit 0 dönmüştü
- schtasks EPERM uyarısı çıktı (gateway service env refresh atlandı) — çözüm: gateway manuel stop + `openclaw gateway --force` ile yeniden başlatıldı
- Gateway 4.22 binary ile çalışıyor, webchat UI bağlandı
- Memory index **DIRTY** idi — `openclaw memory index --force` Claude tarafından tetiklendi (background, tamamlanıyor)

### Görev 2 — %80 BİTTİ ✅
Claude `OPS/08_DUSLER_FEATURE_MAP.md` yazdı. Düşler özeti:
- Üç uyku fazı: **light / REM / deep**
- Dosya sistemi: `~/.openclaw/workspace/memory/dreaming/{light,rem,deep}/YYYY-MM-DD.md`
- Ham corpus: `~/.openclaw/workspace/memory/.dreams/session-corpus/`
- Event stream: `~/.openclaw/workspace/memory/.dreams/events.jsonl`
- CLI: `openclaw memory {status,promote,promote-explain,rem-harness,rem-backfill,index,search}`
- Cron: `0 3 * * *` (daily 03:00), minScore=0.8, limit=10, recency half-life 14 gün, maxAgeDays=30
- Gateway RPC: `doctor.memory.dreamDiary`, `doctor.memory.status` (UI panelinin kaynağı)
- "Bellek kopması" root cause: bugün deep faz 0 aday promote etti — minScore eşiği yüksek + muhtemel Gemini 2.5-flash 400 error REM lasting-truth generation'ı çökertiyor
- DREAMS.md henüz yazılmamış (`rem-backfill` çalıştırılmamış)

Senin (Codex) eksik yapacağın: `rem-harness --json` ve `rem-backfill --json` smoke çıktılarını alıp OPS/08'e appendix ekle, gerçek REM JSON şemasını doğrula.

### Kalan görevler — SANA
Sıra artık: **Görev 3 → Görev 4 → Görev 6 → Görev 7 (rapor) → Görev 5 (opsiyonel)**.

Görev 3 için OPS/08 sana gerekli API ve regex şablonunu verdi. İlk iş:
1. `OPS/08_DUSLER_FEATURE_MAP.md` Read et
2. `server/skills/openclaw_dreams_skill.py` yaz (Görev 3 şablonuna göre)
3. `tests/test_openclaw_dreams_skill.py`
4. `server/bridge.py:handle_command` içinde `/dusler-snapshot`, `/dusler-rapor` branch'leri (additive)
5. Her şey yeşilse commit: `feat: dreams skill — Düşler/REM persona memory bridge`

Görev 4 (config drift) için: `diff` komutunu jq ile çalıştır, farkları kategorize et, clobbered ile canonical arasındaki şema farkları var mı bak. Fix kodu yazma, rapor yaz.

Görev 6 için: Sen CLI sandbox'a girdiğinde `openclaw cron add` izin hatası alabilirsin. Önce `openclaw cron list` ile kontrol et — zaten daily backup cron var mı? Yoksa `cron add` komutunun exact syntax'ını `--help` ile çıkar, Ekrem'e tek komutluk elle çalıştır talimatı hazırla (commit etme, OPS'de yazılı bırak).

### Sandbox notu (Codex için)
- `%APPDATA%\npm\` dışına yazmaya kalkma — EPERM yer.
- `~/.openclaw/` altına YAZABİLİRSİN (workspace-write sandbox içinde).
- Repo kökünde her yere yazabilirsin (git altındaki dosyalar dahil).
- Claude'un update'i zaten hallettiği için senin `openclaw update` çalıştırmana gerek yok.
