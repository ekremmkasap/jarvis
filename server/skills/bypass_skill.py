"""
Jarvis Bypass Skill
Python permission engine (permission_mode.py) + Node.js executor (port 7090) köprüsü.
"""
import urllib.request, urllib.error, json, subprocess, os, sys
from pathlib import Path

_SKILLS_DIR = Path(__file__).parent
if str(_SKILLS_DIR) not in sys.path:
    sys.path.insert(0, str(_SKILLS_DIR))

BYPASS_PORT = int(os.environ.get("BYPASS_PORT", 7090))
BYPASS_URL  = f"http://localhost:{BYPASS_PORT}"
CORE_DIR    = os.path.join(
    os.path.dirname(__file__), "..", "..", "jarvis-bypass-core"
)

def _call(method, path, body=None):
    url = BYPASS_URL + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e)}

# ─── Public API ────────────────────────────────────────────

def bypass_status():
    h = _call("GET", "/health")
    node_ok = h.get("ok", False)
    node_mode = h.get("mode", "?")

    # Python permission engine durumu
    py_mode = "?"
    py_updated = "?"
    try:
        from permission_mode import get_mode_state
        ps = get_mode_state()
        py_mode = ps.get("mode", "?")
        py_updated = (ps.get("updated_at") or "default")[:19]
    except ImportError:
        py_mode = "engine yok"

    emoji_node = {"strict": "🔒", "auto": "⚡", "danger": "☠️"}.get(node_mode, "❓")
    emoji_py   = {"strict": "🔒", "auto": "⚡", "danger": "☠️"}.get(py_mode,   "❓")
    node_status = "🟢 aktif" if node_ok else "🔴 çalışmıyor"

    sync_icon = "✅" if node_mode == py_mode else "⚠️ DESYNC"

    lines = [
        "**Jarvis Bypass — Unified Permission Layer**",
        "",
        f"🐍 Python Engine: {emoji_py} `{py_mode.upper()}` (güncellendi: {py_updated})",
        f"⚙️  Node Executor: {node_status} {emoji_node} `{node_mode.upper()}`",
        f"🔗 Senkronizasyon: {sync_icon}",
        f"⏱ Node Uptime: {int(h.get('uptime', 0))}s",
        f"🌐 Port: {BYPASS_PORT}",
    ]
    if not node_ok:
        lines.append("\nBaslatmak icin: `/bypass-start`")
    return "\n".join(lines)

def bypass_mode(mode):
    valid = {"strict", "auto", "danger"}
    if mode not in valid:
        return f"❌ Geçersiz mod. Kullanım: `/bypass-mode strict|auto|danger`"

    errors = []
    emoji = {"strict": "🔒", "auto": "⚡", "danger": "☠️"}.get(mode, "")

    # 1. Python permission engine güncelle
    try:
        from permission_mode import set_mode
        set_mode(mode, actor="telegram")
    except ImportError:
        errors.append("Python engine bulunamadı")
    except Exception as e:
        errors.append(f"Python: {e}")

    # 2. Node.js bypass core güncelle
    r = _call("POST", "/mode", {"mode": mode})
    if not r.get("ok"):
        errors.append(f"Node: {r.get('error', '?')}")

    if errors:
        return f"⚠️ Mode kısmen değiştirildi: `{mode.upper()}`\nHatalar: {', '.join(errors)}"
    return f"{emoji} Mode değiştirildi: `{mode.upper()}` (Python + Node senkron)"

def bypass_exec(command):
    if not command:
        return "❌ Komut boş. Örnek: `/bypass-exec echo merhaba`"

    # Python permission engine ile kontrol et
    try:
        from permission_mode import evaluate_command
        decision = evaluate_command(command, surface="safe")
        if not decision["allowed"]:
            mode = decision.get("mode", "?")
            reason = decision.get("message", "izin yok")
            emoji = {"strict": "🔒", "auto": "⚡", "danger": "☠️"}.get(mode, "❓")
            return (
                f"⛔ **İzin Verilmedi**\n"
                f"{emoji} Mode: `{mode.upper()}`\n"
                f"Sebep: {reason}"
            )
        # Python ALLOW → Node executor'a ilet (preApproved=True)
        r = _call("POST", "/exec", {
            "command": command,
            "preApproved": True,
            "decisionMode": decision.get("mode", "auto")
        })
    except ImportError:
        # permission_mode yoksa direkt Node'a git
        r = _call("POST", "/exec", {"command": command})

    status = r.get("status", "?")
    emoji = {"executed": "✅", "blocked": "⛔", "error": "❌"}.get(status, "❓")
    lines = [f"{emoji} `{command}`", f"Status: `{status}`"]
    if r.get("stdout"):
        lines.append(f"```\n{r['stdout'][:1000]}\n```")
    if r.get("stderr"):
        lines.append(f"stderr:\n```\n{r['stderr'][:500]}\n```")
    if r.get("message"):
        lines.append(r["message"])
    return "\n".join(lines)

def bypass_logs(n=10):
    r = _call("GET", f"/logs?n={n}")
    if not isinstance(r, list):
        return f"❌ Log alınamadı: {r}"
    if not r:
        return "📋 Log boş"
    lines = ["📋 **Son Komutlar:**", ""]
    for entry in r[-n:]:
        s = entry.get("status", "?")
        c = entry.get("command", "?")[:60]
        t = entry.get("ts", "")[:19]
        lines.append(f"`{t}` | `{s}` | `{c}`")
    return "\n".join(lines)

def bypass_start():
    core_dir = os.path.abspath(CORE_DIR)
    if not os.path.exists(core_dir):
        return f"❌ jarvis-bypass-core bulunamadı: {core_dir}"
    try:
        subprocess.Popen(
            ["node", "src/index.js"],
            cwd=core_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            if sys.platform == "win32" else 0
        )
        return f"🚀 Bypass Core başlatılıyor... port {BYPASS_PORT}"
    except Exception as e:
        return f"❌ Başlatma hatası: {e}"
