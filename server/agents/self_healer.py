"""
Jarvis self-healer.
error -> classify -> generate fix commands -> retry -> remember working fix
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

_SKILLS = Path(__file__).parent.parent / "skills"
if str(_SKILLS) not in sys.path:
    sys.path.insert(0, str(_SKILLS))

ERROR_PATTERNS = [
    ("not found", "missing_binary"),
    ("command not found", "missing_binary"),
    ("no such file", "missing_file"),
    ("permission denied", "permission"),
    ("module not found", "missing_module"),
    ("cannot find module", "missing_module"),
    ("modulenotfounderror", "missing_module"),
    ("importerror", "missing_module"),
    ("npm err", "npm_error"),
    ("npm warn", "npm_warn"),
    ("enoent", "missing_file"),
    ("eacces", "permission"),
    ("eaddrinuse", "port_in_use"),
    ("address already in use", "port_in_use"),
    ("syntaxerror", "syntax_error"),
    ("timeout", "timeout"),
    ("connection refused", "service_down"),
    ("network error", "network"),
    ("ssl", "ssl_error"),
    ("python: can't open", "missing_file"),
    ("no module named", "missing_module"),
]


def analyze_error(stderr: str, stdout: str = "") -> str:
    combined = (stderr + " " + stdout).lower()
    for pattern, error_type in ERROR_PATTERNS:
        if pattern in combined:
            return error_type
    return "unknown"


def _is_windows() -> bool:
    return os.name == "nt"


def _shell_quote(value: str) -> str:
    if not value:
        return '""' if _is_windows() else "''"
    if _is_windows():
        return f'"{value}"'
    return "'" + value.replace("'", "'\"'\"'") + "'"


def generate_fix(command: str, error_type: str, stderr: str = "") -> list[str]:
    """Generate one or more low-risk fix commands for the error."""
    cmd = command.strip()
    first_word = cmd.split()[0] if cmd.split() else cmd
    target = cmd.split()[-1] if cmd.split() else cmd

    fixes = {
        "missing_binary": [
            _missing_binary_lookup(first_word),
            _missing_binary_install(first_word),
        ],
        "missing_module": [
            _detect_module_fix(cmd, stderr),
        ],
        "permission": _permission_fixes(target),
        "missing_file": [
            _missing_file_fix(target),
        ],
        "npm_error": [
            "npm install",
            "npm install --legacy-peer-deps",
        ],
        "npm_warn": [cmd],
        "port_in_use": [
            _detect_port_fix(stderr),
        ],
        "syntax_error": [],
        "timeout": [cmd],
        "service_down": [
            f"echo Service check needed: {first_word}",
        ],
        "network": [
            _network_check_command(),
        ],
        "unknown": [],
    }

    result = fixes.get(error_type, [])
    return [fix for fix in result if fix]


def _detect_module_fix(command: str, stderr: str) -> str:
    module_match = re.search(r"[Nn]o module named ['\"]?([a-zA-Z0-9_-]+)", stderr)
    npm_match = re.search(r"Cannot find module ['\"]([a-zA-Z0-9_/@-]+)", stderr)

    if module_match:
        mod = module_match.group(1)
        return f"py -m pip install {mod}" if _is_windows() else f"pip install {mod}"
    if npm_match:
        mod = npm_match.group(1)
        if not mod.startswith("."):
            return f"npm install {mod}"
    if "python" in command.lower():
        if _is_windows():
            return "if exist requirements.txt (py -m pip install -r requirements.txt || pip install -r requirements.txt) else echo requirements.txt missing"
        return "pip install -r requirements.txt 2>/dev/null || echo 'requirements.txt missing'"
    return "npm install"


def _detect_port_fix(stderr: str) -> str:
    port_match = re.search(r":(\d{4,5})", stderr)
    if port_match:
        port = port_match.group(1)
        if _is_windows():
            return f"netstat -ano | findstr :{port}"
        return f"lsof -i :{port} || netstat -an | grep {port}"
    if _is_windows():
        return "netstat -ano | findstr LISTENING"
    return "lsof -i -P -n | head -5 || netstat -an | grep LISTEN"


def _missing_binary_lookup(first_word: str) -> str:
    if _is_windows():
        return f"where {first_word} || echo {first_word} missing"
    return f"command -v {first_word} || echo '{first_word} missing'"


def _missing_binary_install(first_word: str) -> str:
    if _is_windows():
        return f"py -m pip install {first_word} || pip install {first_word} || npm install -g {first_word} || echo manual install required"
    return f"pip install {first_word} 2>/dev/null || npm install -g {first_word} 2>/dev/null || echo 'manual install required'"


def _permission_fixes(target: str) -> list[str]:
    quoted_target = _shell_quote(target)
    if _is_windows():
        return [
            f"icacls {quoted_target}",
            f"dir {quoted_target}",
        ]
    return [
        f"chmod +x {quoted_target}",
        f"ls -la {quoted_target} 2>/dev/null",
    ]


def _missing_file_fix(target: str) -> str:
    quoted_target = _shell_quote(target)
    if _is_windows():
        return f"dir {quoted_target} || cd"
    return f"ls -la {quoted_target} 2>/dev/null || pwd"


def _network_check_command() -> str:
    if _is_windows():
        return "ping -n 1 8.8.8.8 >nul 2>&1 && echo ok || echo network_error"
    return "ping -c 1 8.8.8.8 >/dev/null 2>&1 && echo ok || echo network_error"


def self_heal(command: str, result: dict, memory=None, max_retries: int = 2) -> dict:
    """
    Main self-heal loop.
    result: output from run_command.run
    memory: optional memory object with get_fix/remember
    """
    if result.get("returncode", -1) == 0 or result.get("error") is None:
        return {**result, "healed": False, "heal_attempts": 0}

    stderr = result.get("stderr", "")
    stdout = result.get("stdout", "")
    error_type = analyze_error(stderr, stdout)

    if memory:
        known_fix = memory.get_fix(error_type, command)
        if known_fix:
            fix_cmds = [known_fix]
        else:
            fix_cmds = generate_fix(command, error_type, stderr)
    else:
        fix_cmds = generate_fix(command, error_type, stderr)

    if not fix_cmds:
        return {
            **result,
            "healed": False,
            "heal_attempts": 0,
            "error_type": error_type,
            "message": f"No fix generated (error_type: {error_type})",
        }

    try:
        from run_command import run
    except ImportError:
        return {
            **result,
            "healed": False,
            "error_type": error_type,
            "message": "run_command import failed",
        }

    heal_log = []
    for attempt in range(max_retries):
        for fix_cmd in fix_cmds:
            fix_result = run(fix_cmd, surface="safe")
            heal_log.append({"fix": fix_cmd, "result": fix_result.get("returncode", -1)})

        retry_result = run(command, surface="safe")
        if retry_result.get("returncode", -1) == 0:
            if memory and fix_cmds:
                memory.remember(error_type, command, fix_cmds[0])
            return {
                **retry_result,
                "healed": True,
                "heal_attempts": attempt + 1,
                "error_type": error_type,
                "fix_used": fix_cmds[0],
                "heal_log": heal_log,
            }

    return {
        **result,
        "healed": False,
        "heal_attempts": max_retries,
        "error_type": error_type,
        "heal_log": heal_log,
        "message": f"Self-heal failed after {max_retries} attempts (type: {error_type})",
    }
