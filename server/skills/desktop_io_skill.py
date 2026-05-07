"""
Jarvis Desktop I/O Skill
========================
Masaüstünde dosya oluşturma, not defteri açma ve dikte etme yeteneği.

Desteklenen Komutlar (bridge.py + Telegram):
  /notaç [dosya_adı]         → Notepad açar + boş dosya oluşturur
  /notyaz [dosya_adı] [içerik] → Dosyaya metin yazar / ekler
  /dosyaoluştur [yol] [içerik] → Belirtilen yola dosya oluşturur
  /dosyaoku [yol]             → Dosya içeriğini okur

Intent patterns (voice/chat):
  "not defteri aç ..." → _handle_open_notepad()
  "... yaz / yaza" / "şunu not et" → _handle_write_note()
  "dosya oluştur"     → _handle_create_file()
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Varsayılan masaüstü dizini — env varsa orası kullanılır
_DEFAULT_DESKTOP = Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Desktop"
DESKTOP_PATH = Path(os.environ.get("JARVIS_DESKTOP_PATH", str(_DEFAULT_DESKTOP)))

# Güvenli izin verilen dizinler (path traversal önlemi)
_ALLOWED_DIRS: tuple[Path, ...] = (
    DESKTOP_PATH,
    Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Documents",
    Path(os.environ.get("USERPROFILE", os.path.expanduser("~"))) / "Downloads",
)

_UNSAFE_RE = re.compile(r"\.\.|[<>:\"|?*]")


# ---------------------------------------------------------------------------
# Güvenlik
# ---------------------------------------------------------------------------

def _safe_path(filename: str, base_dir: Path = DESKTOP_PATH) -> Path:
    """
    Verilen dosya adını güvenli bir şeye dönüştür.
    Path traversal girişimlerini engeller.
    """
    clean_name = _UNSAFE_RE.sub("_", filename.strip().replace("/", "_").replace("\\", "_"))
    if not clean_name:
        clean_name = f"jarvis_not_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    target = (base_dir / clean_name).resolve()
    # Hedef izin verilen dizinlerde mi?
    for allowed in _ALLOWED_DIRS:
        try:
            target.relative_to(allowed.resolve())
            return target
        except ValueError:
            continue
    # Güvenli değilse masaüstüne at
    return (DESKTOP_PATH / clean_name).resolve()


def _normalize_intent_text(value: str) -> str:
    return (
        str(value or "")
        .replace("ı", "i")
        .replace("İ", "I")
        .replace("ğ", "g")
        .replace("Ğ", "G")
        .replace("ş", "s")
        .replace("Ş", "S")
        .replace("ç", "c")
        .replace("Ç", "C")
        .replace("ö", "o")
        .replace("Ö", "O")
        .replace("ü", "u")
        .replace("Ü", "U")
        .lower()
    )


# ---------------------------------------------------------------------------
# Temel işlemler
# ---------------------------------------------------------------------------

def create_file(filename: str, content: str = "", base_dir: Path = DESKTOP_PATH) -> dict:
    """
    Dosya oluşturur ve içeriğini yazar.
    
    Returns:
        {"success": bool, "path": str, "message": str}
    """
    target = _safe_path(filename, base_dir)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # Eğer dosya yoksa oluştur; varsa append et
        mode = "a" if target.exists() else "w"
        with open(target, mode, encoding="utf-8") as fh:
            if mode == "a" and content:
                fh.write(f"\n{content}")
            elif content:
                fh.write(content)
        return {
            "success": True,
            "path": str(target),
            "message": f"✅ Dosya oluşturuldu: {target.name}",
        }
    except Exception as exc:
        return {"success": False, "path": "", "message": f"❌ Dosya oluşturma hatası: {exc}"}


def write_to_file(filename: str, content: str, base_dir: Path = DESKTOP_PATH, overwrite: bool = False) -> dict:
    """
    Mevcut dosyaya metin ekler veya üstüne yazar.
    """
    target = _safe_path(filename, base_dir)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "w" if overwrite else "a"
        with open(target, mode, encoding="utf-8") as fh:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            prefix = f"\n[{timestamp}] " if mode == "a" else ""
            fh.write(f"{prefix}{content}\n")
        return {
            "success": True,
            "path": str(target),
            "message": f"✅ Yazıldı → {target.name}",
        }
    except Exception as exc:
        return {"success": False, "path": "", "message": f"❌ Yazma hatası: {exc}"}


def read_file(filepath: str) -> dict:
    """Dosya içeriğini okur (max 5000 karakter)."""
    target = Path(filepath.strip()).expanduser()
    if not target.exists():
        return {"success": False, "content": "", "message": f"❌ Dosya bulunamadı: {filepath}"}
    if not target.is_file():
        return {"success": False, "content": "", "message": "❌ Bu bir dosya değil."}
    try:
        content = target.read_text(encoding="utf-8", errors="ignore")[:5000]
        return {"success": True, "content": content, "message": f"📄 {target.name} ({len(content)} karakter)"}
    except Exception as exc:
        return {"success": False, "content": "", "message": f"❌ Okuma hatası: {exc}"}


def open_notepad(filepath: str | None = None) -> dict:
    """
    Windows Notepad'i açar.
    filepath verilmezse geçici bir not dosyası oluşturup açar.
    """
    try:
        if filepath is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(DESKTOP_PATH / f"jarvis_not_{ts}.txt")
        target = Path(filepath)
        # Dosya yoksa boş oluştur ki Notepad hata vermesin
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
        if sys.platform == "win32":
            subprocess.Popen(["notepad.exe", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return {"success": True, "path": str(target), "message": f"📝 Notepad açıldı: {target.name}"}
    except Exception as exc:
        return {"success": False, "path": "", "message": f"❌ Notepad açılamadı: {exc}"}


# ---------------------------------------------------------------------------
# Intent Handlers (bridge.py hook'ları için)
# ---------------------------------------------------------------------------

_NOTE_INTENT_RE = re.compile(
    r"(not\s*al|not\s*defteri|sunu\s*not\s*et|yaz[a]?|kaydet|dosya\s*olustur|txt\s*olustur)",
    re.IGNORECASE | re.UNICODE,
)
_OPEN_INTENT_RE = re.compile(
    r"(not\s*defteri\s*ac|notepad\s*ac|ac\s*not\s*defteri)",
    re.IGNORECASE | re.UNICODE,
)
_CREATE_INTENT_RE = re.compile(
    r"(masaustunde.*(?:txt|dosya).*(?:olustur|ac)|(?:txt|dosya)\s*olustur)",
    re.IGNORECASE | re.UNICODE,
)


def detect_desktop_intent(message: str) -> str | None:
    """
    Mesajın masaüstü dosya işlemi içerip içermediğini tespit eder.
    Returns: "open_notepad" | "write_note" | "create_file" | None
    """
    normalized = _normalize_intent_text(message)
    if _OPEN_INTENT_RE.search(normalized):
        return "open_notepad"
    if _CREATE_INTENT_RE.search(normalized):
        return "create_file"
    if _NOTE_INTENT_RE.search(normalized):
        return "write_note"
    return None


def handle_desktop_command(cmd: str, args: str) -> str:
    """
    bridge.py'den çağrılacak ana dispatcher.
    
    Desteklenen /komutlar:
      /notaç [dosya_adı]
      /notyaz [dosya_adı]|[içerik]
      /dosyaoluştur [dosya_adı]|[içerik]
      /dosyaoku [yol]
    """
    cmd = cmd.lower().strip("/").strip()
    args = args.strip()

    if cmd in ("notaç", "notac", "notepad"):
        filepath = str(DESKTOP_PATH / args) if args else None
        result = open_notepad(filepath)
        return result["message"]

    elif cmd in ("notyaz", "yaz", "notaleyaz"):
        # Format: dosya_adı|içerik  veya sadece içerik → varsayılan dosya adı
        if "|" in args:
            fname, content = args.split("|", 1)
        else:
            fname = f"jarvis_notlar_{datetime.now().strftime('%Y%m%d')}.txt"
            content = args
        result = write_to_file(fname.strip(), content.strip())
        return result["message"]

    elif cmd in ("dosyaoluştur", "dosyaolustur", "dosyaac", "dosya", "create"):
        if "|" in args:
            fname, content = args.split("|", 1)
        else:
            fname, content = args, ""
        result = create_file(fname.strip(), content.strip())
        return result["message"]

    elif cmd in ("dosyaoku", "oku", "read"):
        result = read_file(args)
        if result["success"]:
            return f"{result['message']}\n\n{result['content'][:2000]}"
        return result["message"]

    else:
        return (
            "📁 *Desktop I/O Komutları:*\n"
            "/notaç [dosya_adı] → Notepad açar\n"
            "/notyaz [dosya]|[içerik] → Dosyaya yazar\n"
            "/dosyaoluştur [dosya]|[içerik] → Dosya oluşturur\n"
            "/dosyaoku [yol] → Dosya okur"
        )


# ---------------------------------------------------------------------------
# Voice / Chat intent handler (bridge.py APPEND için)
# ---------------------------------------------------------------------------

def handle_note_intent(message: str, persona_id: str = "jarvis") -> str | None:
    """
    Sesli / chat komutlardaki 'not al', 'yaz', 'kaydet' intentini işler.
    
    Eğer mesaj not alma, dosya oluşturma niyeti taşıyorsa dosyayı yazar
    ve kullanıcıya bilgi mesajı döner. Yoksa None döner (normal akış devam eder).
    """
    intent = detect_desktop_intent(message)
    if intent is None:
        return None

    if intent == "open_notepad":
        result = open_notepad()
        return result["message"]

    # Varsayılan günlük not dosyası
    today = datetime.now().strftime("%Y-%m-%d")
    filename = f"jarvis_not_{today}.txt"

    # Mesajı temizle — intent kelimelerini çıkar
    clean_content = re.sub(
        r"(not\s*al|not\s*defteri|şunu\s*not\s*et|sunu\s*not\s*et|yaz[a]?|kaydet|dosya\s*oluştur|dosya\s*olustur|txt\s*oluştur|txt\s*olustur|masaüstünde|masaustunde|:)\s*",
        "",
        message,
        flags=re.IGNORECASE | re.UNICODE,
    ).strip()

    if intent == "create_file":
        result = create_file(filename, clean_content)
        return result["message"]

    if not clean_content:
        # Sadece "not al" yazılmış, içerik yok → notepad aç
        result = open_notepad(str(DESKTOP_PATH / filename))
        return result["message"] + "\n📝 Notunuzu yazabilirsiniz."

    result = write_to_file(filename, clean_content)
    return result["message"] + f"\n📄 '{clean_content[:50]}...' kaydedildi." if len(clean_content) > 50 else result["message"]


__all__ = [
    "create_file",
    "write_to_file",
    "read_file",
    "open_notepad",
    "handle_desktop_command",
    "handle_note_intent",
    "detect_desktop_intent",
    "DESKTOP_PATH",
]
