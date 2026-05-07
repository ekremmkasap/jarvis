---
tags: [personas, architecture, integration, roadmap]
date: 2026-04-17
---

# 7 Persona × AI Tool Matrix — Sabrican Pattern Genişletme

## Amaç

Her persona'yı Sabrican gibi **secondary runtime layer** ile zenginleştirmek. Sabrican'ın OpenClaw entegrasyonu template. Her persona kendi domain'ine özgü AI tool'lar + dispatch fonksiyonları alacak.

GLM-5.1 (Z.ai) bağlantısı 2-3 güne geldiğinde, kod-ağırlıklı personalar (Seda, Luna) otomatik olarak GLM-5.1 chain'ine düşecek — `config/model_router.yml` zaten hazır, sadece `GLM_API_KEY` env var bekliyor.

---

## Sabrican Pattern (Template)

Sabrican'ın yapısı — her persona için kopyalanacak:

```yaml
sabrican:
  secondary_runtimes:
    - id: openclaw
      mode: helper_only
      canonical_runtime: false
      activation_status: enabled
      dispatch_module: server.openclaw_bridge
      sub_agents: [openclaw_integrator, gateway_health_watcher, channel_delivery_operator, auth_profile_sync]
      skill_surfaces: [gateway_health, channel_delivery, auth_profile_sync, wrapper_control]
```

**Bridge dispatch fonksiyonları:**
- `dispatch_<task>()` — görev yönlendirme
- `run_<subagent>()` — subagent çalıştırma
- `send_<channel>_update()` — mesaj iletim

**Telegram komutları:**
- `/<persona>-health`, `/<persona>-skill`, `/<persona>-<task>`, `/<persona>-subagents`

---

## Mevcut Durum Özeti

| Persona | Domain | Codex Slot | Mevcut Skill | Secondary Runtime | Eksik |
|---|---|---|---|---|---|
| **Seda** | Kod/debug/PR | forge | aider, cline, claude_agent | ❌ yok | Claude Code bridge, GLM-5.1 route |
| **Mert** | Araştırma/rakip | nexus | mert_research_skill, web_search_deep | ❌ yok | Perplexity/Tavily adapter |
| **Buse** | Pazarlama/içerik | spark | buse_content_skill, instagram_skill | ❌ yok | Image gen, ElevenLabs |
| **Eren** | Veri/dashboard | spark | eren_data_skill | ❌ yok | DuckDB, Plotly, NotebookLM |
| **Luna** | Güvenlik (lab) | shield | luna_scan_skill, luna_browser_skill, luna_report_skill | ❌ yok | Semgrep, Bandit, Trivy |
| **Sabrican** | Ops/deploy | nexus | sabrican_ops, sabrican_subagent_runner | ✅ **OpenClaw** | Docker Compose tooling |
| **Sabri** | Strateji/yaratıcı | atlas | sabri_openclaw_skill, agency_os, c_level_advisor | ⚠️ isim çakışması | Sequential thinking MCP |

---

## Persona-Spesifik Tool Entegrasyon Önerileri

### Seda — Kod Ustası (Priority: 🔥 1)

**AI Tool Stack:**
- **Claude Code CLI** (primary) — `openclaw_bridge` pattern ile `claude_code_bridge.py`
- **Aider** (mevcut `aider_skill.py`) — git-aware refactor
- **Cline** (mevcut `cline_skill.py`) — VS Code agent
- **GLM-5.1** (Z.ai bekleniyor) — SWE-Bench #1, açık kaynak kod için
- **Codex forge slot** — `backend-engineer`, `code-reviewer`, `debugger`, `test-engineer`

**Sub-agents (önerilen):**
- `code_reviewer` — PR analiz
- `test_writer` — pytest/vitest üretim
- `refactor_agent` — git-aware refactor
- `glm_swe_runner` — SWE-Bench tarzı zor patch'ler GLM-5.1'e

**Telegram komutları:**
- `/seda-review <PR-URL>` — code review
- `/seda-refactor <dosya>` — aider zinciri
- `/seda-test <modül>` — test üret
- `/seda-glm <problem>` — GLM-5.1'e spesifik delegasyon

**Yeni dosya:**
- `server/seda_bridge.py` — dispatch katmanı

---

### Mert — Araştırma Ustası (Priority: 🔥 2)

