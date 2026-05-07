# Data Model: Persona Switching

## Entities

### ActivePersona (`state/active_agent.json`)
| Alan | Tip | Açıklama |
|------|-----|---------|
| id | string | Persona slug: "seda", "jarvis" |
| name | string | Görünen isim: "Seda" |
| color | string | Hologram hex rengi: "#00ff88" |
| voice | string | TTS sesi: "AhmetNeural", "EmelNeural" |
| role | string | Kısa görev tanımı |
| skills | list[str] | Persona'nın yetenekleri |
| greeting | string | İlk karşılama metni (TTS'e okunur) |
| activated_at | float | Unix timestamp |

### PersonaConfig (`config/agents.yaml` → `personas:` bölümü)
| Alan | Tip | Açıklama |
|------|-----|---------|
| name | string | Görünen isim |
| role | string | Görev tanımı |
| color | string | Hex renk kodu |
| voice | string | TTS ses motoru |
| skills | list[str] | Yetenek etiketleri |
| greeting | string | Karşılama cümlesi |
| triggers | list[str] | Trigger kelimeleri (lower-case) |

## State Transitions

```
Kullanıcı mesajı
    → detect_switch_from_text(text) → None veya persona_id
    → switch_persona(persona_id)
        → config'den persona profilini yükle
        → state/active_agent.json'ı güncelle
        → {"ok": True, "name": ..., "greeting": ..., "color": ...} döndür
    → bridge.py → TTS greeting
    → bridge.py → Telegram yanıtı
```

## Validation Rules
- `id` boş olamaz, lowercase, alfanumerik
- `color` `#` ile başlamalı, 7 karakter
- `greeting` boş olamaz
- Bilinmeyen persona_id → `{"ok": False, "error": "..."}`
