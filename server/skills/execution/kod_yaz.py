"""
Skill: kod_yaz
Kategori: execution
Dosya oluşturma, güncelleme, syntax kontrol
"""
import subprocess
import logging
from pathlib import Path

log = logging.getLogger("skill.kod_yaz")

MANIFEST = {
    "name": "kod_yaz",
    "version": "1.0",
    "category": "execution",
    "inputs": {"path": "str", "content": "str", "action": "str"},
    "outputs": {"success": "bool", "result": "str"},
    "permissions": ["read", "write"],
    "failure_modes": ["path_not_allowed", "syntax_error", "write_error"],
    "logs": ["path", "action", "success"]
}

ALLOWED_DIRS = ["/opt/jarvis", "/home/userk", "/tmp"]


def _path_allowed(path: str) -> bool:
    p = Path(path).resolve()
    return any(str(p).startswith(d) for d in ALLOWED_DIRS)


def run(path: str, content: str = "", action: str = "write") -> dict:
    if not _path_allowed(path):
        return {"success": False, "result": f"Yol izin dışı: {path}", "error": "path_not_allowed"}

    p = Path(path)
    action = action.lower()
    log.info(f"kod_yaz: {action} -> {path}")

    if action in ("write", "yaz", "olustur", "create"):
        if not content:
            return {"success": False, "result": "İçerik boş.", "error": "empty_content"}
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            log.info(f"Yazıldı: {path} ({len(content)} karakter)")
            return {"success": True, "result": f"Dosya yazıldı: {path}", "error": None}
        except Exception as e:
            return {"success": False, "result": str(e), "error": "write_error"}

    if action in ("append", "ekle"):
        if not content:
            return {"success": False, "result": "İçerik boş.", "error": "empty_content"}
        try:
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n" + content)
            return {"success": True, "result": f"Eklendi: {path}", "error": None}
        except Exception as e:
            return {"success": False, "result": str(e), "error": "write_error"}

    if action in ("syntax", "kontrol", "check"):
        if not p.exists():
            return {"success": False, "result": "Dosya bulunamadı.", "error": "file_not_found"}
        try:
            r = subprocess.run(
                ["python3", "-m", "py_compile", str(p)],
                capture_output=True, text=True, timeout=10
            )
            if r.returncode == 0:
                return {"success": True, "result": f"Syntax OK: {path}", "error": None}
            else:
                return {"success": False, "result": r.stderr.strip(), "error": "syntax_error"}
        except Exception as e:
            return {"success": False, "result": str(e), "error": "check_error"}

    if action in ("oku", "read"):
        if not p.exists():
            return {"success": False, "result": "Dosya bulunamadı.", "error": "file_not_found"}
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            return {"success": True, "result": content[:3000], "error": None}
        except Exception as e:
            return {"success": False, "result": str(e), "error": "read_error"}

    return {"success": False, "result": f"Bilinmeyen işlem: {action}", "error": "unknown_action"}


if __name__ == "__main__":
    r = run("/tmp/jarvis_test.py", "print('Jarvis kod_yaz skill test OK')", "write")
    print(r)
    r2 = run("/tmp/jarvis_test.py", action="syntax")
    print(r2)
