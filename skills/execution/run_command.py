"""
Skill: run_command
Kategori: execution
j.txt Section 5 - Komut calistirma skill (kontrollü, loglanmis)
"""
import subprocess
import logging
import shlex

log = logging.getLogger("skill.run_command")

MANIFEST = {
    "name": "run_command",
    "version": "1.0",
    "category": "execution",
    "inputs": {"command": "str", "timeout": "int", "cwd": "str"},
    "outputs": {"stdout": "str", "stderr": "str", "returncode": "int"},
    "permissions": ["execute"],
    "failure_modes": ["timeout", "permission_denied", "command_not_found"],
    "logs": ["command", "returncode", "duration"]
}

# Yasakli komutlar (j.txt Section 7 - Policy Gate)
FORBIDDEN = ["rm -rf /", "mkfs", "dd if=", "> /dev/sda", "shutdown", "reboot"]


def _policy_check(command: str) -> tuple[bool, str]:
    for f in FORBIDDEN:
        if f in command:
            return False, f"Forbidden command pattern: {f}"
    return True, "ok"


def run(command: str, timeout: int = 30, cwd: str = None) -> dict:
    ok, reason = _policy_check(command)
    if not ok:
        log.error(f"Policy blocked: {command}")
        return {"stdout": "", "stderr": reason, "returncode": -1, "error": "policy_blocked"}

    log.info(f"Running: {command[:80]}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        log.info(f"returncode={result.returncode}")
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "error": None
        }
    except subprocess.TimeoutExpired:
        log.error(f"Timeout: {command}")
        return {"stdout": "", "stderr": "timeout", "returncode": -1, "error": "timeout"}
    except Exception as e:
        log.error(f"Error: {e}")
        return {"stdout": "", "stderr": str(e), "returncode": -1, "error": str(e)}


if __name__ == "__main__":
    r = run("echo 'Jarvis skill test OK' && date")
    print(r)
