#!/usr/bin/env python3
"""
OpenClaw Skill v2.0 — Pinokio/Windows Edition
Ollama (yerel) veya Claude CLI ile görev çalıştırır.
Komutlar: /agent <gorev>, /task <gorev>, /durum
"""
import sys
import subprocess
import logging
import platform
import os
from pathlib import Path

# ── Path setup ───────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent  # server/
IS_WINDOWS = platform.system() == "Windows"

# Agents ve core klasörlerini yükle
for _p in [
    BASE_DIR / "agents",
    BASE_DIR / "core",
    Path("/opt/jarvis/agents"),
    Path("/opt/jarvis/core"),
]:
    _ps = str(_p)
    if _p.exists() and _ps not in sys.path:
        sys.path.insert(0, _ps)

log = logging.getLogger("openclaw")

# ── Claude CLI: Windows/Linux otomatik bul ───────────────────────────
def _find_claude() -> str:
    candidates = [
        # Windows - npm global
        Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",
        Path(os.environ.get("APPDATA", "")) / "npm" / "claude",
        # Linux
        Path("/home/userk/.npm-global/bin/claude"),
        Path("/usr/local/bin/claude"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    # PATH'te ara
    try:
        r = subprocess.run(
            ["where" if IS_WINDOWS else "which", "claude"],
            capture_output=True, text=True, timeout=3
        )
        if r.returncode == 0:
            return r.stdout.strip().splitlines()[0]
    except Exception:
        pass
    return ""

CLAUDE_BIN = _find_claude()

# ── Sunucu bağlamı ────────────────────────────────────────────────────
SERVER_CONTEXT = f"""Sen Jarvis Mission Control'dasın.
Platform: {'Windows/Pinokio' if IS_WINDOWS else 'Linux/Ubuntu'}
Proje dizini: {BASE_DIR}
Ollama: http://127.0.0.1:11434
Web Dashboard: http://127.0.0.1:8080
Kullanıcı: Ekrem (owner, tam yetkili)
"""


# ── Görev çalıştır: önce Ollama, fallback Claude CLI ─────────────────
def run_agent_task(task: str, send_progress=None) -> str:
    if send_progress:
        send_progress("_Jarvis düşünüyor..._")

    # 1. Önce CoreAgent dene
    try:
        from agent import Task as CoreTask
        from claude_agent import ClaudeAgent
        agent = ClaudeAgent()
        t = CoreTask(goal=task)
        ctx = {"chat_history": [], "inputs": {"server_context": SERVER_CONTEXT}, "plan": []}
        result = agent.run(t, ctx)
        output = result.get("output", "").strip()
        if output:
            log.info("CoreAgent başarılı")
            return output
    except Exception as e:
        log.debug(f"CoreAgent yok/hata ({e}), fallback Ollama")

    # 2. Ollama ile çalıştır (her zaman mevcut)
    return _run_with_ollama(task, send_progress)


def _run_with_ollama(task: str, send_progress=None) -> str:
    """Ollama ile görev çalıştır."""
    if send_progress:
        send_progress("_Ollama Agent çalışıyor..._")
    try:
        import json
        from urllib.request import urlopen, Request

        # Mevcut en iyi modeli bul
        model = _get_best_model()

        system = (
            SERVER_CONTEXT + "\n\n"
            "Sen gelişmiş bir görev yürütme ajanısın. "
            "Adım adım düşün, net ve uygulanabilir cevaplar ver. "
            "Türkçe yaz."
        )
        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": task}],
            "system": system,
            "stream": False,
            "options": {"temperature": 0.6, "num_predict": 1024, "num_ctx": 4096}
        }).encode()

        req = Request(
            "http://127.0.0.1:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
        output = result.get("message", {}).get("content", "").strip()
        return f"[{model.split(':')[0]}] {output}" if output else "(boş yanıt)"

    except Exception as e:
        log.error(f"Ollama agent hatası: {e}")
        # 3. Son çare: Claude CLI
        if CLAUDE_BIN:
            return _run_claude_direct(task, send_progress)
        return f"Hata: Ollama bağlanamadı ve Claude CLI bulunamadı. ({e})"


def _run_claude_direct(task: str, send_progress=None) -> str:
    """Claude CLI ile görev çalıştır (varsa)."""
    if not CLAUDE_BIN:
        return "Claude CLI bulunamadı. 'npm install -g @anthropic-ai/claude-code' ile kur."
    if send_progress:
        send_progress("_Claude CLI çalışıyor..._")

    prompt = SERVER_CONTEXT + "\n\nGörev: " + task + "\n\nTürkçe, net yanıt ver."
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True,
            timeout=120, encoding="utf-8", errors="replace"
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output or "(boş yanıt)"
    except subprocess.TimeoutExpired:
        return "Zaman aşımı: Görev 120 saniyede tamamlanamadı."
    except Exception as e:
        return f"Claude hatası: {e}"


def _get_best_model() -> str:
    """Ollama'da kurulu en iyi modeli seç."""
    try:
        import json
        from urllib.request import urlopen, Request
        with urlopen(Request("http://127.0.0.1:11434/api/tags"), timeout=3) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        priority = [
            "deepseek-r1", "qwen2.5:7b", "llama3.1", "llama3.2",
            "mistral", "deepseek-coder", "qwen2.5-coder", "qwen2.5"
        ]
        for p in priority:
            match = next((m for m in models if p in m), None)
            if match:
                return match
        return models[0] if models else "llama3.2:latest"
    except Exception:
        return "llama3.2:latest"


def run_shell_full(cmd: str) -> str:
    """Platform uyumlu shell komutu çalıştır."""
    DANGER = ["rm -rf /", "mkfs", "Format-Volume", "> /dev/sd", "dd if=/dev/zero"]
    if any(d.lower() in cmd.lower() for d in DANGER):
        return "HATA: Tehlikeli komut engellendi."
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True,
                timeout=30, encoding="utf-8", errors="replace"
            )
        else:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=30, encoding="utf-8", errors="replace",
                cwd=str(BASE_DIR)
            )
        return (result.stdout.strip() or result.stderr.strip() or "(çıktı yok)")[:3000]
    except subprocess.TimeoutExpired:
        return "Komut zaman aşımına uğradı (30sn)"
    except Exception as e:
        return f"Komut hatası: {e}"


