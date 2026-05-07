# Claude Managed Agents - Jarvis Roadmap

Source date: 2026-04-15
Source type: operator-provided roadmap note

## Ana Fikir

Jarvis'in hedefi sadece kullanicinin laptopunda calisan bir masaustu asistani olmak degil. Nihai hedef, 24/7 calisabilen managed-agent mimarisidir.

Managed-agent mantigi uc parcadan olusur:

- Agent Config: hangi model, hangi yetki, hangi skill, hangi arac.
- Environment: ajan icin hazir calisma ortami; Python, Node, repo, MCP baglantilari, credential politikasi.
- Session: gorevin gercek kosusu; dosya, hafiza ve konusma durumu devam eder.

Jarvis icin karsiligi:

- Agent Config -> `config/agents.yaml`, `config/model_router.yml`, persona `llm_profile`, skill registry.
- Environment -> `master_launcher.py`, `.env`, MCP/Slack/GitHub/Gmail/Notion baglantilari, local/remote runner.
- Session -> `state/`, `server/.reme/`, `persona_memory`, `swarm` task state, `outputs/`.

## Jarvis Vizyonu

Jarvis su sekilde evrilmeli:

- Lokal mod: `JARVIS.bat` ile masaustunde voice + hologram + bridge.
- Cloud/managed mod: ayni ajan configleri cloud runner uzerinde 24/7 calisir.
- Hibrit mod: lokal ses/hologram kullanici arayuzu olur; agir ve uzun gorevler cloud-managed session'a dispatch edilir.

## Neden Onemli

Lokal Jarvis guclu ama laptop bagimlidir:

- Laptop kapanirsa is durur.
- Internet koparsa ajanlar durur.
- Uzun sosyal medya, lead, Slack/GitHub/Gmail takip gorevleri sureklilik ister.

Managed-agent modeli bu bagimliligi kaldirir:

- Ajanlar uyurken de calisir.
- OAuth/MCP ile tool baglantilari API key kopyalamadan yonetilir.
- Skill'ler cloud session icinde de kullanilir.
- Session state kalici oldugu icin gorev sifirdan baslamaz.

## Jarvis Icin Uygulama Katmanlari

### 1. Agent Config Standardi

Her Jarvis personasi icin config ayni sekilde okunmali:

- `id`
- `display_name`
- `role`
- `model_chain`
- `llm_profile`
- `voice_model`
- `tools`
- `skills`
- `risk_level`
- `auto_approve`

Mevcut 7 persona key havuzu bu katmana baglidir:

- Seda
- Mert
- Buse
- Eren
- Luna
- Sabrican
- Sabri

### 2. Environment Standardi

Jarvis environment iki moda ayrilmali:

- `local`: Windows masaustu, Mark-XXXV voice, Electron hologram, local bridge.
- `managed`: cloud session, MCP OAuth, persistent workspace, scheduled/background jobs.

Environment config su sorulari cevaplamali:

- Bu ajan hangi repo/vault ile calisacak?
- Hangi MCP/tool baglantilari aktif?
- Hangi env key'ler mevcut?
- Hangi komutlar onay ister?
- Hangi dosyalara yazabilir?

### 3. Session Standardi

Her uzun gorev session olarak kaydedilmeli:

- `session_id`
- `persona_id`
- `goal`
- `status`
- `started_at`
- `last_heartbeat`
- `artifacts`
- `memory_refs`
- `handoff_notes`

Bu model Jarvis'teki mevcut swarm ve autonomous loop yapisina uyarlanabilir.

## MCP / OAuth Yaklasimi

Hedef: Gmail, Slack, GitHub, Notion, Google Drive gibi araclari Jarvis'e API key kopyalayarak degil, OAuth/MCP baglantisi olarak tanitmak.

Jarvis kurali:

- Lokal `.env` sadece local fallback ve self-hosted servisler icin kullanilir.
- OAuth/MCP connector yetkileri cloud/managed agent tarafinda tutulur.
- Secret/key/cookie icerigi wiki'ye yazilmaz.
- Wiki sadece hangi connector'in ne icin kullanildigini ve operasyon kurallarini tutar.

