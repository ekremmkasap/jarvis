"""
Jarvis Corp — Agent State Tracker
Tüm agentların gerçek zamanlı durumunu izler ve raporlar.
"""
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE_DIR   = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR.parent / "config"
STATE_FILE = BASE_DIR / "logs" / "agent_state.json"
HIERARCHY_PATH = CONFIG_DIR / "corporate_hierarchy.json"
BYPASS_PORT = int(os.environ.get("BYPASS_PORT", 7090))


def _load_hierarchy():
    with open(HIERARCHY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"agents": {}, "updated": None}


def _save_state(state):
    STATE_FILE.parent.mkdir(exist_ok=True)
    state["updated"] = datetime.now().isoformat()
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _check_bypass():
    try:
        url = f"http://localhost:{BYPASS_PORT}/health"
        with urllib.request.urlopen(url, timeout=3) as r:
            return json.loads(r.read())
    except Exception:
        return {"ok": False, "mode": "offline"}


def refresh_state():
    """Tüm agentların durumunu güncelle ve kaydet."""
    data  = _load_hierarchy()
    state = _load_state()
    bypass = _check_bypass()

    for agent in data["hierarchy"]:
        aid = agent["id"]
        prev = state["agents"].get(aid, {})

        # Codex hesaplarını kontrol et
        if agent.get("provider") == "openai-codex":
            email = os.environ.get(agent.get("email_env", ""), "")
            new_status = "ready" if email else "env_missing"
        elif agent["tier"] == "patron":
            new_status = "active"
        elif agent["tier"] == "worker":
            new_status = "standby"
        else:
            new_status = agent.get("status", "unknown")

        state["agents"][aid] = {
            "id": aid,
            "label": agent["label"],
            "tier": agent["tier"],
            "level": agent["level"],
            "department": agent.get("department", ""),
            "status": new_status,
            "provider": agent.get("provider", ""),
            "model": agent.get("model", ""),
            "current_task": prev.get("current_task"),
            "last_active": prev.get("last_active"),
            "tasks_done": prev.get("tasks_done", 0),
            "errors": prev.get("errors", 0)
        }

    state["bypass"] = {
        "ok": bypass.get("ok", False),
        "mode": bypass.get("mode", "offline"),
        "uptime": bypass.get("uptime", 0)
    }
    _save_state(state)
    return state


def set_agent_task(agent_id, task, status="working"):
    """Bir agent'a aktif görev ata."""
    state = _load_state()
    if agent_id not in state["agents"]:
        state["agents"][agent_id] = {}
    state["agents"][agent_id]["current_task"] = task
    state["agents"][agent_id]["status"] = status
    state["agents"][agent_id]["last_active"] = datetime.now().isoformat()
    _save_state(state)


def complete_agent_task(agent_id, success=True):
    """Agent görevini tamamlandı olarak işaretle."""
    state = _load_state()
    if agent_id in state["agents"]:
        a = state["agents"][agent_id]
        a["current_task"] = None
        a["status"] = "idle"
        a["last_active"] = datetime.now().isoformat()
        if success:
            a["tasks_done"] = a.get("tasks_done", 0) + 1
        else:
            a["errors"] = a.get("errors", 0) + 1
    _save_state(state)


def analyze(call_llm=None):
    state = refresh_state()
    return {
        "report": get_live_board(),
        "score": 85,
        "error": None,
        "state": state
    }


def get_live_board():
    """Telegram'a gönderilecek canlı agent board."""
    state = refresh_state()
    agents = state.get("agents", {})
    bypass = state.get("bypass", {})
    updated = state.get("updated", "?")[:19]

    tier_order = ["patron", "owner", "ceo", "manager", "deputy", "operator", "worker"]
    tier_labels = {
        "patron":   "👑 PATRON",
        "owner":    "💎 SAHİPLER",
        "ceo":      "🎖  CEO",
        "manager":  "🗂  MÜDÜRLER",
        "deputy":   "📋 YARDIMCILAR",
        "operator": "⚙️  OPERATÖRLER",
        "worker":   "🤖 WORKERS"
    }

    status_icons = {
        "active": "🟢", "idle": "🟢", "ready": "🟢",
        "working": "🔵", "pending_login": "🟡",
        "standby": "⚪", "quota_exceeded": "🔴",
        "env_missing": "🟠", "offline": "🔴", "unknown": "⚪"
    }

    lines = [
        "🏢 **Jarvis Corp — Live Board**",
        f"🕐 {updated}",
        f"🔧 Bypass: {'🟢' if bypass.get('ok') else '🔴'} `{bypass.get('mode','?')}`",
        ""
    ]

    # Tier gruplandır
    by_tier = {}
    for a in agents.values():
        t = a.get("tier", "?")
        by_tier.setdefault(t, []).append(a)

    for tier in tier_order:
        group = by_tier.get(tier, [])
        if not group:
            continue
        lines.append(f"**{tier_labels.get(tier, tier.upper())}**")
        for a in sorted(group, key=lambda x: x.get("level", 9)):
            icon = status_icons.get(a.get("status", ""), "⚪")
            task = a.get("current_task")
            task_str = f" → `{task[:40]}`" if task else ""
            done = a.get("tasks_done", 0)
            done_str = f" ✓{done}" if done else ""
            lines.append(f"  {icon} **{a['label']}**{task_str}{done_str}")
        lines.append("")

    # Özet
    total = len(agents)
    working = sum(1 for a in agents.values() if a.get("status") == "working")
    ready   = sum(1 for a in agents.values() if a.get("status") in ("active", "idle", "ready"))
    lines.append(f"📊 Toplam: {total} | Aktif: {ready} | Çalışıyor: {working}")

    return "\n".join(lines)


def get_owner_status():
    """agent_07 ve agent_08 paralel görünüm."""
    state = refresh_state()
    agents = state.get("agents", {})
    bypass = state.get("bypass", {})

    lines = ["💎 **Şirket Sahipleri — Paralel Durum**", ""]

    for aid in ["agent_07_owner_seda", "agent_08_owner_bdolu"]:
        a = agents.get(aid, {})
        if not a:
            lines.append(f"⚠️ `{aid}` state'de yok")
            continue
        icon = {"active":"🟢","ready":"🟢","working":"🔵","pending_login":"🟡"}.get(a.get("status",""), "⚪")
        task = a.get("current_task", "—")
        done = a.get("tasks_done", 0)
        errs = a.get("errors", 0)
        last = (a.get("last_active") or "—")[:19]
        lines.append(f"{icon} **{a['label']}**")
        lines.append(f"  Durum: `{a.get('status','?')}`")
        lines.append(f"  Görev: {task}")
        lines.append(f"  Tamamlanan: {done} | Hata: {errs}")
        lines.append(f"  Son aktivite: {last}")
        lines.append("")

    lines.append(f"🔧 Bypass Core: {'🟢 aktif' if bypass.get('ok') else '🔴 offline'} | mod: `{bypass.get('mode','?')}`")
    return "\n".join(lines)