**AI Tool Stack:**
- **Perplexity API** (web + citation) — yeni skill: `perplexity_skill.py`
- **Tavily Search** (semantic search) — yeni skill: `tavily_skill.py`
- **Jina AI Reader** (URL → markdown) — yeni skill: `jina_reader_skill.py`
- **GLM-5.1 long-context** — büyük doküman özetleme
- **Gemini 2.5 Pro 1M context** (fallback, mevcut)

**Sub-agents (önerilen):**
- `deep_researcher` — Perplexity zinciri
- `competitor_scanner` — rakip profil tarama
- `trend_tracker` — GitHub trending + HN takibi
- `source_archiver` — Jina → vault ingest

**Telegram komutları:**
- `/mert-derinara <konu>` — Perplexity deep research
- `/mert-rakip <şirket>` — competitor scan
- `/mert-trend` — haftalık teknoloji trendleri
- `/mert-arsivle <URL>` — Jina ile vault'a arşivle

**Yeni dosya:**
- `server/mert_bridge.py`

---

### Buse — Pazarlama Ustası (Priority: 3)

**AI Tool Stack:**
- **Gemini 2.5 image gen** (görsel üretim) — yeni skill: `gemini_image_skill.py`
- **ElevenLabs TTS** (reklam sesi) — yeni skill: `elevenlabs_skill.py`
- **Instagram Graph API** (mevcut `instagram_skill.py`) — posting
- **Buffer API** (scheduling) — yeni skill: `buffer_skill.py`
- **Claude Opus** (copywriting derinliği)

**Sub-agents (önerilen):**
- `copywriter` — landing/CTA üretimi
- `image_designer` — post/reel görseli
- `scheduler` — Buffer/Hootsuite posting
- `brand_voice_guard` — tone consistency

**Telegram komutları:**
- `/buse-landing <ürün>` — landing copy
- `/buse-gorsel <brief>` — image gen
- `/buse-post <platform> <içerik>` — post scheduler
- `/buse-ses <metin>` — ElevenLabs reklam sesi

**Yeni dosya:**
- `server/buse_bridge.py`

---

### Eren — Veri Ustası (Priority: 4)

