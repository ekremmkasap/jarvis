# Claude Code Kaynak Kodu — Jarvis Entegrasyon Planı

**Tarih:** 2026-04-12  
**Kaynak:** `claude-code-main/src/`  
**Hedef:** Jarvis Mission Control

---

## Özet

Claude Code'un sızdırılan kaynak kodunda incelenen dizinler:

| Dizin / Dosya | Ne İçeriyor |
|---|---|
| `src/coordinator/coordinatorMode.ts` | Çok-ajan orkestrasyon sistemi (Coordinator + Worker pattern) |
| `src/skills/bundledSkills.ts` | Skill kayıt sistemi (registerBundledSkill + dosya extraction) |
| `src/skills/bundled/batch.ts` | Paralel worktree'lerde 5-30 ajan çalıştırma + PR takibi |
| `src/skills/bundled/remember.ts` | Çok-katmanlı hafıza gözden geçirme skill'i |
| `src/cost-tracker.ts` | Model bazlı token + USD maliyet takibi, oturum arası kalıcılık |
| `src/voice/voiceModeEnabled.ts` | Sesli mod kill-switch + OAuth kontrol katmanı |
| `src/plugins/builtinPlugins.ts` | Kullanıcı açıp kapatabilen plugin registry sistemi |

Jarvis'in zaten sahip olmadığı ama kesinlikle ihtiyaç duyduğu **3 entegrasyon** aşağıda detaylandırılmıştır.

---

## Entegrasyon 1 — Model Bazlı Token & Maliyet Takibi

### Kaynak Dosyalar
- `src/cost-tracker.ts`
- `src/utils/modelCost.js` (calculateUSDCost)

### Ne Yapıyor
Claude Code her LLM çağrısında input/output/cache token sayısını ve USD maliyetini model adı bazında birikimli olarak tutar. Oturum kapanınca `saveCurrentSessionCosts()` ile proje config'e yazar; bir sonraki oturumda `restoreCostStateForSession()` ile geri yükler. Web UI'da `formatTotalCost()` ile "kullanım model bazında" gösterimi yapar.

Jarvis'in `model_router.py`'i Groq / Gemini / Ollama / Claude arasında routing yapıyor ama hiçbir yerde token tüketimi veya TL/USD maliyet birikimi tutulmuyor. SaaS müşterilerine abonelik planı sunulduğu hâlde kullanım görünürlüğü yok.

### Jarvis'te Nereye Gidecek

| Bileşen | Dosya |
|---|---|
| Token sayacı Python modülü | `server/cost_tracker.py` (yeni) |
| Model router hook'u | `server/model_router.py` — her `chat()` çağrısından sonra `record_usage(model, input_tokens, output_tokens, cost_usd)` çağrısı |
| SQLite depolama | `server/data/usage.db` — tablo: `(ts, model, input_tok, output_tok, cost_usd, session_id)` |
| Web UI widget | `apps/web-ui/src/components/StatsBar.tsx` — mevcut stats bar'a "Bugün: $X.XX / N token" satırı |
| Bridge endpoint | `server/bridge.py` — `GET /api/usage?period=today|week|month` |

### Tahmini İş Yükü
**M (Medium)** — ~4 saat  
Sıfır dış bağımlılık (SQLite stdlib). Model_router'daki her API çağrısı zaten tek noktadan geçiyor, hook kolaydır. StatsBar TypeScript tarafında küçük eklemedir.

---

## Entegrasyon 2 — Coordinator / Worker Paralel Ajan Çerçevesi

### Kaynak Dosyalar
- `src/coordinator/coordinatorMode.ts`
- `src/skills/bundled/batch.ts`

### Ne Yapıyor
Claude Code, bir "Coordinator" ajan spawn ediyor; Coordinator bağımsız görev birimlerini paralel "Worker" ajanlara devrediyor. Her Worker izole bir `git worktree`'de çalışıp PR açıyor. Coordinator notifikasyon aldıkça durum tablosunu güncelliyor. Batch skill bu çerçeveyi 5-30 paralel iş için somutlaştırıyor.

Jarvis'in `swarm_skill.py` ve `agent_runner.py` yapısı var ama şu an:
- Ajanlar sıralı (sequential) çalışıyor ya da basit thread pool var.
- Coordinator → Worker görev devirinde "sentez" adımı yok; Coordinator bulguları anlamadan doğrudan devretme anti-pattern'i mevcut.
- Worker bitişlerinde merkezi bir durum takibi yok.

### Jarvis'te Nereye Gidecek

