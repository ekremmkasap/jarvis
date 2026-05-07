"""
Jarvis Corp — Coordinator Engine
CEO katmanı: görevi alır, capability router'dan en iyi repoyu seçer, execute eder.
22 repo birbirine bu engine üzerinden bağlanır.
"""
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# Capability Router'ı import et
_AGENTS_DIR = Path(__file__).parent
if str(_AGENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_AGENTS_DIR))

BASE_DIR    = Path(__file__).parent.parent
CONFIG_DIR  = BASE_DIR.parent / "config"
BYPASS_PORT = int(os.environ.get("BYPASS_PORT", 7090))

# Departman → Jarvis skill eşlemesi
DEPT_SKILLS = {
    "marketing":   ["/reklam_ajans", "/icerik", "/ara", "/satis"],
    "engineering": ["/code", "/aider", "/bypass-exec", "/swarm"],
    "strategy":    ["/ara", "/rakip", "/ebay", "/trendyol"],
    "operations":  ["/swarm", "/bypass-exec", "/task"],
    "security":    ["/bypass-logs", "/security-board", "/bypass-mode strict"],
}

# Anahtar kelime → departman yönlendirme
KEYWORD_DEPT = {
    "reklam": "marketing", "kampanya": "marketing", "içerik": "marketing",
    "icerik": "marketing", "seo": "marketing", "sosyal": "marketing",
    "tiktok": "marketing", "instagram": "marketing", "viral": "marketing",
    "kod": "engineering", "code": "engineering", "bug": "engineering",
    "deploy": "engineering", "api": "engineering", "python": "engineering",
    "javascript": "engineering", "debug": "engineering", "yazılım": "engineering",
    "araştır": "strategy", "analiz": "strategy", "rakip": "strategy",
    "pazar": "strategy", "trend": "strategy", "ebay": "strategy",
    "trendyol": "strategy", "büyüme": "strategy", "strateji": "strategy",
    "çalıştır": "operations", "komut": "operations", "swarm": "operations",
    "otomasyon": "operations", "pipeline": "operations",
    "güvenlik": "security", "security": "security", "engelle": "security",
    "güvenli": "security",
}


def _call_swarm(goal, cwd=None):
    body = json.dumps({"goal": goal, "cwd": cwd}).encode()
    req = urllib.request.Request(
        f"http://localhost:{BYPASS_PORT}/swarm",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "verdict": "error", "summary": str(e)}


def _detect_departments(goal):
    goal_lower = goal.lower()
    detected = set()
    for kw, dept in KEYWORD_DEPT.items():
        if kw in goal_lower:
            detected.add(dept)
    return list(detected) if detected else ["operations"]


def _build_dept_tasks(goal, departments):
    """Her departman için alt görev tanımla."""
    tasks = []
    for dept in departments:
        if dept == "marketing":
            tasks.append({
                "dept": "marketing",
                "manager": "mgr_marketing",
                "goal": f"Pazarlama görevi: {goal}",
                "type": "content"
            })
        elif dept == "engineering":
            tasks.append({
                "dept": "engineering",
                "manager": "mgr_engineering",
                "goal": f"Teknik uygulama: {goal}",
                "type": "code"
            })
        elif dept == "strategy":
            tasks.append({
                "dept": "strategy",
                "manager": "mgr_strategy",
                "goal": f"Araştırma ve analiz: {goal}",
                "type": "research"
            })
        elif dept == "operations":
            tasks.append({
                "dept": "operations",
                "manager": "mgr_operations",
                "goal": goal,
                "type": "exec"
            })
        elif dept == "security":
            tasks.append({
                "dept": "security",
                "manager": "mgr_security",
                "goal": f"Güvenlik kontrolü: {goal}",
                "type": "audit"
            })
    return tasks


def _smart_route(goal, dept):
    """Capability router ile en iyi repoyu seç."""
    try:
        from capability_router import route, recommend_pipeline
        result = route(goal)
        return result
    except Exception:
        return {"repo": "bypass-core", "primary_command": "/swarm", "alternatives": []}


def run_corporate_task(goal, call_llm=None):
    """
    CEO koordinatörü: görevi al, departmanlara kır, execute et.
    """
    if not goal:
        return "❌ Hedef boş. Örnek: `/sirket-gorev viral reklam kampanyası hazırla`"

    lines = [
        f"🎖 **Jarvis Corp — CEO Koordinatörü**",
        f"🎯 Hedef: {goal}",
        ""
    ]

    # 1. Departman tespiti
    departments = _detect_departments(goal)
    lines.append(f"📋 Tespit edilen departmanlar: {', '.join(departments)}")
    lines.append("")

    # 2. Alt görevler
    dept_tasks = _build_dept_tasks(goal, departments)

    # 3. LLM destekli planlama (varsa)
    if call_llm and len(departments) > 1:
        try:
            plan_prompt = (
                f"Şirket hedefi: {goal}\n"
                f"İlgili departmanlar: {', '.join(departments)}\n"
                "Her departman için 1 cümlelik somut alt görev yaz. Türkçe."
            )
            llm_plan = call_llm(plan_prompt)
            if llm_plan:
                lines.append("🧠 **CEO Planı:**")
                lines.append(llm_plan[:500])
                lines.append("")
        except Exception:
            pass

    # 4. Her departman görevi execute et — capability router ile en iyi repo seçilir
    results = []
    for task in dept_tasks:
        dept_emoji = {"marketing":"📣","engineering":"⚙️","strategy":"🎯","operations":"🔄","security":"🔒"}.get(task["dept"],"🏢")

        # Router: bu görev için en iyi repo hangisi?
        route_info = _smart_route(task["goal"], task["dept"])
        best_repo = route_info.get("repo", "bypass-core")
        best_cmd  = route_info.get("primary_command", "/swarm")
        alts      = route_info.get("alternatives", [])

        lines.append(f"{dept_emoji} **{task['dept'].upper()}** → `{best_repo}` ({best_cmd})")
        if alts:
            lines.append(f"  Alternatif: {', '.join(alts[:2])}")

        result = _call_swarm(task["goal"])
        verdict = result.get("verdict", "?")
        summary = result.get("summary", "")
        emoji = {"pass":"✅","fail":"❌","error":"❌"}.get(verdict,"⏳")

        lines.append(f"  {emoji} {verdict}: {summary}")
        results.append({"dept": task["dept"], "repo": best_repo, "verdict": verdict, "summary": summary})
        lines.append("")

    # 5. Genel özet
    passed = sum(1 for r in results if r["verdict"] == "pass")
    total  = len(results)
    overall = "✅ Tamamlandı" if passed == total else f"⚠️ {passed}/{total} başarılı"
    lines.append(f"📊 **Genel Durum:** {overall}")
    lines.append(f"🕐 {datetime.now().strftime('%H:%M:%S')}")

    return "\n".join(lines)


def analyze(call_llm=None):
    return {
        "report": "Coordinator Engine hazır. /sirket-gorev ile kullan.",
        "score": 90,
        "error": None
    }
