# Claude Code Kaynak Kodu Analizi

[[index]] | Tarih: 2026-04-12 | Kaynak: `claude-code-main/src/`

## Genel Bakış

Claude Code'un sızdırılan TypeScript kaynak kodu incelendi. Sistem Bun runtime üzerinde çalışan, React/Ink tabanlı bir terminal UI uygulamasıdır. `@anthropic-ai/sdk` ve `@modelcontextprotocol/sdk` bağımlılıkları üzerine kurulu çok katmanlı bir mimari sunar.

---

## Modül Tablosu

| Dizin | Açıklama | Öne Çıkan Dosyalar |
|-------|----------|-------------------|
| `tools/AgentTool` | Sub-agent yönetimi — yeni bir agent spawn eder, araç listesi ve izin kapsamını yönetir, transcript kaydı tutar | `runAgent.ts`, `prompt.ts`, `loadAgentsDir.ts`, `forkSubagent.ts` |
| `tools/BashTool` | Kabuk komutu çalıştırıcı, timeout ve sandbox yönetimi | `BashTool.tsx` |
| `tools/FileEditTool` | Dosya düzenleme aracı (diff tabanlı) | `FileEditTool.tsx` |
| `tools/SkillTool` | Skill tanımlarını yükler ve çalıştırır | `SkillTool.tsx` |
| `tools/ScheduleCronTool` | Cron ifadesi oluşturup tekrarlayan görev zamanlar | `prompt.js` |
| `tools/SendMessageTool` | Agent'lar arası mesajlaşma | `constants.js` |
| `skills/bundled` | Yerleşik skill'ler: loop, simplify, updateConfig, scheduleRemoteAgents, remember, verify | `loop.ts`, `simplify.ts`, `updateConfig.ts`, `remember.ts` |
| `skills/loadSkillsDir.ts` | Dizinden `.md` skill dosyalarını dinamik yükler | `loadSkillsDir.ts` |
| `coordinator/coordinatorMode.ts` | Coordinator (CEO) vs normal agent modunu belirler; swarm yönetimi için özel araç seti | `coordinatorMode.ts` |
| `bridge` | Claude.ai ile uzak oturum köprüsü — JWT, polling, session spawner, WebSocket transport | `bridgeMain.ts`, `replBridge.ts`, `jwtUtils.ts`, `sessionRunner.ts` |
| `services/mcp` | MCP sunucu bağlantısı (stdio, SSE, StreamableHTTP), araç proxy, OAuth akışı | `client.ts` |
| `services/autoDream` | Arkaplanda bellek konsolidasyonu — session sayısı ve zaman eşiğine göre `/dream` çalıştırır | `autoDream.ts`, `consolidationPrompt.ts` |
| `services/extractMemories` | Oturumdan hafıza çıkarma servisi | `extractMemories.ts` |
| `services/analytics` | Growthbook feature flag, Datadog, event log | `growthbook.js`, `index.js` |
| `services/lsp` | LSP entegrasyonu (dil sunucusu desteği) | `lsp/` |
| `context` | Sistem promptu ve kullanıcı bağlamı oluşturma, her turn'de inject | `context.ts` |
| `coordinator` | Swarm koordinatör modu, TeamCreate/TeamDelete araçları | `coordinatorMode.ts` |
| `components` | Ink/React terminal UI bileşenleri: App, BridgeDialog, AutoUpdater vb. | `App.tsx`, `BridgeDialog.tsx` |
| `hooks` | React hook'ları: useVoice, useSwarmInitialization, useTaskListWatcher, useMergedTools | `useVoice.ts`, `useSwarmInitialization.ts` |
| `state` | AppState store, selectors, state transitions | `AppStateStore.ts`, `store.ts` |
| `tasks` | Görev tipleri: LocalAgentTask, RemoteAgentTask, InProcessTeammateTask, DreamTask | `types.ts`, `DreamTask/` |
| `voice` | Ses modu etkinleştirme bayrağı | `voiceModeEnabled.ts` |
| `memdir` | Auto-memory dizin yolları ve yönetimi | `paths.ts` |
| `plugins` | Plugin yükleme ve builtin plugin'ler | `builtinPlugins.ts` |
| `commands` | 100'den fazla slash command: advisor, bughunter, compact, diff, review, teleport, ultraplan vb. | `advisor.ts`, `review.ts`, `ultraplan.tsx` |
| `QueryEngine.ts` | Ana sorgu döngüsü — araç çağrısı, model yanıtı, streaming yönetimi | `QueryEngine.ts` |
| `Task.ts` | Görev yaşam döngüsü soyutlaması | `Task.ts` |
| `Tool.ts` | Araç sözleşmesi ve ToolUseContext tanımı | `Tool.ts` |

---

## Jarvis'e Entegre Edilebilecek 5 Pattern

### 1. `autoDream` — Arkaplan Bellek Konsolidasyonu
`services/autoDream/` dizinindeki sistem, belirli sayıda session birikmesi ve zaman eşiği geçtikten sonra otomatik olarak bir sub-agent spawn ederek eski oturumları özetler ve uzun süreli belleğe yazar. Jarvis'in `memory.py` modülüne bu "uyku-sırasında-öğren" döngüsü eklenebilir: Telegram konuşmaları belirli threshold'u geçince `/dream` komutuyla özetlenip SQLite'a konsolide edilir.

### 2. `skills/loadSkillsDir.ts` — Dosyadan Dinamik Skill Yükleme
Markdown dosyalarını tarayarak runtime'da skill olarak kaydetme mekanizması. Jarvis'teki `SkillRegistry` zaten benzer bir yapıya sahip; aynı pattern ile `.md` tabanlı skill'ler `server/skills/` altına `loadSkillsDir` mantığıyla entegre edilebilir — kod yazmadan skill eklenebilir hale gelir.

### 3. `coordinator/coordinatorMode.ts` — CEO/Worker Swarm Mimarisi
Coordinator agent'ın `TEAM_CREATE_TOOL`, `TEAM_DELETE_TOOL` ve `SEND_MESSAGE_TOOL` aracılığıyla alt-agent'ları yönetme biçimi. Jarvis'in Codex Swarm mimarisiyle (`project_codex_swarm_architecture.md`) doğrudan örtüşüyor — coordinator/normal mod ayrımı Jarvis'in `agent_runner.py`'sine uygulanabilir.

### 4. `tools/ScheduleCronTool` + `skills/bundled/loop.ts` — Doğal Dil Cron
"check deploys every 5m" gibi doğal dil ifadelerini cron ifadesine çeviren ve `ScheduleCronTool` ile planlayan zincir. Jarvis Telegram botuna bu pattern uygulanarak kullanıcı "her gün sabah 8'de rapor ver" diyebilir, bot bunu cron'a çevirebilir.

### 5. `services/mcp/client.ts` — Çoklu Transport MCP Bağlantısı
SSE, stdio ve StreamableHTTP üç transport tipini destekleyen MCP client. Jarvis'in mevcut Notion/Gmail MCP entegrasyonları yalnızca stdio kullanıyor; SSE veya StreamableHTTP eklenirse uzak MCP sunuculara (bulut tabanlı) bağlanılabilir ve yeni skill'ler sunucu yeniden başlatılmadan yüklenebilir.

---

## İlgili Jarvis Sayfaları

- [[mimari-genel-bakis]] — Jarvis katman yapısı
- [[ajanlar]] — Swarm mimarisi planları
- [[oz-ogrenme]] — Bellek konsolidasyonu bağlantısı
- [[entegrasyonlar]] — MCP entegrasyonları
