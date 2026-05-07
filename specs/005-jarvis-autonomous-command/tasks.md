# Tasks

## Faz 6: Agent hafiza paneli + API
- [x] `server/skills/agent_memory_skill.py` persona memory kayitlarini JSONL'den toparlayan, Obsidian not istatistiklerini hesaplayan ve `/hafiza` ile `/ajanlarin-ozeti` metinlerini ureten yuzeyi sagliyor.
- [x] `server/bridge.py` append-only autonomous command layer icinde `GET /api/persona/{id}/memory`, `GET /api/agents/summary`, `GET /api/pc/status`, `/hafiza` ve `/ajanlarin-ozeti` entegrasyonlari mevcut.
- [x] `apps/web-ui/src/lib/bridgeProxy.ts` web UI tarafinda bridge JSON proxy helper'ini sagliyor.
- [x] `apps/web-ui/src/app/api/agents/summary/route.ts` bridge uzerinden ajan ozetini Next API route olarak yayinliyor.
- [x] `apps/web-ui/src/app/api/persona/[id]/memory/route.ts` aktif veya secili persona icin memory istegini Next API route olarak yayinliyor.
- [x] `apps/web-ui/src/app/api/pc/status/route.ts` PC durumunu bridge proxy uzerinden UI'a aktariyor.
- [x] `apps/web-ui/src/components/AgentMemoryPanel.tsx` ajan ozeti, aktif persona hafizasi ve PC durumunu 3 saniyelik polling ile gosteren paneli sagliyor.
- [x] `apps/web-ui/src/components/MissionControlDashboard.tsx` operator dashboard icine `AgentMemoryPanel` yerlesimini ekliyor.
- [x] `tests/test_agent_memory_skill.py` hafiza snapshot ve summary yuzeylerini kapsiyor.

## Verification so far
- [x] `tests/test_telegram_voice.py`
- [x] `tests/test_pc_control_gateway.py`
- [x] `tests/test_intent_persona_router.py`
- [x] `tests/test_obsidian_auto_writer.py`
- [x] `tests/test_wiki_auto_writer.py`
- [x] `tests/test_agent_memory_skill.py`
