# Contract: Persona API Surface

## 1. GET /api/persona/active

Current active persona snapshot for voice UI and hologram renderer.

### Response 200

```json
{
  "id": "seda",
  "name": "Seda",
  "color": "#00ff88",
  "voice": "AhmetNeural",
  "role": "Kod/Debug/PR",
  "skills": ["code_review", "implementer"],
  "greeting": "Merhaba, Seda burada. Hangi kodla basliyoruz?",
  "activated_at": "2026-04-13T12:05:46.494547+00:00"
}
```

### Rules

- `id`, `name`, `color`, `voice` zorunlu
- `color` `#RRGGBB` formatinda
- endpoint aktif persona bulunamazsa Jarvis fallback payload dondurur

---

## 2. POST /api/chat

Normal chat endpoint; aktif persona varsa response persona prompt ve persona memory scope ile uretilir.

### Request

```json
{
  "message": "su Python kodunu incele"
}
```

### Response 200

```json
{
  "response": "[openrouter/deepseek-v3] Auth tarafinda null guard eksik gorunuyor.",
  "model": "openrouter/deepseek/deepseek-v3.2",
  "provider": "openrouter",
  "route": "default",
  "fallback_used": false,
  "attempts": []
}
```

### Persona-Aware Behavior

- Active persona Jarvis degilse:
  - response active persona system prompt'u ile uretilir
  - history active persona scope'undan okunur
  - history ayni persona scope'una yazilir
- Active persona Jarvis ise mevcut route behavior degismez

---

## 3. Runtime Files as Interface

Bu feature icin asagidaki dosyalar da interface surface kabul edilir:

- `state/active_agent.json`
- `state/agent_world.json`
- `state/agent_memory/<persona_id>/conversation_<chat_id>.jsonl`

Bu dosyalarin alan isimleri testlerle sabitlenmelidir.
