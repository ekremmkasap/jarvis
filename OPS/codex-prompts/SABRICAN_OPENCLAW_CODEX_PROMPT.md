# Sabrican + OpenClaw — Codex Subagent Entegrasyon Promptu

**Tarih:** 2026-04-14  
**Codex Sekmesi:** Sabrican (nexus slot)  
**Repo:** C:\Users\sergen\Desktop\jarvis-mission-control

---

## Bağlam

Jarvis Mission Control projesinde Sabrican, DevOps ve otomasyon direktörüdür.
OpenClaw bir secondary/helper runtime katmanıdır — canonical runtime değildir.
Bu promptu Codex'e ver; Sabrican altındaki subagent yapısını ve OpenClaw entegrasyonunu uygulasın.

---

## Görev

Aşağıdaki dosyaları önce oku, sonra değişiklik yap:

1. `server/openclaw_bridge.py` — OpenClaw bridge (mevcut)
2. `config/agents.yaml` — Sabrican persona (mevcut, canonical blok)
3. `server/persona_manager.py` — persona runtime (mevcut)
4. `tests/test_persona_manager.py` — mevcut testler

---

## Yapılacaklar (Sırayla)

### Adım 1 — OpenClaw Helper Subagent Sınıfı

`server/openclaw_bridge.py` içine şu subagent sınıflarını ekle:

```python
class GatewayHealthWatcher:
    """Sabrican alt ajanı: OpenClaw gateway sağlık kontrolü."""
    def check(self) -> dict:
        # openclaw_bridge.py:64 satırındaki health endpoint'i kullan
        # {"status": "ok"|"degraded"|"down", "latency_ms": int}

class ChannelDeliveryOperator:
    """Sabrican alt ajanı: Kanal teslimat yönetimi."""
    def deliver(self, channel: str, payload: dict) -> dict:
        # openclaw_bridge.py:78 satırındaki delivery mekanizması
        # {"delivered": bool, "channel": str, "error": str|None}

class AuthProfileSync:
    """Sabrican alt ajanı: Auth profil senkronizasyonu."""
    def sync(self, profile_id: str) -> dict:
        # openclaw_bridge.py:206 satırındaki sync mekanizması
        # {"synced": bool, "profile_id": str}
```

Kural: Bu sınıflar `helper_only=True` flag'i taşısın. bridge.py veya hey_jarvis.py'ı replace etmesin.

---

### Adım 2 — Sabrican Sistem Promptunu Doğrula

`config/agents.yaml` içinde Sabrican bloğunun şu field'ları içerdiğini doğrula:

```yaml
sabrican:
  system_prompt: |
    Sen Sabrican'sın. Ops direktörüsün. ...
  sub_agents: [deploy_runner, ci_monitor, service_watcher, obsidian_writer, openclaw_integrator]
  codex_subagents: [devops-engineer, deployment-engineer, sre-engineer, llm-architect]
  secondary_runtimes:
    - id: openclaw
      mode: helper_only
      canonical_runtime: false
      sub_agents: [gateway_health_watcher, channel_delivery_operator, auth_profile_sync]
```

Eksik field varsa ekle. Mevcut field'lara dokunma.

---

### Adım 3 — Sabrican Subagent Runner

`server/skills/sabrican_subagent_runner.py` dosyasını oluştur:

```python
"""
Sabrican alt ajan orkestrasyonu.
OpenClaw secondary layer dahil.
Sıralı çalışır, hata toleranslı.
"""

from server.openclaw_bridge import GatewayHealthWatcher, ChannelDeliveryOperator, AuthProfileSync

SUBAGENT_REGISTRY = {
    "deploy_runner": lambda payload: run_deploy(payload),
    "ci_monitor": lambda payload: check_ci(payload),
    "service_watcher": lambda payload: check_services(payload),
    "gateway_health_watcher": lambda payload: GatewayHealthWatcher().check(),
    "channel_delivery_operator": lambda payload: ChannelDeliveryOperator().deliver(**payload),
    "auth_profile_sync": lambda payload: AuthProfileSync().sync(payload.get("profile_id")),
}

def run_subagent_chain(task_list: list[dict]) -> list[dict]:
    """Sıralı çalıştır, hata toleranslı."""
    results = []
    for task in task_list:
        try:
            fn = SUBAGENT_REGISTRY.get(task["type"])
            result = fn(task.get("payload", {})) if fn else {"error": "unknown_agent"}
            results.append({"task": task["type"], "status": "done", "result": result})
        except Exception as e:
            results.append({"task": task["type"], "status": "failed", "error": str(e)})
    return results
```

---

### Adım 4 — Test

`tests/test_sabrican_subagents.py` dosyasını oluştur:

```python
"""Sabrican subagent ve OpenClaw layer testleri."""
import pytest
from unittest.mock import patch, MagicMock

def test_gateway_health_watcher_returns_status():
    from server.openclaw_bridge import GatewayHealthWatcher
    watcher = GatewayHealthWatcher()
    # Mock network call
    with patch.object(watcher, 'check', return_value={"status": "ok", "latency_ms": 12}):
        result = watcher.check()
    assert result["status"] in ("ok", "degraded", "down")

def test_sabrican_subagent_chain_tolerates_failure():
    from server.skills.sabrican_subagent_runner import run_subagent_chain
    tasks = [
        {"type": "service_watcher", "payload": {}},
        {"type": "unknown_agent", "payload": {}},  # Bu başarısız olmalı
    ]
    results = run_subagent_chain(tasks)
    assert any(r["status"] == "failed" for r in results)
    assert any(r["status"] == "done" for r in results)

def test_openclaw_is_helper_only():
    import yaml
    with open("config/agents.yaml") as f:
        config = yaml.safe_load(f)
    personas_list = [v for v in config.values() if isinstance(v, dict)]
    # Son personas bloğu
    sabrican = None
    for block in config.values():
        if isinstance(block, dict) and "sabrican" in block:
            sabrican = block["sabrican"]
    if sabrican and "secondary_runtimes" in sabrican:
        for rt in sabrican["secondary_runtimes"]:
            if rt.get("id") == "openclaw":
                assert rt.get("canonical_runtime") == False
                assert rt.get("mode") == "helper_only"
```

---

## Doğrulama

```bash
python -m py_compile server/openclaw_bridge.py server/skills/sabrican_subagent_runner.py
python -m pytest tests/test_sabrican_subagents.py tests/test_persona_manager.py -q
```

Beklenen: Tüm testler geçer, import kırığı yok.

---

## Değiştirilmeyecekler

- `server/bridge.py` — bu turda dokunma
- `hey_jarvis.py` — bu turda dokunma
- `server/persona_manager.py` core mantığı — sadece yeni field tolere edilir
- `state/active_agent.json` — persona_manager sorumluluğu, Sabrican dokunmaz

---

## Teslim Formatı

Değişen dosyalar + ne yapıldı + doğrulama komutu + residual risk.
