"""
Skill: run_command
Kategori: execution
j.txt Section 5 - Komut calistirma skill (kontrollu, loglanmis)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

BYPASS_PORT = int(os.environ.get("BYPASS_PORT", 7090))

ROOT_DIR = Path(__file__).resolve().parent  # server/skills/
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from permission_mode import evaluate_command  # noqa: E402

log = logging.getLogger("skill.run_command")

MANIFEST = {
    "name": "run_command",
    "version": "1.1",
    "category": "execution",
    "inputs": {
        "command": "str",
        "timeout": "int",
        "cwd": "str",
        "surface": "str",
    },
    "outputs": {
        "stdout": "str",
        "stderr": "str",
        "returncode": "int",
        "mode": "str",
    },
    "permissions": ["execute"],
    "failure_modes": ["timeout", "permission_denied", "command_not_found"],
    "logs": ["command", "returncode", "duration", "mode"],
}


def run(command: str, timeout: int = 30, cwd: str | None = None, surface: str = "safe") -> dict:
    decision = evaluate_command(command, surface=surface)
    if not decision["allowed"]:
        error = "policy_blocked" if decision["status"] == "blocked" else "approval_required"
        log.warning("Command denied (%s/%s): %s", decision["mode"], surface, command[:120])
        return {
            "stdout": "",
            "stderr": decision["message"],
            "returncode": -1,
            "error": error,
            "mode": decision["mode"],
            "decision": decision,
        }

    log.info("Running (%s/%s): %s", decision["mode"], surface, command[:120])

    # Node.js executor varsa ona yönlendir (pre-approved = Python zaten ALLOW dedi)
    node_result = _try_node_executor(command, cwd, timeout, decision["mode"])
    if node_result is not None:
        node_result["decision"] = decision
        return node_result

    # Node yoksa Python subprocess fallback
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        log.info("returncode=%s", result.returncode)
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "error": None,
            "mode": decision["mode"],
            "decision": decision,
        }
    except subprocess.TimeoutExpired:
        log.error("Timeout: %s", command)
        return {
            "stdout": "",
            "stderr": f"timeout after {timeout}s",
            "returncode": -1,
            "error": "timeout",
            "mode": decision["mode"],
            "decision": decision,
        }
    except Exception as exc:
        log.error("Error: %s", exc)
        return {
            "stdout": "",
            "stderr": str(exc),
            "returncode": -1,
            "error": str(exc),
            "mode": decision["mode"],
            "decision": decision,
        }


def _try_node_executor(command: str, cwd, timeout: int, mode: str):
    """Python → Node.js executor HTTP köprüsü. Node çalışmıyorsa None döner."""
    try:
        body = json.dumps({
            "command": command,
            "cwd": cwd,
            "timeout": timeout,
            "preApproved": True,
            "decisionMode": mode
        }).encode()
        req = urllib.request.Request(
            f"http://localhost:{BYPASS_PORT}/exec",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=min(timeout + 5, 120)) as r:
            data = json.loads(r.read())
        return {
            "stdout": data.get("stdout", ""),
            "stderr": data.get("stderr", ""),
            "returncode": 0 if data.get("ok") else 1,
            "error": None if data.get("ok") else data.get("message"),
            "mode": mode,
            "via": "node-executor"
        }
    except urllib.error.URLError:
        log.debug("Node executor ulaşılamıyor, Python fallback")
        return None
    except Exception as exc:
        log.warning("Node executor hatası: %s", exc)
        return None


if __name__ == "__main__":
    samples = [
        ("echo Jarvis skill test OK", "safe"),
        ("git status", "safe"),
        ("python --version", "danger"),
    ]
    for sample, surface in samples:
        print(run(sample, surface=surface))
