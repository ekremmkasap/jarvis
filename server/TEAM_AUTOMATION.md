# Team Automation

Jarvis artik manuel sekme kopyalama yerine otomatik bir uzman takim akisi kullanabilir.

## Akis
- `Agent OS Runtime` istegi route eder ve ilgili departmanlari secer.
- `Planner` hedefi plan, acceptance criteria ve risklere boler.
- `Builder` uygulanabilir artifact uretir.
- `Guard` artifact'i review eder.
- `Research` sadece gerekli gorevlerde ek baglam saglar.
- `Synthesizer` final raporu tek yerde toplar.

## Girdiler
- `/team <hedef>` dogrudan team orchestrator calistirir.
- `/task <hedef>` artik once team orchestrator dener, gerekirse eski `agent_loop` fallback olur.
- Dogal dilde karmaşık kod ve tasarim istekleri otomatik olarak team moduna dusebilir.

## Canli Calistirma
- Foreground: `python server/bridge.py`
- Detached Windows baslatma: `start_jarvis_detached.bat`
- Web UI: `http://127.0.0.1:8081`
- Team audit izle: `Get-Content .\server\logs\team_audit.jsonl -Wait`

## Dosyalar
- `server/agent_os/runtime.py`
- `server/agent_workspace/departments/*`
- `server/core/team_orchestrator.py`
- `server/agents/planner_agent.py`
- `server/agents/builder_agent.py`
- `server/agents/guard_agent.py`
- `server/agents/research_agent.py`
- `server/agents/synthesizer_agent.py`
- `server/config/team_config.json`

## Kayitlar
- Audit: `server/logs/team_audit.jsonl`
- Working memory: `server/memory/working_memory/team_tasks.jsonl`

## Kurallar
- Guard `critical` veya `high` bulursa gorev otomatik onay almaz.
- Builder en fazla `max_review_loops` kadar duzeltme turuna girer.
- Research her istekte degil, sadece config'teki kurallara gore calisir.