## Skill Yaklasimi

Managed-agent vizyonunda skill'ler Jarvis'in superpower katmanidir.

Jarvis skill standardi:

- Kisa `SKILL.md`
- Gerekiyorsa `references/`
- Gerekiyorsa `agents/openai.yaml`
- Gereksiz README/changelog yok
- Tek sorumluluk
- Test edilebilir command veya Python entrypoint

Bu yaklasim `jarvis-collab-router`, `media_intake_skill`, `repo_file_index_skill`, `batch_profile_scraper` gibi yerel skill'leri cloud session'a tasinabilir hale getirir.

## Oncelikli Use Case'ler

### 1. Content Assistant

Jarvis sosyal hesaplari ve Reels verilerini takip eder:

- Instagram/Reels metadata alir.
- Hook, CTA, lead magnet sinyali cikarir.
- Wiki'ye kaydeder.
- Buse/Sabri persona'lari icerik onerisi uretir.

### 2. CRM / Lead Updater

Jarvis Gmail, Slack, Instagram ve form kaynaklarini izler:

- Yeni lead adaylarini yakalar.
- Lead wiki profili uretir.
- Eren skorlar.
- Sabri stratejik aksiyon onerir.

### 3. Code Reviewer

Jarvis GitHub PR ve CI durumunu izler:

- Review thread okur.
- CI fail analiz eder.
- Patch planlar.
- User onayi olmadan merge/push yapmaz.

### 4. Ad Monitor

Jarvis reklam metriklerini takip eder:

- CPL/CPA spike yakalar.
- Gunluk rapor uretir.
- Slack/Telegram sesli anons yapar.

### 5. Client Email Responder

Jarvis gelen mailleri okur:

- Taslak yanit uretir.
- Kullanici onayi olmadan gondermez.
- CRM ve lead memory ile baglar.

## Jarvis Icin Faz Plani

### Faz 1 - Local Managed-Agent Emulation

Amaç: Cloud'a gecmeden once ayni mimariyi lokal Jarvis icinde standartlastirmak.

Gerekli isler:

- Agent config alanlarini standart hale getir.
- Session manifest formatini ekle.
- Skill registry'yi command/router ile bagla.
- Repo file index ve media intake'i wiki ile bagla.
- Voice narrator task completion anonslarini standardize et.

### Faz 2 - Cloud Runner Adapter

Amaç: Uzun gorevleri lokalden bagimsiz calisacak runner'a dispatch etmek.

Gerekli isler:

- `managed_session` abstraction.
- `start_session`, `status_session`, `stop_session`, `resume_session`.
- Local runner ve cloud runner ayni interface'i kullansin.
- Artifacts `outputs/managed_sessions/` altina yazilsin.

### Faz 3 - MCP/OAuth Tool Layer

Amaç: Slack, GitHub, Gmail, Drive, Notion connector'larini agent environment katmanina baglamak.

Gerekli isler:

- Connector registry.
- Yetki matrisi.
- Read-only ve write-on-approval modlari.
- Slack/GitHub outgoing action guard.

### Faz 4 - 24/7 Operational Agents

Amaç: Jarvis'in belirli ajanlari surekli gorevlerde calissin.

Ilk 7 operasyon:

- Sabrican: system health/watchdog.
- Buse: content trend monitor.
- Eren: KPI/data monitor.
- Sabri: daily CEO synthesis.
- Seda: repo/code queue.
- Luna: browser/research watcher.
- Mert: long-form research/notebook synthesis.

## Net Davranis Kurali

Kullanici "Jarvis 24/7 calissin", "managed agent", "cloud agent", "laptop kapaliyken calissin", "Slack/Gmail/GitHub takip etsin" dediginde bu roadmap aktif kabul edilir.

Once hedef belirlenir:

- Tek ajan mi?
- 7 persona mi?
- Lokal emulation mi?
- Gercek cloud/managed dispatch mi?
- Hangi connector'lar read-only, hangileri write-on-approval?

Sonra uygulama en kucuk guvenli fazdan baslar.

