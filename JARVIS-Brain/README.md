---
tags: [vault, index, jarvis]
date: 2026-04-16
---

# JARVIS-Brain

Jarvis Mission Control'un kalıcı bilgi deposu. Obsidian vault olarak kuruldu, Claude Code MCP (`jarvis-brain` / @bitbonsai/mcpvault) üzerinden erişilebilir.

## Amaç

- Günlük dev log ve mimari kararlar tek yerde
- Instagram, GitHub, makale kaynaklarının kategorize arşivi
- Jarvis personalarının (Seda, Mert, Buse, Sabri, Eren, Luna, Sabrican) proje bellekleri
- Sohbet arası bilgi devamlılığı

## Aktif Roadmap
- [[02-Projects/persona-tool-matrix]] — 7 persona × AI tool entegrasyon planı (2026-04-17)
- [[04-Dev-Log/2026-04-17]] — POC roadmap: VibeVoice, Octogent, Graphify, Claude-Mem, OpenGuider

## Klasör Yapısı

| Klasör | İçerik |
|---|---|
| `01-Daily-Notes/` | Günlük notlar (`YYYY-MM-DD.md`) — kısa, serbest form |
| `02-Projects/` | Aktif projeler — Jarvis Mission Control, OpenClaw, CloudManager |
| `03-Knowledge/` | Konsept sayfaları — Graphify, VibeVoice, Claude-Mem, Opus 4.7 |
| `04-Dev-Log/` | Detaylı dev log (`YYYY-MM-DD.md`) — ne yapıldı, neden, nasıl |
| `05-Resources/` | Dış kaynaklar — Instagram linkleri, GitHub repo listesi |
| `06-Architecture/` | Sistem mimarisi — overview, port tablosu, data flow |

## Navigation

- Başla: [[04-Dev-Log/2026-04-16]] — bugünkü log
- Proje: [[02-Projects/jarvis-mission-control]]
- Mimari: [[06-Architecture/system-overview]]
- Kaynaklar: [[05-Resources/instagram-sources]], [[05-Resources/github-repos]]

## Kullanım

Yeni not/log eklerken:
1. Doğru klasöre koy
2. YAML frontmatter (tags, date) eklemeyi unutma
3. Obsidian `[[bağlantı]]` syntax'ı kullan
4. Tarih formatı: `YYYY-MM-DD`
