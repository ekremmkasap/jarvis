# Jarvis Mission Control — Yol Haritası
Olusturulma: 2026-03-01

---

## MEVCUT DURUM (Tamamlanan)

### Altyapi
- Ubuntu sunucu: 192.168.1.109 (userk/userk1)
- Node.js v22, Python 3.12, Claude Code v2.1.63 (Pro plan - selenkasaap122@gmail.com)
- Claude binary: /home/userk/.npm-global/bin/claude
- Ollama: aktif, llama3.2:latest kurulu (2.0 GB)

### Jarvis Cekirdegi (/opt/jarvis/)
- core/agent.py         — CoreAgent, Task, MemoryManager, SubAgent (state machine)
- core/orchestrator.py  — Orchestrator + PlannerAgent, ImplementerAgent, ReviewerAgent
- agents/claude_agent.py  — Claude CLI ile AI (root icin /root/.claude/ credential var)
- agents/ollama_agent.py  — Ollama REST API (http://127.0.0.1:11434)
- skills/cognitive/parse_requirements.py
- skills/cognitive/memory_compactor.py  — 50 mesaj dolunca otomatik ozet
- skills/execution/run_command.py
- skills/execution/sunucu_yonet.py      — systemctl, log, disk/ram/cpu
- skills/execution/kod_yaz.py           — dosya yaz/oku/syntax kontrol
- skills/io/read_file.py
- skills/governance/policy_check.py     — audit trail, rol bazli yetki

### Telegram Entegrasyonu
- /home/userk/telegram_gateway_v2.py    — Ana gateway (aktif servis)
- /home/userk/jarvis_router.py          — Mesaj siniflandirici + AI yonlendirici
- Bot token: [redacted - use .env]
- Authorized Chat ID: [redacted - use .env]
- Komutlar: /help, /status, /memory, /tasks
- Her mesaj → JarvisRouter → Claude (karmask) / Ollama (basit) / Skill (sunucu)

### Servisler
- gateway.service        — telegram_gateway_v2.py (AKTIF)
- openclaw.service       — AKTIF
- openclaw-gateway.service — AKTIF
- ollama.service         — AKTIF

### Bellek
- /opt/jarvis/memory/working_memory/chat_history.jsonl  — Son 50 mesaj (sonra compaction)
- /opt/jarvis/memory/project_memory/MEMORY.md           — Proje kararlari
- /opt/jarvis/memory/project_memory/MISSION.md          — Misyon tanimi
- /opt/jarvis/memory/project_memory/chat_summaries.md   — Compaction ozetleri
- /opt/jarvis/memory/knowledge_store/                   — (bos, FAZ 3)

---

## SONRAKI ADIMLAR (Oncelik sirasi)

### FAZ 2-A: AI Kalitesini Artir (ONCELIKLI)
[ ] Claude cevaplarini Telegram'da test et (nasılsın, sunucu durumu, kod yaz...)
[ ] Ollama yavas ise: sunucu_yonet skill'e dogrudan cevap uret (AI olmadan)
[ ] ClaudeAgent timeout'u 60sn yap, Ollama fallback calis tirma suresini artir
[ ] jarvis_router._classify() iyilestir: daha iyi kategori tespiti

### FAZ 2-B: Yeni Skills
[ ] skills/io/youtube_upload.py    — yt-dlp + YouTube Data API v3
[ ] skills/io/tiktok_upload.py     — TikTok uploader
[ ] skills/io/eticaret.py          — Shopify + Printify API
[ ] skills/execution/git_ops.py    — git clone/pull/push/commit
[ ] skills/cognitive/summarize.py  — Uzun metni ozetle

### FAZ 2-C: OpenClaw Entegrasyonu
[ ] /opt/jarvis/openclaw/bridge.py gercek implementasyon yaz
[ ] OpenClaw <-> Jarvis mesaj kanali kur
[ ] openclaw.json Ollama modellerini guncelle (llama3.2 hazir)

### FAZ 3: Otomasyon Fabrikasi
[ ] YouTube otomasyon pipeline: video bul → indir → edit → yukle
[ ] TikTok AI influencer: icerik uret → seslendir → yukle
[ ] E-ticaret: Shopify urun ekle, Printify siparis takip
[ ] Cron job: belirlenen saatlerde otomatik gorev calistir (/opt/jarvis/config/cron.json)

### FAZ 4: Cok Kullanicili / Guvenlik
[ ] Telegram grup destegi (allowlist ile)
[ ] API key donusumu (claude.ai OAuth yerine)
[ ] Rate limiting: kullanici basi dakikada max istek
[ ] Rollback sistemi: basarisiz gorevler icin geri alma

---

## BILINEN SORUNLAR

1. Ollama yavas: llama3.2 CPU ile calisiyor, GPU yok. Cevap 15-30sn surebilir.
   Cozum: Kucuk model (llama3.2:1b) veya Ollama timeout artir.

2. gateway.service User=root: Guvenlik riski. 
   Cozum: User=userk yap, sudo olmadan calisan servislere gec.

3. Telegram mesaj limiti: 4096 karakter.
   Cozum: telegram_gateway_v2.py send() fonksiyonu bolme yapiyor (OK).

4. chat_history.jsonl compaction: Claude ile ozetleme yapiyor ama Claude da
   zaman alabilir. Asenkron Popen ile cozuldu (gateway bloklanmiyor).

---

## KRITIK DOSYALAR (Hizli referans)

Degistirince gateway restart gerekir:
  /home/userk/telegram_gateway_v2.py
  /home/userk/jarvis_router.py

Degistirince restart gerekmez (runtime import):
  /opt/jarvis/agents/*.py
  /opt/jarvis/skills/**/*.py
  /opt/jarvis/core/agent.py
  /opt/jarvis/core/orchestrator.py

Servis yeniden baslatma:
  echo userk1 | sudo -S systemctl restart gateway.service

Log izleme:
  echo userk1 | sudo -S journalctl -u gateway.service -f

---

## YENI OTURUMDA BASLANGIC KONTROL LISTESI

1. ssh userk@192.168.1.109
2. systemctl is-active gateway.service  → active olmali
3. ollama list                           → llama3.2 gozukmeli
4. Telegram'dan /status yaz             → cevap gelmeli
5. Yukardaki SONRAKI ADIMLAR listesine bak, birinden devam et