**AI Tool Stack:**
- **DuckDB** (lokal analytics) — yeni skill: `duckdb_skill.py`
- **Plotly MCP** veya chart MCP — yeni skill: `plotly_chart_skill.py`
- **NotebookLM** (veri anlatımı) — mevcut `notebooklm_skill.py` var mı? Kontrol et
- **Pandas/Polars** (zaten Python'da)
- **Claude Opus** (analiz sentezi)

**Sub-agents (önerilen):**
- `sql_generator` — natural language → DuckDB SQL
- `chart_builder` — grafik üretimi
- `narrative_writer` — veri hikayesi
- `kpi_tracker` — metrik takibi

**Telegram komutları:**
- `/eren-sorgu <SQL/doğal dil>` — DuckDB
- `/eren-grafik <veri>` — chart gen
- `/eren-kpi` — haftalık metrikler
- `/eren-rapor <konu>` — veri raporu

**Yeni dosya:**
- `server/eren_bridge.py`

---

### Luna — Güvenlik Ustası (Priority: 5) ⚠️ lab-only

**AI Tool Stack:**
- **Semgrep** (SAST) — yeni skill: `semgrep_skill.py`
- **Bandit** (Python security) — yeni skill: `bandit_skill.py`
- **Trivy** (container scan) — yeni skill: `trivy_skill.py`
- **GLM-5.1** (security reasoning) — kod analizi için
- **Codex shield slot** — `security-auditor`, `pentest-engineer`

**Constraint:** `lab_only: true` — canlı hedef, izinsiz exploit HARD REJECT.

**Sub-agents (önerilen):**
- `sast_scanner` — Semgrep/Bandit zinciri
- `container_auditor` — Trivy
- `log_analyzer` — güvenlik log incele
- `defensive_advisor` — savunma önerileri (sadece)

**Telegram komutları:**
- `/luna-scan <repo>` — SAST (lab)
- `/luna-container <image>` — Trivy
- `/luna-log <path>` — log analiz
- `/luna-advise <senaryo>` — defensive öneri

**Yeni dosya:**
- `server/luna_bridge.py`

---

### Sabrican — Ops Ustası (Priority: ✅ mevcut)

**Zaten var:** OpenClaw helper layer. 4 subagent. 4 komut.

**Genişletme önerileri:**
- **Docker Compose skill** — yeni: `docker_compose_skill.py`
- **k8s MCP** — varsa bağla
- **Ansible runner** — yeni: `ansible_skill.py` (ileriki faz)

**Eksik komutlar:**
- `/sabrican-docker <compose-up/down/ps>`
- `/sabrican-deploy <servis>`
- `/sabrican-izle <servis-log>`

---

### Sabri — Strateji Ustası (Priority: 6)

**AI Tool Stack:**
- **Claude Opus** (reasoning depth) — primary
- **Sequential Thinking MCP** — çok-adımlı strateji
- **Agency OS skill** (mevcut `agency_os_skill.py`)
- **C-Level Advisor** (mevcut `c_level_advisor_skill.py`)
- **GLM-5.1 reasoning chain** (zaten model_router'da)

**Not:** `sabri_openclaw_skill.py` var — isim kafa karıştırıcı, aslında Sabrican'a ait olması lazım. Rename önerisi: `sabrican_openclaw_helper.py`.

**Sub-agents (önerilen):**
- `strategy_architect` — uzun vadeli plan
- `offer_designer` — teklif/kampanya
- `brand_positioner` — marka konumu
- `wildcard_connector` — disiplinlerarası bağlantı

**Telegram komutları:**
- `/sabri-strateji <konu>` — deep reasoning
- `/sabri-teklif <müşteri>` — offer writer
- `/sabri-baglanti <A> <B>` — iki disiplin bağlama
- `/sabri-vizyon` — 6-aylık vizyon

**Yeni dosya:**
- `server/sabri_bridge.py`

---

## Uygulama Sırası (Adım Adım)

1. **Seda bridge** (🔥 en yüksek değer — günlük kod işleri direkt etkiler)
2. **Mert bridge** (🔥 research otomasyonu, vault'la çakışıyor)
3. **Buse bridge** (pazarlama ihtiyacı netleşince)
4. **Eren bridge** (veri ihtiyacı KPI aşamasında)
5. **Luna bridge** (güvenlik pass olmadıkça beklet)
6. **Sabri bridge** (strateji seansları için)
7. **Sabrican genişletme** (docker_compose + k8s)

Her bridge ~2-3 saatlik iş: YAML update + `<persona>_bridge.py` + bridge.py komut handler'ları + test.

---

## GLM-5.1 Yerleşim Planı

`config/model_router.yml` GLM chain'leri zaten hazır:
- `code` chain: GLM-5.1 primary → Groq Kimi K2 fallback
- `reasoning` chain: GLM-5.1 → Gemini 2.5 Pro fallback

**2-3 gün sonra Z.ai üyelik geldiğinde:**
1. `.env` → `GLM_API_KEY=<key>`
2. Test: `python -c "from server.model_router import get_client; c = get_client('glm'); print(c.test())"`
3. `/seda-glm <problem>` ile smoke test
4. Otomatik devreye girecek (code chain'de primary)

**Persona bazlı GLM öncelik:**
- 🔥 Seda (SWE-Bench #1 kod)
- 🔥 Luna (security reasoning)
- ⭐ Sabri (strategy reasoning)
- ⭐ Mert (long-context research)
- Diğerleri: fallback olarak

---

## Onay Beklenen Kararlar

1. **Sıralama doğru mu?** Seda → Mert → Buse → Eren → Luna → Sabri → Sabrican extension
2. **Her persona için ayrı bridge dosyası (`<persona>_bridge.py`)** mı, yoksa tek `persona_bridges.py` mı tercih?
3. **Sabri vs Sabrican isim karışıklığı** — `sabri_openclaw_skill.py` rename olsun mu?
4. **Tool satın alım sırası:**
   - Perplexity API ($20/ay) — Mert için
   - ElevenLabs ($5/ay starter) — Buse için
   - Diğerleri ücretsiz (DuckDB, Semgrep, Bandit, Trivy, Jina)

## İlgili
- [[02-Projects/openclaw-integration]] — template
- [[04-Dev-Log/2026-04-17]] — POC roadmap
- [[06-Architecture/system-overview]] — mevcut persona tablosu
