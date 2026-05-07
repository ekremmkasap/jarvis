# Data Model: MARK-XXXXVI — Jarvis Autonomous Command Layer

## Entities

### VoiceMessage
```python
{
  "telegram_file_id": str,       # Telegram file_id for download
  "duration_seconds": int,       # Ses süresi
  "transcription": str,          # STT çıktısı (Türkçe metin)
  "confidence": float | None,    # STT güven skoru (Groq destekliyorsa)
  "processed_at": str,           # ISO8601
  "chat_id": int                 # Hangi chat'ten geldi
}
```

### PCCommand
```python
{
  "command_key": str,            # "ekran-goruntusu" | "pc-durum" | "ac" | "dosya-gonder"
  "args": str | None,            # Ek argüman (uygulama adı, dosya yolu vb.)
  "whitelist_approved": bool,    # Whitelist kontrolü geçti mi
  "result": str,                 # İşlem sonucu (dosya path veya metin)
  "executed_at": str,            # ISO8601
  "persona_id": str,             # Kim tetikledi
  "chat_id": int
}
```
- `whitelist_approved: false` → eylem gerçekleşmez, audit log'a düşer

### IntentResult
```python
{
  "raw_message": str,
  "detected_intent": str,        # "research" | "code" | "social" | "aws" | "pc_control" | "wiki" | "memory" | "general"
  "target_persona": str | None,  # "mert" | "seda" | "buse" | "sabrican" | None
  "confidence": float,           # 0.0 - 1.0
  "auto_switched": bool,         # Persona değişti mi
  "ts": str
}
```
- `confidence < 0.7` → `target_persona = None`, mevcut persona korunur

### PCControlWhitelist (`config/pc_control_whitelist.yaml`)
```yaml
commands:
  ekran-goruntusu:
    action: screenshot
    args_required: false
  pc-durum:
    action: system_status
    args_required: false
  ac:
    action: open_app
    args_required: true
    allowed_apps: [chrome, vscode, notepad, explorer, spotify]
  dosya-gonder:
    action: send_file
    args_required: true
    allowed_dirs: ["C:/Users/sergen/Desktop", "C:/Users/sergen/Documents"]
  jarvis-baslat:
    action: start_jarvis
    args_required: false
  jarvis-kapat:
    action: stop_jarvis
    args_required: false
```

### ObsidianAutoEntry
```python
{
  "persona_id": str,
  "vault_folder": str,           # "personas/mert" | "personas/sabrican/actions"
  "title": str,                  # Otomatik üretilir: YYYY-MM-DD-{slug}
  "content_md": str,
  "created_at": str,
  "source_type": str             # "research" | "pc_action" | "conversation" | "wiki_sync"
}
```

### WikiAutoEntry
```python
{
  "file_path": str,              # "wiki/{slug}.md"
  "title": str,
  "content_md": str,
  "updated_at": str,
  "linked_personas": list[str],
  "source": str                  # "intent" | "manual_command"
}
```
- Her yazımdan sonra `wiki/index.md` ve `wiki/log.md` güncellenir
- `wiki/hot.md` günlük en son araştırma özetiyle güncellenir

### CodexPersonaSlotMap (`config/agents.yaml`'a eklenir)
```yaml
# Her persona'ya eklenecek alan:
codex_slot: forge  # forge | nexus | spark | shield | atlas
```
Mapping:
```
seda      → forge
mert      → nexus
sabrican  → nexus
buse      → spark
eren      → spark
luna      → shield
sabri     → atlas
```

### AgentMemorySnapshot (runtime, API response)
```python
{
  "persona_id": str,
  "persona_name": str,
  "recent_messages": [
    {"role": str, "content": str, "ts": str}
  ],                             # Son N mesaj (default 5)
  "last_active": str,
  "obsidian_note_count": int     # personas/{id}/ altında .md sayısı
}
```

## State Transitions

### VoiceMessage Flow
```
Telegram voice note
  → download .ogg
  → STT transcription
  → IntentResult
  → [auto_switch? → persona_switch]
  → normal message processing
  → TTS response
  → send_voice Telegram
```

### PCCommand Flow
```
Telegram /komut <args>
  → whitelist_check(command_key)
  → [approved] → execute action → result
  → [rejected] → "izin verilmiyor" mesajı
  → audit_log(PCCommand)
  → ObsidianAutoEntry (sadece approved)
```
