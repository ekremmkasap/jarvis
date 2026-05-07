# Research: Persona Switching — Phase 0

## Bulgular

### 1. bridge.py import zinciri
- `_switch_persona_for_chat()` → `from persona_manager import switch_persona` → HATA: modül yok
- `detect_switch_from_text()` → bridge.py içinde mi tanımlı? Grep sonucu: satır 3625'te çağrılıyor, tanımı başka yerde olmalı — `persona_manager.py`'de tanımlanacak
- Fix: `server/persona_manager.py` oluşturulunca her iki import da çalışır

### 2. State yönetimi
- `state/active_agent.json` yok → oluşturulacak, default Jarvis
- Mevcut `STATE = RuntimeState(...)` bridge.py içinde, `ACTIVE_AGENTS` dict per-chat Telegram session'ı — bunlar ayrı, çakışma yok

### 3. Türkçe trigger detection
- "Seda ile konuş", "Seda'ya sor", "Sedaya geç", "Seda'yı çağır" — çekim ekleri değişiyor
- Karar: config'deki `triggers` listesi + `startswith` + `in` kontrolü — regex gerekmez

### 4. Hologram renk güncellemesi
- hologram `/api/desktop-assistant` poll ediyor ve `agent` alanına bakıyor
- `active_agent.json`'daki `color` bridge endpoint'e enjekte edilebilir — Faz 2 işi, şimdi değil

## Kararlar

| Karar | Seçim | Alternatif |
|-------|-------|-----------|
| Persona config lokasyonu | `config/agents.yaml` `personas:` bölümü | Ayrı `config/personas.yaml` — gereksiz dosya |
| Trigger matching | triggers listesi + lower() contains | Spacy/NLP — overkill |
| State persistence | JSON dosya | SQLite — overkill tek değer için |
| Hologram renk | Sonraya bırakıldı (Faz 2) | Şimdi yapılabilir ama scope dışı |
