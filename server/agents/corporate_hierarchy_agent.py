"""
Jarvis Corporate Hierarchy Agent
Şirket hiyerarşisini yönetir, agent durumlarını raporlar, görev delegasyonu yapar.
"""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE_DIR   = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR.parent / "config"
HIERARCHY_PATH = CONFIG_DIR / "corporate_hierarchy.json"
BYPASS_PORT = int(os.environ.get("BYPASS_PORT", 7090))


def _load_hierarchy():
    with open(HIERARCHY_PATH, encoding="utf-8") as f:
        return json.load(f)


def _bypass_status():
    try:
        url = f"http://localhost:{BYPASS_PORT}/health"
        with urllib.request.urlopen(url, timeout=3) as r:
            return json.loads(r.read())
    except Exception:
        return {"ok": False}


def analyze(call_llm=None):
    """Hiyerarşi özeti + aktif agent sayısı."""
    data = _load_hierarchy()
    agents = data["hierarchy"]
    tiers = {}
    for a in agents:
        t = a["tier"]
        tiers[t] = tiers.get(t, 0) + 1

    return {
        "report": get_org_chart(),
        "score": 90,
        "error": None,
        "total_agents": len(agents),
        "tiers": tiers
    }


def get_org_chart():
    data = _load_hierarchy()
    agents = data["hierarchy"]
    depts  = data.get("departments", {})
    lines = [f"🏢 **{data['company']} — Org Chart**", ""]

    tier_order = ["patron", "owner", "ceo", "manager", "deputy", "operator", "worker"]
    tier_labels = {
        "patron":   "👑 PATRON",
        "owner":    "💎 ŞİRKET SAHİBİ",
        "ceo":      "🎖  CEO",
        "manager":  "🗂  MÜDÜR",
        "deputy":   "📋 MÜDÜR YARDIMCISI",
        "operator": "⚙️  OPERATÖR",
        "worker":   "🤖 WORKER HAVUZU"
    }

    for tier in tier_order:
        tier_agents = [a for a in agents if a["tier"] == tier]
        if not tier_agents:
            continue
        lines.append(f"**{tier_labels.get(tier, tier.upper())}**")
        for a in tier_agents:
            dept = a.get("department", "")
            dept_info = depts.get(dept, {})
            emoji = dept_info.get("emoji", "•")
            status = a.get("status", "?")
            status_icon = {"active": "🟢", "pending_login": "🟡", "quota_exceeded": "🔴", "dynamic": "🔵"}.get(status, "⚪")
            human_tag = " 👤" if a.get("human") else ""
            lines.append(f"  {status_icon} {emoji} `{a['id']}` — {a['label']}{human_tag}")
        lines.append("")

    return "\n".join(lines)


def get_agent_detail(agent_id):
    data = _load_hierarchy()
    for a in data["hierarchy"]:
        if a["id"] == agent_id or a["label"].lower() == agent_id.lower():
            depts = data.get("departments", {})
            dept_info = depts.get(a.get("department", ""), {})
            lines = [
                f"**{dept_info.get('emoji','🤖')} {a['title']}**",
                f"ID: `{a['id']}`",
                f"Tier: `{a['tier']}` | Level: {a['level']}",
                f"Durum: `{a.get('status','?')}`",
                f"Provider: `{a.get('provider','?')}` / Model: `{a.get('model','?')}`",
                f"Departman: `{a.get('department','?')}`",
                f"Rapor: → `{a.get('reports_to','?')}`",
            ]
            if a.get("email_env"):
                email = os.environ.get(a["email_env"], "(env eksik)")
                lines.append(f"Email: `{email}`")
            if a.get("skills"):
                lines.append(f"Skills: {' '.join(['`/'+s+'`' for s in a['skills']])}")
            if a.get("description"):
                lines.append(f"\n_{a['description']}_")
            return "\n".join(lines)
    return f"❌ Agent bulunamadı: `{agent_id}`"


