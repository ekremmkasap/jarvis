"""
Skill: sunucu_yonet
Kategori: execution
Sunucu yönetimi: servis kontrolü, sistem durumu, log okuma
"""
import subprocess
import logging

log = logging.getLogger("skill.sunucu_yonet")

MANIFEST = {
    "name": "sunucu_yonet",
    "version": "1.0",
    "category": "execution",
    "inputs": {"action": "str", "target": "str"},
    "outputs": {"result": "str", "success": "bool"},
    "permissions": ["execute", "system"],
    "failure_modes": ["permission_denied", "service_not_found", "command_error"],
    "logs": ["action", "target", "returncode"]
}

ALLOWED_SERVICES = ["gateway", "openclaw", "ollama", "openclaw-gateway"]


def _run(cmd: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def run(action: str, target: str = "") -> dict:
    action = action.lower().strip()
    log.info(f"sunucu_yonet: {action} {target}")

    # Sistem durumu
    if action in ("durum", "status", "bilgi"):
        cmds = {
            "CPU": "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",
            "RAM": "free -h | awk '/^Mem:/{print $3\"/\"$2}'",
            "Disk": "df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\" dolu)\"}'",
            "Uptime": "uptime -p",
        }
        lines = []
        for label, cmd in cmds.items():
            ok, out = _run(cmd)
            lines.append(f"{label}: {out if ok else 'N/A'}")
        return {"result": "\n".join(lines), "success": True, "error": None}

    # Servis başlat/durdur/yeniden başlat/durum
    if action in ("baslat", "start", "durdur", "stop", "yeniden-baslat", "restart", "servis-durum", "service-status"):
        if not target:
            return {"result": "Hedef servis belirtilmedi.", "success": False, "error": "no_target"}
        if target not in ALLOWED_SERVICES:
            return {"result": f"'{target}' servisi izin listesinde değil.", "success": False, "error": "not_allowed"}

        action_map = {
            "baslat": "start", "start": "start",
            "durdur": "stop", "stop": "stop",
            "yeniden-baslat": "restart", "restart": "restart",
            "servis-durum": "status", "service-status": "status",
        }
        systemctl_action = action_map[action]
        cmd = f"echo userk1 | sudo -S systemctl {systemctl_action} {target}.service 2>&1"
        ok, out = _run(cmd)
        return {"result": out[:500], "success": ok, "error": None if ok else "command_failed"}

    # Log oku
    if action in ("log", "loglar", "logs"):
        service = target or "gateway"
        if service not in ALLOWED_SERVICES:
            return {"result": f"'{service}' izin listesinde değil.", "success": False, "error": "not_allowed"}
        cmd = f"echo userk1 | sudo -S journalctl -u {service}.service -n 20 --no-pager 2>&1"
        ok, out = _run(cmd)
        return {"result": out[:1000], "success": ok, "error": None}

    # Çalışan processler
    if action in ("processler", "processes", "ps"):
        ok, out = _run("ps aux --sort=-%cpu | head -10")
        return {"result": out, "success": ok, "error": None}

    return {"result": f"Bilinmeyen işlem: '{action}'. Geçerli: durum, baslat, durdur, restart, log, ps", "success": False, "error": "unknown_action"}


if __name__ == "__main__":
    print("=== Sunucu Durumu ===")
    r = run("durum")
    print(r["result"])
    print("\n=== Gateway Servis Durumu ===")
    r = run("servis-durum", "gateway")
    print(r["result"][:300])
