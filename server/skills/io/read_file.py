"""
Skill: read_file
Kategori: io
j.txt Section 5 - Dosya okuma skill
"""
import logging
from pathlib import Path

log = logging.getLogger("skill.read_file")

MANIFEST = {
    "name": "read_file",
    "version": "1.0",
    "category": "io",
    "inputs": {"path": "str", "encoding": "str", "max_bytes": "int"},
    "outputs": {"content": "str", "size": "int", "lines": "int"},
    "permissions": ["read"],
    "failure_modes": ["file_not_found", "permission_denied", "encoding_error"],
    "logs": ["path", "size"]
}

# Izin verilen dizinler (j.txt Section 7 - capability-based)
ALLOWED_DIRS = ["/opt/jarvis", "/home/userk", "/tmp"]


def _path_allowed(path: str) -> bool:
    p = Path(path).resolve()
    return any(str(p).startswith(d) for d in ALLOWED_DIRS)


def run(path: str, encoding: str = "utf-8", max_bytes: int = 50000) -> dict:
    if not _path_allowed(path):
        log.warning(f"Access denied: {path}")
        return {"content": "", "size": 0, "lines": 0, "error": "path_not_allowed"}

    p = Path(path)
    if not p.exists():
        log.warning(f"File not found: {path}")
        return {"content": "", "size": 0, "lines": 0, "error": "file_not_found"}

    try:
        size = p.stat().st_size
        content = p.read_text(encoding=encoding, errors="replace")
        if len(content) > max_bytes:
            content = content[:max_bytes] + "\n... [truncated]"

        lines = content.count("\n")
        log.info(f"Read: {path} ({size} bytes, {lines} lines)")
        return {"content": content, "size": size, "lines": lines, "error": None}
    except Exception as e:
        log.error(f"Read error: {e}")
        return {"content": "", "size": 0, "lines": 0, "error": str(e)}


if __name__ == "__main__":
    r = run("/opt/jarvis/memory/project_memory/MEMORY.md")
    print(f"Size: {r['size']} bytes, Lines: {r['lines']}")
    print(r['content'][:200] or "(empty)")
