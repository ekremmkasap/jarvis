# External Repos Map

Bu dosya `external-repos/` altina indirilen repolarin Jarvis'e nasil uyarlanacagini tek yerde tutar.

## Core Repo Havuzu

Bu grup, Jarvis'e dogrudan veya secilerek capability tasiyacagimiz repolardir.

### 1. `disler/claude-code-hooks-mastery`
- Rol: hook sinir sistemi
- Jarvis'te: `.claude/hooks/*`
- Durum: foundation entegre

### 2. `VoltAgent/awesome-codex-subagents`
- Rol: uzman alt-ajan havuzu
- Jarvis'te: `server/config/agent_manifests.json` icindeki `recommended_subagents`
- Durum: shortlist entegre

### 3. `paperclipai/paperclip`
- Rol: company layer / governance / org chart
- Jarvis'te: dashboard company karti, governance summary, quota pressure
- Durum: foundation entegre

### 4. `github/spec-kit`
- Rol: spec-driven gelistirme akisi
- Jarvis'te: `CLAUDE.md`, `.claude/commands/speckit.*`, `.specify/*`
- Durum: foundation entegre

## Core Ama Secilerek Kullanilacaklar

### 5. `alirezarezvani/claude-skills`
- Rol: marketing, growth, review, autoresearch
- Durum: secili skill'ler `.claude/skills/` altina alindi

### 6. `slavingia/skills`
- Rol: validate-idea, mvp, first-customers, pricing, marketing-plan
- Durum: secili skill'ler `.claude/skills/` altina alindi

### 7. `BlockRunAI/ClawRouter`
- Rol: model routing mantigi
- Durum: referans / ilham

## Reference Repo Havuzu

Bu grup, su an dogrudan entegre edilmeyecek ama mimari / runtime / ingest / UX dersi veren repolardir.

### 8. `kyegomez/swarms`
- Rol: hiyerarsik orchestration desenleri

### 9. `crewAIInc/crewAI`
- Rol: research -> execute -> review role patterni

### 10. `cline/cline`
- Rol: IDE ajan UX ve tool-use referansi

### 11. `paul-gauthier/aider`
- Rol: terminal coding agent akisi

### 12. `All-Hands-AI/OpenHands`
- Rol: sandboxed autonomous engineer akisi

### 13. `stitionai/devika`
- Rol: planning + web research + execution

### 14. `tanbiralam/claude-code`
- Rol: yarim milyon satir sinifinda runtime/orchestration referansi

### 15. `coleam00/claude-code-new-features-early-2026`
- Rol: 2026 feature set / roadmap referansi

### 16. `instructkr/claw-code`
- Rol: execution core mimari referansi

### 17. `HKUDS/CLI-Anything`
- Rol: computer mode / desktop control referansi

### 18. `mcp-server-youtube-transcript`
- Rol: transcript alma deseni

### 19. `youtube-mcp-server`
- Rol: YouTube MCP referansi

### 20. `youtube-transcript-api`
- Rol: transcript fallback referansi

## Önerilen Sayım

- Fiziksel indirilen repo sayısı: 22
- Aktif core repo havuzu: 15
- Reference repo havuzu: 7

Eger istenirse active core sayisi 18'e kadar genisletilebilir; ama su an daha temiz olan model 15 core + 7 reference ayrimidir.

## Kullanım Kuralı

- Dış repolar aynen içeri dökülmez.
- Jarvis'e sadece secili pattern ve capability taşınır.
- Her entegrasyon:
  1. local-first
  2. küçük doğru değişiklik
  3. mevcut runtime'ı bozmama
  kurallarıyla yapılır.