def get_jarvis_status() -> str:
    """Sistem durum raporu — Windows/Linux uyumlu."""
    lines = [f"Platform: {'Windows/Pinokio' if IS_WINDOWS else 'Linux'}"]

    if IS_WINDOWS:
        # Ollama kontrol
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "if(Get-Process ollama -EA SilentlyContinue){'active'}else{'inactive'}"],
                capture_output=True, text=True, timeout=4
            )
            lines.append(f"[{'OK' if 'active' in r.stdout else 'XX'}] ollama: {r.stdout.strip()}")
        except Exception:
            lines.append("[??] ollama: bilinmiyor")

        # RAM
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "$os=Get-WmiObject Win32_OperatingSystem;$u=[math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/1MB,1);$t=[math]::Round($os.TotalVisibleMemorySize/1MB,1);Write-Output \"${u}GB/${t}GB\""],
                capture_output=True, text=True, timeout=5
            )
            lines.append(f"RAM: {r.stdout.strip()}")
        except Exception:
            pass
    else:
        for svc in ["jarvis", "n8n", "ollama", "tenant_manager"]:
            try:
                r = subprocess.run(["systemctl", "is-active", svc + ".service"],
                                   capture_output=True, text=True, timeout=3)
                status = r.stdout.strip()
                lines.append(f"[{'OK' if status == 'active' else 'XX'}] {svc}: {status}")
            except Exception:
                lines.append(f"[??] {svc}: bilinmiyor")
        try:
            r = subprocess.run("free -h | awk '/^Mem:/ {print $3\"/\"$2}'",
                               shell=True, capture_output=True, text=True, timeout=3)
            lines.append(f"RAM: {r.stdout.strip()}")
        except Exception:
            pass

    # Ollama modelleri
    try:
        import json
        from urllib.request import urlopen, Request
        with urlopen(Request("http://127.0.0.1:11434/api/tags"), timeout=3) as r:
            models = [m["name"] for m in json.loads(r.read()).get("models", [])]
        lines.append(f"Ollama: {len(models)} model — {', '.join(models[:3])}")
    except Exception:
        lines.append("Ollama: bağlanamadı")

    # Claude CLI
    lines.append(f"Claude CLI: {'✅ ' + CLAUDE_BIN if CLAUDE_BIN else '❌ kurulu değil'}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("=== OpenClaw Skill v2.0 — Pinokio Edition ===")
    print(get_jarvis_status())
