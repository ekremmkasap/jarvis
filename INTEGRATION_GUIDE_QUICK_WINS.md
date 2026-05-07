# Claude Code → Jarvis Integration: Şimdi Implement Et

## Entegrasyon Talimatları

İmplementasyon yapılı. Şimdi **3 file'ı bridge.py ve master_launcher.py'a entegre et**:

### Dosyalar

1. **`server/services/skill_loader.py`** — Dinamik `.md`-tabanlı skill loading
2. **`server/services/coordinator_mode.py`** — CEO/worker swarm mode
3. **`server/services/memory_consolidation.py`** — Session-between learning

---

## STEP 1: bridge.py'da Skill Loader Entegrasyonu

**Lokasyon**: `server/bridge.py` (top'ında import'lar arasına ekle)

```python
# Line ~30 (mevcut imports sonrasında)
from server.services.skill_loader import load_skills_from_directory, watch_skills_directory, SkillRegistry

# Global registry
_skill_registry = None

def initialize_skills():
    """Bridge startup'ında skill'leri yükle"""
    global _skill_registry
    skills_dir = os.path.join(os.path.dirname(__file__), 'skills')
    _skill_registry = load_skills_from_directory(skills_dir, ignore_errors=True)
    
    # Opsiyonel: hot-reload için directory watched'ini başlat
    if os.getenv('JARVIS_SKILL_HOTRELOAD', 'false').lower() == 'true':
        watch_skills_directory(skills_dir, _skill_registry)
    
    return _skill_registry
```

**FastAPI app'ında (startup event):**

```python
@app.on_event("startup")
async def startup_event():
    """Bridge startup"""
    # ... existing startup code ...
    
    # Skill loader entegrasyonu
    initialize_skills()
    logger.info("✓ Skill loader initialized")
```

