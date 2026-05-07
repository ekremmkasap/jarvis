# Swarm Hologram — Design Doc
**Versiyon:** 1.0  
**Tarih:** 2026-04-12  
**Yazar:** Antigravity (AI Engineer)

---

## Genel Bakış

Jarvis Mark-XXXV swarm sisteminde 7 klon ajan (Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri) birbirleriyle Türkçe sesli diyalog kurar. Her ajanın ayrı bir Electron hologram penceresi vardır. Jarvis CEO orkestrasyonu altında `/swarm-konuş` komutuyla tetiklenir.

---

## Mimari

```
Tetikleyici (/swarm-konuş "konu")
         │
         ▼
  jarvis_ceo.py → start_dialogue(topic)
         │
         ▼
  conversation_engine.py → dialogue(topic, participants, rounds)
         │
         ├──► Her tur: Gemini Flash API → yanıt metni
         │
         ├──► edge_tts → tmp/[agent]_[turn].mp3
         │
         ├──► state/swarm_speaking_state.json güncelle
         │
         └──► server/logs/swarm_dialogue.jsonl kayıt
                    │
                    ▼
         bridge.py /api/swarm-status
                    │
                    ▼
         Electron swarm_windows.js → her 2sn poll
         Her ajan penceresi: orb pulse + alt yazı
```

---

## Ajan Profilleri

| Ajan     | Rol        | Renk    | Ses (edge_tts)       | Env Key          |
|----------|------------|---------|----------------------|------------------|
| seda     | Developer  | #00ff88 | tr-TR-EmelNeural     | GEMINI_KEY_SEDA  |
| mert     | Researcher | #ffdd00 | tr-TR-AhmetNeural    | GEMINI_KEY_MERT  |
| buse     | Marketer   | #ff69b4 | tr-TR-EmelNeural     | GEMINI_KEY_BUSE  |
| eren     | Analyst    | #ff8c00 | tr-TR-AhmetNeural    | GEMINI_KEY_EREN  |
| luna     | Security   | #9b59b6 | tr-TR-EmelNeural     | GEMINI_KEY_LUNA  |
| sabrican | Ops        | #95a5a6 | tr-TR-AhmetNeural    | GEMINI_KEY_SABRICAN |
| sabri    | Wildcard   | #e74c3c | tr-TR-AhmetNeural    | GEMINI_KEY_SABRI |

---

## Hologram Pencere Konumları

```
Sol taraf          Sağ taraf
─────────          ─────────
luna      y=0      seda      y=0
sabrican  y=290    mert      y=290
sabri     y=580    buse      y=580
                   eren      y=870
```

- Boyut: 200×280 px  
- transparent, frame:false, alwaysOnTop, skipTaskbar

---

## Swarm State Şeması

```json
{
  "speaking": "seda",
  "text": "Kodu inceliyorum...",
  "participants": ["seda", "mert", "buse"],
  "dialogue_active": true,
  "ceo_phase": "thinking",
  "updated_at": 1744500000.0
}
```

---

## API Yanıt Şeması — `/api/swarm-status`

```json
{
  "active": ["seda", "mert"],
  "active_agents": ["seda", "mert"],
  "speaking": "seda",
  "text": "Kodu inceliyorum...",
  "ceo_phase": "thinking",
  "dialogue_active": true,
  "participants": ["seda", "mert", "buse"],
  "slots": {"seda": "active", "mert": "active", ...},
  "timestamp": "2026-04-12T..."
}
```

---

## Diyalog Akışı

```
CEO → start_dialogue("konu", auto_select=True)
    → route_keywords(topic) → participants ['seda','mert','buse']
    → ConversationEngine.dialogue(topic, participants, rounds=2)
    → Tur 1:
        Buse konuşur → Gemini → metin → edge_tts → mp3 → çal
        state dosyasını güncelle → UI güncellenir
        Seda konuşur → ... → çal
        Mert konuşur → ... → çal
    → Tur 2: aynı, önceki konuşmalar context olarak eklenir
    → CEO özet yap
    → speaking: null, dialogue_active: false
```

---

## Güvenlik Kuralları

- API key loglara asla yazılmaz
- state/codex-accounts/ ve config/account_registry.json'a dokunulmaz
- Mevcut bridge.py endpointleri korunur
- Ses dosyaları tmp/ altında geçicidir; log'a sadece metin kaydedilir
