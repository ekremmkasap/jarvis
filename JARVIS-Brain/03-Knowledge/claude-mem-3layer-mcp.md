---
tags: [knowledge, memory, mcp, architecture]
date: 2026-04-16
source: instagram
---

# Claude-Mem — 3-Layer MCP Memory

MCP üzerinden **3 katmanlı memory** — progressive disclosure, BM25 index.

## 3 Katman
1. **Hot layer** — son N mesaj, ham
2. **Warm layer** — özetlenmiş, indexed (BM25)
3. **Cold layer** — archived, semantic search ile çağrılır

## Progressive Disclosure
LLM'e hemen tüm geçmişi vermek yerine, ihtiyaca göre katman katman açılır. Önce hot → gerekirse warm → gerekirse cold.

## BM25 Index
Keyword-based retrieval; semantic embedding'e göre daha hızlı/ucuz, teknik içerikte daha isabetli.

## Bilinen Sorunlar
- Node ve Bun runtime karışık → kurulum tuhaflıkları
- JSON parser XML'i reject ediyor → tool output format mismatch

## Jarvis İçin
- `server/skills/` altındaki sentence-transformers memory ile kıyaslanabilir
- `.claude/` MEMORY.md + auto-memory sistemi zaten katmanlı
- JARVIS-Brain vault = kalıcı cold layer olarak düşünülebilir

## Kaynak
- https://www.instagram.com/reel/DW_j8JJkkGo/

## İlgili
- [[graphify-token-optimization]] — benzer amaç, farklı yaklaşım
- [[06-Architecture/system-overview]]
