# Quickstart: Dijital Ajan V3 Persona Runtime

**Branch**: `004-dijital-ajan-v3-persona-swarm`

---

## 1. Configuration

`.env.example` icine eklenecek veya mevcut `.env` icinde doldurulacak:

```env
OBSIDIAN_VAULT_PATH=C:\Users\sergen\ObsidianVault
JARVIS_BACKEND_URL=http://127.0.0.1:8081
JARVIS_CHAT_PRIORITY=backend
```

Notlar:

- `OBSIDIAN_VAULT_PATH` opsiyoneldir; bos ise note write/recall komutlari fail-soft donecek.
- Persona color/voice/system prompt/sub_agents degerleri `config/agents.yaml` icinden gelir.

---

## 2. Start Runtime

Bridge + voice + hologram normal startup ile acilir:

```bash
python server/bridge.py
python hey_jarvis.py --text-mode
```

Desktop hologram ayrica Electron uygulamasi olarak acilabilir:

```bash
cd apps/desktop-hologram
npm start
```

---

## 3. Persona Smoke Tests

### US1 - Smart Persona Response

1. `Buse ile konus`
2. `landing page nasil olsun?`
3. Beklenen: pazarlama/CTA odakli yanit
4. `Seda ile konus`
5. `su Python kodunu incele`
6. Beklenen: teknik/debug odakli yanit

### US2 - Obsidian Second Brain

1. `Mert ile konus`
2. `bunu kaydet: Shopify rakip analizi notu`
3. Beklenen: `%OBSIDIAN_VAULT_PATH%/personas/mert/` altinda yeni markdown
4. `bu konuda ne biliyorsun?`
5. Beklenen: ayni klasorden ilgili note referansi

### US3 - Alt Ajan Swarm

1. `Seda ile konus`
2. `su repoyu analiz et ve ozetle`
3. Beklenen: step listesi, ardindan birlesik rapor
4. Bir step fail olursa beklenen: persona hangi adimda sorun oldugunu soyler

### US4 - Voice + Hologram

1. `Buse ile konus`
2. Beklenen: aktif voice `EmelNeural`, glow rengi `#ff69b4`
3. `Jarvis'e don`
4. Beklenen: default voice + default glow

---

## 4. Pytest

```bash
python -m pytest ^
  tests/test_persona_manager.py ^
  tests/test_bridge_persona_flow.py ^
  tests/test_persona_obsidian_skill.py ^
  tests/test_persona_swarm.py ^
  tests/test_voice_runtime_state.py -v --tb=short
```

---

## 5. Manual API Checks

Aktif persona:

```bash
curl http://127.0.0.1:8081/api/persona/active
```

Persona-aware chat:

```bash
curl -X POST http://127.0.0.1:8081/api/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\":\"Seda ile konus\"}"
```

---

## 6. Expected Artifacts

```text
state/
├── active_agent.json
├── agent_world.json
└── agent_memory/
    ├── seda/
    ├── mert/
    └── ...

%OBSIDIAN_VAULT_PATH%/
└── personas/
    ├── seda/
    ├── mert/
    └── ...
```
