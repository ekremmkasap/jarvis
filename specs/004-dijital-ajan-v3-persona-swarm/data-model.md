# Data Model: 7 Persona Swarm

## Entities

### PersonaProfile
```python
{
  "id": str,                    # "seda", "mert", ...
  "name": str,                  # "Seda"
  "role": str,                  # "kod/debug/PR uzmanı"
  "color": str,                 # "#00ff88"
  "voice": str,                 # "AhmetNeural"
  "skills": list[str],
  "greeting": str,
  "triggers": list[str],
  "system_prompt": str,         # Tam karakter promptu
  "sub_agents": list[str],
  "codex_subagents": list[str],
  "skill_surfaces": list[str],
  "handoff_targets": list[str],
  "tone_guide": {"formality": str, "technical_depth": str, "emoji_use": bool},
  "domain_limits": {"restricted_topics": list[str], "fallback_persona": str, "lab_only": bool},
  "obsidian_folder": str
}
```

### PersonaMemory
```python
# state/agent_memory/<persona_id>/memory.json
{
  "persona_id": str,
  "messages": [{"role": str, "content": str, "ts": str}],
  "last_active": str
}
```

### ObsidianNote
```python
# <OBSIDIAN_VAULT_PATH>/personas/<persona_id>/<title>.md
{
  "persona_id": str,
  "title": str,
  "content": str,   # Markdown
  "created_at": str,
  "tags": list[str]
}
```

### SubAgentTask
```python
{
  "id": str,           # uuid
  "type": str,         # "web_search" | "code_analyzer" | "file_reader" | ...
  "payload": dict,
  "status": str,       # "pending" | "running" | "done" | "failed"
  "result": any,
  "created_by_persona": str,
  "created_at": str
}
```

### ActivePersonaState
```python
# state/active_agent.json
{
  "id": str,
  "name": str,
  "color": str,
  "voice": str,
  "activated_at": str
}
```

## State Transitions

```
"Mert'e yönlendir"
  → persona_manager.switch_persona("mert")
  → state/active_agent.json güncellenir
  → hey_jarvis.py AhmetNeural yükler
  → hologram #ffdd00'a geçer (0.6s transition)
  → "Efendim Ekrem, ..." Mert greeting TTS
```

## Sub-Agent Orkestrasyonu

```
Persona 3+ adımlı görev alır
  → subagent_runner.run([T1, T2, T3])
  → Sıralı: T1 → T2 → T3
  → Hata: persona raporlar, sonraki adım devam eder
  → Tüm sonuçlar persona'ya döner → özetler
  → obsidian_writer → personas/<id>/ altına yazar
```

## Sub-Agent Tip Kataloğu

| Tip | Kaynak Dosya | Sahibi |
|-----|-------------|--------|
| `code_analyzer` | `server/skills/` | Seda, Luna |
| `file_reader` | bridge.py file endpoint | Seda, Eren, Luna |
| `test_runner` | pytest subprocess | Seda |
| `web_search` | `server/skills/web_search_skill.py` | Mert, Buse |
| `price_tracker` | `server/skills/ebay_research.py` | Mert |
| `market_analyzer` | `server/skills/research_scheduler_skill.py` | Mert |
| `instagram_poster` | `server/skills/instagram_skill.py` | Buse |
| `content_writer` | LLM direct | Buse, Sabri |
| `seo_checker` | web_search_skill pattern | Buse |
| `campaign_designer` | LLM (Gemini Pro) | Sabri |
| `brand_writer` | LLM (Groq llama-3.3-70b) | Sabri |
| `offer_builder` | LLM | Sabri |
| `youtube_analyzer` | web_search + YouTube API | Eren |
| `kpi_tracker` | ebay_research pattern | Eren |
| `dashboard_builder` | LLM + veri | Eren |
| `log_scanner` | `server/logs/` + regex | Luna |
| `vuln_checker` | OWASP + LLM | Luna |
| `code_auditor` | read-only code review | Luna |
| `deploy_runner` | master_launcher pattern | Sabrican |
| `ci_monitor` | GitHub API | Sabrican |
| `service_watcher` | `/health` endpoint | Sabrican |
| `gateway_health_watcher` | `openclaw_bridge.py:64` | Sabrican/OpenClaw |
| `channel_delivery_operator` | `openclaw_bridge.py:78` | Sabrican/OpenClaw |
| `auth_profile_sync` | `openclaw_bridge.py:206` | Sabrican/OpenClaw |
| `obsidian_writer` | `server/skills/obsidian_sync_skill.py` | Tüm personalar |