| Bileşen | Dosya |
|---|---|
| Coordinator sınıfı | `server/agents/coordinator_agent.py` (yeni) |
| Worker havuzu | `services/orchestrator/agent_runner.py` — `run_parallel_workers(tasks: list[WorkerTask])` metodu |
| Görev durum izleme | `services/orchestrator/live_state.py` — mevcut `build_live_event_counts()` yanına `worker_status_table()` |
| Bridge endpoint | `server/bridge.py` — `POST /api/batch` komutu: `{instruction, max_workers}` alıp Coordinator başlatır |
| Web UI tablo | `apps/web-ui/src/components/StatsBar.tsx` veya yeni `WorkerStatusTable.tsx` |

**Temel tasarım kararı (kaynak koddan alınan):** Coordinator her Worker sonucunu **kendisi sentezlemeli** — "based on your findings, fix it" gibi delegasyon yasaklanmalı. Bu kural `server/agents/coordinator_agent.py` system prompt'una yazılmalı.

### Tahmini İş Yükü
**L (Large)** — ~2-3 gün  
Mevcut `swarm_skill.py` ile çakışmaları çözme, worktree izolasyonu (Windows'ta git worktree desteği test gerektirir), Telegram üzerinden durum bildirimi entegrasyonu gerekiyor. Değer yüksek ama risk de yüksek.

---

## Entegrasyon 3 — Skill Kayıt Sistemi: `BundledSkillDefinition` Pattern'i

### Kaynak Dosyalar
- `src/skills/bundledSkills.ts`
- `src/plugins/builtinPlugins.ts`

### Ne Yapıyor
Claude Code'da skill'ler `registerBundledSkill({ name, description, whenToUse, allowedTools, getPromptForCommand })` ile merkezi registery'e kaydedilir. Her skill:
- `whenToUse` alanıyla LLM'e kendini tanıtır (semantic routing için).
- `isEnabled()` fonksiyonuyla runtime'da açılıp kapanabilir.
- İsteğe bağlı `files` dict'i ile referans dosyalarını diske extract edip skill prompt'unu `Base directory: <dir>` ile prefix'leyerek LLM'in `Read/Grep` yapmasına izin verir.
- Plugin sistemi sayesinde kullanıcı `/plugin` UI'ından skill'leri toggle edebilir.

Jarvis'in `server/skills/` dizininde 60+ Python skill dosyası var ama:
- `bridge.py`'deki dispatcher if/elif zinciri ile yönetiliyor — yeni skill eklenince bridge.py'i elle düzenlemek gerekiyor.
- `whenToUse` / semantic routing yok; intent ya hardcoded ya da LLM'e bırakılmış.
- Runtime enable/disable mekanizması yok.

### Jarvis'te Nereye Gidecek

| Bileşen | Dosya |
|---|---|
| Skill registry modülü | `server/skill_registry.py` (yeni) — `register_skill(name, description, when_to_use, handler_fn, enabled=True)` |
| Auto-discovery | `server/skill_registry.py` — `server/skills/` dizinini tarayıp `SKILL_META = {...}` dict'i olan dosyaları otomatik yükle |
| Bridge dispatcher güncelleme | `server/bridge.py` — if/elif zincirini `registry.dispatch(command, args)` tek çağrısıyla değiştir |
| Telegram routing | `server/telegram/telegram_intelligence.py` — `intent` sonucunu registry'nin `when_to_use` alanlarıyla eşleştir |
| Web UI skill listesi | `apps/web-ui/src/app/page.tsx` veya yeni `SkillPanel.tsx` — `GET /api/skills` endpoint'inden skill listesini çekip toggle UI |

### Tahmini İş Yükü
**M (Medium)** — ~6 saat  
Mevcut skill dosyaları bozulmadan korunabilir; sadece her dosyaya `SKILL_META` dict'i eklenir. Bridge.py dispatcher refactor riskli ama izole test edilebilir. Değer/risk oranı en yüksek entegrasyon budur.

---

## Öncelik Sırası

| Öncelik | Entegrasyon | Sebep |
|---|---|---|
| 1 | Skill Registry | En az riskli, en fazla uzun vadeli fayda; bridge.py bakımını dramatik azaltır |
| 2 | Maliyet Takibi | SaaS müşteri faturalaması için kritik; sıfır dış bağımlılık |
| 3 | Coordinator/Worker | Güçlü ama Windows worktree ve swarm çakışması nedeniyle daha fazla hazırlık gerektirir |

---

## İlgili Jarvis Dosyaları (Referans)

- `server/bridge.py` — ana dispatcher (Entegrasyon 1, 2, 3 hepsi dokunur)
- `server/model_router.py` — Entegrasyon 1 hook noktası
- `server/skills/swarm_skill.py` — Entegrasyon 2 ile çakışma riski
- `services/orchestrator/agent_runner.py` — Entegrasyon 2 genişletme hedefi
- `apps/web-ui/src/components/StatsBar.tsx` — Entegrasyon 1 ve 3 UI hedefi
- `apps/web-ui/src/hooks/useJarvisStore.ts` — state yönetimi, her entegrasyon için güncellenebilir