def get_department_view(dept_name):
    data = _load_hierarchy()
    depts = data.get("departments", {})

    # Departman adı eşleştirme
    dept_map = {
        "marketing": "marketing", "pazarlama": "marketing",
        "engineering": "engineering", "muhendislik": "engineering", "mühendislik": "engineering",
        "operations": "operations", "operasyon": "operations",
        "strategy": "strategy", "strateji": "strategy",
        "security": "security", "guvenlik": "security", "güvenlik": "security",
        "sales": "sales", "satis": "sales", "satış": "sales",
        "executive": "executive", "yonetim": "executive", "yönetim": "executive"
    }
    dept_key = dept_map.get(dept_name.lower(), dept_name.lower())
    dept_info = depts.get(dept_key, {})
    emoji = dept_info.get("emoji", "🏢")

    agents = [a for a in data["hierarchy"] if a.get("department") == dept_key]
    if not agents:
        return f"❌ Departman bulunamadı: `{dept_name}`"

    lines = [f"{emoji} **{dept_key.upper()} Departmanı** ({len(agents)} agent)", ""]
    for a in sorted(agents, key=lambda x: x["level"]):
        status_icon = {"active": "🟢", "pending_login": "🟡", "quota_exceeded": "🔴"}.get(a.get("status"), "⚪")
        lines.append(f"  {status_icon} [{a['level']}] **{a['title']}** — `{a['id']}`")
    return "\n".join(lines)


def get_active_owners():
    """agent_07 ve agent_08'in durumunu döndürür (paralel görünürlük)."""
    data = _load_hierarchy()
    bypass = _bypass_status()
    bypass_ok = bypass.get("ok", False)
    bypass_mode = bypass.get("mode", "?") if bypass_ok else "offline"

    owners = [a for a in data["hierarchy"] if a["tier"] == "owner"]
    lines = ["**👁 Aktif Sahip Agentlar**", ""]

    for o in owners:
        email = os.environ.get(o.get("email_env", ""), "(env eksik)")
        status = o.get("status", "?")
        status_icon = {"active": "🟢", "pending_login": "🟡"}.get(status, "⚪")
        lines.append(f"{status_icon} **{o['label']}**")
        lines.append(f"  ID: `{o['id']}`")
        lines.append(f"  Email: `{email}`")
        lines.append(f"  Durum: `{status}`")
        lines.append(f"  Provider: `{o.get('provider','?')}`")
        lines.append("")

    lines.append(f"🔧 Bypass Core: {'🟢 aktif' if bypass_ok else '🔴 offline'} (`{bypass_mode}`)")
    return "\n".join(lines)


def delegate_task(from_agent_id, to_agent_id, task):
    """Agent'tan agent'a görev delegasyonu — bypass exec ile çalıştırır."""
    if not task:
        return "❌ Görev boş"

    # Hiyerarşi kontrolü
    data = _load_hierarchy()
    from_a = next((a for a in data["hierarchy"] if a["id"] == from_agent_id), None)
    to_a   = next((a for a in data["hierarchy"] if a["id"] == to_agent_id), None)

    if not from_a:
        return f"❌ Kaynak agent bulunamadı: `{from_agent_id}`"
    if not to_a:
        return f"❌ Hedef agent bulunamadı: `{to_agent_id}`"

    # Yetki kontrolü: from_agent to_agent'ın üstünde mi?
    if from_a["level"] >= to_a["level"]:
        return (
            f"⚠️ Hiyerarşi ihlali: `{from_agent_id}` (level {from_a['level']}) "
            f"→ `{to_agent_id}` (level {to_a['level']}) delegate edemez"
        )

    # Bypass swarm üzerinden çalıştır
    try:
        body = json.dumps({"goal": task}).encode()
        req = urllib.request.Request(
            f"http://localhost:{BYPASS_PORT}/swarm",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())

        verdict = result.get("verdict", "?")
        emoji = {"pass": "✅", "fail": "❌"}.get(verdict, "⏳")
        return (
            f"📤 **Görev Delegasyonu**\n"
            f"Kaynak: `{from_a['label']}` → Hedef: `{to_a['label']}`\n"
            f"Görev: {task}\n"
            f"{emoji} Sonuç: `{verdict}` — {result.get('summary','')}"
        )
    except Exception as e:
        return f"❌ Swarm hatası: {e}"
