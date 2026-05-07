# Contract: HTTP API — MARK-XXXXVI

## GET /api/persona/{id}/memory

Persona'nın son N konuşma mesajını döner.

**Path params**: `id` — persona id (seda, mert, buse, ...)  
**Query params**: `limit` (default: 5, max: 20)

### Response 200
```json
{
  "persona_id": "seda",
  "persona_name": "Seda",
  "recent_messages": [
    {"role": "user", "content": "şu kodu incele", "ts": "2026-04-14T10:30:00"},
    {"role": "assistant", "content": "Auth tarafında null guard eksik...", "ts": "2026-04-14T10:30:02"}
  ],
  "last_active": "2026-04-14T10:30:02",
  "obsidian_note_count": 3
}
```

### Response 404
```json
{"error": "persona_not_found", "id": "unknown"}
```

### Rules
- `recent_messages` en yeniden eskiye sıralı
- `obsidian_note_count` OBSIDIAN_VAULT_PATH yoksa 0

---

## GET /api/agents/summary

Tüm 7 persona'nın hafıza özeti.

### Response 200
```json
{
  "agents": [
    {
      "persona_id": "mert",
      "persona_name": "Mert",
      "last_active": "2026-04-14T09:15:00",
      "message_count": 42,
      "last_obsidian_note": "2026-04-13 - eBay iPhone araştırması",
      "obsidian_note_count": 7
    }
  ],
  "active_persona": "seda",
  "generated_at": "2026-04-14T10:35:00"
}
```

---

## GET /api/pc/status

Anlık sistem durumu.

### Response 200
```json
{
  "cpu_percent": 23.5,
  "ram_used_mb": 8192,
  "ram_total_mb": 16384,
  "disk_used_gb": 245.3,
  "disk_total_gb": 500.0,
  "jarvis_processes": ["bridge.py", "hey_jarvis.py"],
  "ts": "2026-04-14T10:35:00"
}
```
