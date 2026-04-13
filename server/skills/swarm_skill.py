"""
Jarvis Swarm Skill
Agent Swarm'u (port 7090/swarm) Telegram'dan yönetir.
"""
import urllib.request, urllib.error, json, os

BYPASS_PORT = int(os.environ.get("BYPASS_PORT", 7090))
SWARM_URL   = f"http://localhost:{BYPASS_PORT}/swarm"


def _post(body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        SWARM_URL, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e)}


def swarm_run(goal, llm_url=None, cwd=None):
    if not goal:
        return "❌ Hedef boş. Örnek: `/swarm npm bağımlılıkları kur`"

    body = {"goal": goal}
    if llm_url:
        body["llmUrl"] = llm_url
    if cwd:
        body["cwd"] = cwd

    r = _post(body)

    if not r.get("ok"):
        return f"❌ Swarm hatası: {r.get('error', 'bilinmiyor')}"

    verdict = r.get("verdict", "?")
    emoji = {"pass": "✅", "fail": "❌", "pending": "⏸"}.get(verdict, "❓")
    lines = [
        f"{emoji} **Swarm Tamamlandı** — `{verdict.upper()}`",
        f"🎯 Hedef: {goal}",
        f"🔄 Loop: {r.get('loops', '?')}",
        f"📝 Özet: {r.get('summary', '')}",
        ""
    ]

    result_lines = r.get("resultLines", [])
    if result_lines:
        lines.append("**Adımlar:**")
        lines.extend(result_lines[:15])

    warnings = r.get("securityWarnings", [])
    if warnings:
        lines.append(f"\n⚠️ **Güvenlik uyarısı:** {len(warnings)} adımda hassas veri olabilir")

    return "\n".join(lines)
