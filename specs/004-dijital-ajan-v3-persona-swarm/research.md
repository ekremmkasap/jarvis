# Research: Dijital Ajan V3 — Persona Swarm

## Decision 1: System Prompt Injection Strategy
- **Decision**: Active persona system_prompt alanı LLM çağrısının başına enjekte edilir. Model değişmez.
- **Rationale**: En minimal değişiklik. `server/bridge.py` içindeki LLM çağrı noktasına tek bir `persona_manager.get_active_persona()` çağrısı yeterli.
- **Alternatives considered**: Ayrı model fine-tuning (gereksiz maliyet), persona per-model routing (scope dışı).

## Decision 2: Obsidian Entegrasyonu
- **Decision**: Doğrudan dosya sistemi. `OBSIDIAN_VAULT_PATH` env'den alınır. `personas/<persona_id>/` klasörüne markdown yazar.
- **Rationale**: Obsidian API yok. `server/skills/persona_obsidian_skill.py` zaten mevcut ve çalışır durumda.
- **Alternatives considered**: Obsidian REST plugin (ek kurulum gerektirir, kırılgan).

## Decision 3: Alt Ajan Swarm Çalışma Modu
- **Decision**: Aynı process içinde sıralı çalışır. Bağımsız adımlar ThreadPoolExecutor ile paralel.
- **Rationale**: `server/services/persona_swarm.py` zaten mevcut, ThreadPoolExecutor ile paralel destek var.
- **Alternatives considered**: Ayrı process/worker (scope dışı, Faz 4 işi).

## Decision 4: Persona Memory İzolasyonu
- **Decision**: `state/agent_memory/<persona_id>/conversation_<chat_id>.jsonl` — her persona ayrı JSONL.
- **Rationale**: `server/persona_memory.py` zaten mevcut ve bu yapıyı kullanıyor.

## Decision 5: Voice Override
- **Decision**: `hey_jarvis.py` içinde `persona_manager.get_active_persona()["voice"]` çağrısı. Greeting TTS ile çalınır, switch sırasında bir kez tetiklenir (spam yok).

## Decision 6: Hologram Renk Geçişi
- **Decision**: `renderer.js` 3 saniyede bir `/api/persona/active` poll eder (zaten yapıyor). `color` field CSS variable olarak glow'a uygulanır. 0.6s CSS transition.

## Mevcut Durum Analizi

| Bileşen | Durum | Aksiyon |
|---------|-------|---------|
| `server/persona_manager.py` | ✅ Mevcut | system_prompt/sub_agents load eklenecek |
| `server/persona_memory.py` | ✅ Mevcut | Kullanıma hazır |
| `server/skills/persona_obsidian_skill.py` | ✅ Mevcut | Bridge command bağlantısı eklenecek |
| `server/services/persona_swarm.py` | ✅ Mevcut | Real executor'lar bağlanacak |
| `config/agents.yaml` personas | ⚠️ Eksik | `system_prompt`, `sub_agents`, `obsidian_folder` eklenecek |
| `/api/persona/active` endpoint | ✅ Mevcut | Payload `system_prompt` hariç genişletilecek |
| LLM çağrısında system_prompt inject | ❌ Yok | `server/bridge.py` veya `server/model_router.py`'ye eklenecek |
| `hey_jarvis.py` voice override | ⚠️ Kısmi | Greeting + switch hook eklenecek |
| `renderer.js` renk geçişi | ⚠️ Kısmi | CSS transition + color variable eklenecek |
| `OBSIDIAN_VAULT_PATH` | ❌ Kontrol gerekli | `.env.example`'e eklenmeli |