**Skill çalıştırırken (existing `/run-skill` endpoint veya bridge logic'te):**

```python
async def run_skill(skill_name: str, params: dict) -> str:
    """
    Dynamic skill execution via registry
    """
    global _skill_registry
    
    if _skill_registry is None:
        raise RuntimeError("Skill registry not initialized")
    
    skill = _skill_registry.get(skill_name)
    if not skill:
        raise ValueError(f"Skill not found: {skill_name}")
    
    try:
        result = skill.execute_fn(**params)
        return result
    except Exception as e:
        logger.error(f"Skill execution failed: {e}")
        raise
```

---

## STEP 2: bridge.py'da Coordinator Mode Entegrasyonu

**Lokasyon**: `server/bridge.py`

```python
# Line ~30 (imports)
from server.services.coordinator_mode import (
    is_coordinator_mode,
    load_coordinator_config,
    get_available_tools,
    validate_tool_access,
    get_coordinator_system_context
)

# Global config
_coordinator_config = None

def initialize_coordinator():
    """Startup'da coordinator mode'u load et"""
    global _coordinator_config
    
    config_file = os.path.join(
        os.path.dirname(__file__),
        'config',
        'coordinator_config.json'
    )
    
    if os.path.exists(config_file):
        _coordinator_config = load_coordinator_config(config_file)
        logger.info(f"✓ Coordinator mode: {'ENABLED' if _coordinator_config.enabled else 'DISABLED'}")
    else:
        logger.warning(f"Coordinator config not found: {config_file}")

# Startup'da call et
@app.on_event("startup")
async def startup_event():
    # ... existing code ...
    initialize_coordinator()
```

**Tool access validation (tool çalıştırmadan önce):**

```python
async def execute_tool(agent_id: str, tool_name: str, tool_params: dict) -> Any:
    """
    Tool execution with coordinator mode validation
    """
    # Coordinator mode'da access control
    if is_coordinator_mode():
        is_allowed, error_msg = validate_tool_access(agent_id, tool_name, _coordinator_config)
        if not is_allowed:
            raise PermissionError(error_msg)
    
    # ... existing tool execution code ...
    return result
```

**System prompt'a coordinator context'i ekle:**

```python
def get_system_prompt(agent_id: str) -> str:
    """
    Build system prompt with coordinator context
    """
    base_prompt = """You are Jarvis, a Turkish AI assistant..."""
    
    # Coordinator context ekle
    coordinator_context = get_coordinator_system_context(agent_id, _coordinator_config)
    
    return base_prompt + "\n" + coordinator_context if coordinator_context else base_prompt
```

---

## STEP 3: master_launcher.py'da Memory Consolidation

**Lokasyon**: `master_launcher.py`

```python
# imports (top'ta)
from server.services.memory_consolidation import ConsolidationScheduler

# Global scheduler
_consolidation_scheduler = None

def setup_memory_consolidation():
    """Memory consolidation background job'unu setup et"""
    global _consolidation_scheduler
    
    db_path = 'state/Jarvis.db'  
    memory_dir = 'state/agent_memory/consolidated'
    
    _consolidation_scheduler = ConsolidationScheduler(
        db_path=db_path,
        memory_dir=memory_dir,
        check_interval_seconds=3600  # Her saat check et
    )
    
    try:
        _consolidation_scheduler.start_background_scheduler()
        logger.info("✓ Memory consolidation scheduler started")
    except ImportError:
        logger.warning("APScheduler not found, memory consolidation disabled")
        logger.info("  Install with: pip install apscheduler")
        return False
    
    return True


# main() veya startup logic'inde call et
def main():
    """Main launcher"""
    # ... existing code ...
    
    # Memory consolidation setup
    setup_memory_consolidation()
    
    # ... rest of setup ...
```

---

## STEP 4: Example Skill Dosyası Oluştur

Test etmek için örnek skill:

**Dosya**: `server/skills/hello_world.md`

```markdown
---
name: hello_world
description: Basit merhaba dünya skill'i
params:
  name: str = "World"
returns: str
---

```python
def execute(name: str = "World") -> str:
    return f"Hello, {name}! 🎉"
```
```

**Dosya**: `server/skills/summarize_text.md`

```markdown
---
name: summarize_text
description: Metni 3 cümleye öztle
params:
  text: str
  max_sentences: int = 3
returns: str
---

```python
def execute(text: str, max_sentences: int = 3) -> str:
    sentences = text.split('.')
    summary = '.'.join(sentences[:max_sentences])
    return summary + '.'
```
```

---

## STEP 5: Coordinator Config Oluştur

**Dosya**: `server/config/coordinator_config.json`

```json
{
  "enabled": true,
  "ceo_agent_id": "sabri",
  "team": [
    {
      "persona_id": "seda",
      "agent_type": "executor",
      "domain": "dev",
      "tools": ["file_read", "file_write", "bash_execute", "code_review", "test_run"]
    },
    {
      "persona_id": "mert",
      "agent_type": "researcher",
      "domain": "research",
      "tools": ["web_search", "data_fetch", "rss_parse"]
    },
    {
      "persona_id": "eren",
      "agent_type": "executor",
      "domain": "media",
      "tools": ["video_download", "media_process", "file_write"]
    },
    {
      "persona_id": "sabri",
      "agent_type": "coordinator",
      "domain": "strategy",
      "tools": []
    }
  ]
}
```

---

## STEP 6: Environment Variables

`.env` veya `.env.local`'e ekle:

```bash
# Coordinator mode aktif et
JARVIS_COORDINATOR_MODE=true

# Skill hot-reload (development)
JARVIS_SKILL_HOTRELOAD=false

# Memory consolidation threshold
JARVIS_CONSOLIDATION_THRESHOLD=10
JARVIS_CONSOLIDATION_INTERVAL_HOURS=6
```

---

## Test Checklist

- [ ] `pip install pyyaml` (skill_loader.py için)
- [ ] `pip install apscheduler` (memory_consolidation için)
- [ ] `server/services/skill_loader.py` → production
- [ ] `server/services/coordinator_mode.py` → production
- [ ] `server/services/memory_consolidation.py` → production
- [ ] `server/config/coordinator_config.json` oluştur
- [ ] Example skill'ler (`hello_world.md`, `summarize_text.md`) test et
- [ ] bridge.py integration 3 kısım ekle
- [ ] master_launcher.py integration ekle
- [ ] `JARVIS_COORDINATOR_MODE=true` set et
- [ ] Bridge başlat ve logs'u kontrol et:
  - "✓ Skill loader initialized"
  - "✓ Coordinator mode: ENABLED"
  - "✓ Memory consolidation scheduler started"

---

## Verification Commands

```bash
# Test skill loading
curl -X POST http://localhost:8081/run-skill \
  -H "Content-Type: application/json" \
  -d '{"skill": "hello_world", "params": {"name": "Jarvis"}}'

# Expected: { "result": "Hello, Jarvis! 🎉" }

# Test coordinator mode access
curl -X GET http://localhost:8081/available-tools?agent_id=seda

# Expected: Tools limited to executor set (file_read, file_write, bash_execute, etc.)
```

---

## Sonraki Adımlar (Phase 2)

- Skill versioning (git-backed)
- MCP multi-transport integration
- Distributed agent spawning (with Codex swarm)
- Persistent prompt caching

---

**Status**: ✅ READY FOR IMPLEMENTATION

Üç file production'da. Integration guide complete. Start with step 1!

