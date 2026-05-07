"""
Jarvis Dual-Monitor Vision Skill
==================================
Çift monitör destekli ekran analizi.

Mevcut vision_skill.py sadece Telegram fotoğrafı analiz ediyordu.
Bu modül:
  - Tüm bağlı monitörlerin ekran görüntüsünü alır (mss veya pyautogui fallback)
  - Her monitörü ayrı ayrı veya birleştirerek tek bağlamda analiz eder
  - Ollama veya OpenAI Vision API ile içerik döner

Komutlar (bridge.py):
  /ekrantara [monitör?]   → Ekran(lar) analiz et (1, 2 veya "hepsi")
  /ekrananaliz [soru]     → Ekranı al + soruyu yanıtla
"""

from __future__ import annotations

import base64
import json
import os
import tempfile
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Bağımlılıklar
# ---------------------------------------------------------------------------

def _get_mss():
    """mss modülünü import et, yoksa yükle."""
    try:
        import mss
        return mss
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "mss", "-q"], check=True)
        import mss
        return mss


def _get_pil():
    try:
        from PIL import Image
        return Image
    except ImportError:
        import subprocess, sys
        subprocess.run([sys.executable, "-m", "pip", "install", "Pillow", "-q"], check=True)
        from PIL import Image
        return Image


# ---------------------------------------------------------------------------
# Ekran yakalama
# ---------------------------------------------------------------------------

def get_monitor_count() -> int:
    """Sistemdeki monitör sayısını döner."""
    try:
        mss = _get_mss()
        with mss.mss() as sct:
            # mss.monitors[0] = tüm ekranlar birleşik, [1..] = tek tek
            return len(sct.monitors) - 1  # 0 indexi hariç
    except Exception:
        return 1


def capture_monitor(monitor_index: int = 0) -> str | None:
    """
    Belirtilen monitörün ekran görüntüsünü geçici dosyaya kaydeder.
    
    Args:
        monitor_index: 0 = tüm ekranlar birleşik, 1 = 1. monitör, 2 = 2. monitör vb.
    
    Returns:
        Geçici dosya yolu veya None (hata durumunda)
    """
    try:
        mss = _get_mss()
        with mss.mss() as sct:
            monitors = sct.monitors
            if monitor_index >= len(monitors):
                monitor_index = 0  # Fallback: tüm ekranlar
            
            monitor = monitors[monitor_index]
            screenshot = sct.grab(monitor)
            
            # PNG olarak kaydet
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp.close()
            
            # mss raw bytes → Pillow ile kaydet
            Image = _get_pil()
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            img.save(tmp.name, "PNG")
            return tmp.name
    except Exception as exc:
        print(f"[DualVision] Ekran yakalama hatası (monitor {monitor_index}): {exc}")
        return None


def capture_all_monitors() -> list[tuple[int, str]]:
    """
    Tüm monitörlerin ekran görüntüsünü alır.
    
    Returns:
        [(monitor_index, filepath), ...] — başarılı olanlar
    """
    count = get_monitor_count()
    results: list[tuple[int, str]] = []
    for i in range(1, count + 1):  # 1-indexed: birinci monitör = 1
        path = capture_monitor(i)
        if path:
            results.append((i, path))
    # Hiç yoksa birleşik ekranı dene
    if not results:
        path = capture_monitor(0)
        if path:
            results.append((0, path))
    return results


def merge_screenshots(filepaths: list[str]) -> str | None:
    """
    Birden fazla ekran görüntüsünü yatay olarak birleştirir.
    Tek görsel olarak analiz için kullanılır.
    """
    if not filepaths:
        return None
    if len(filepaths) == 1:
        return filepaths[0]
    try:
        Image = _get_pil()
        images = [Image.open(p) for p in filepaths]
        total_width = sum(img.width for img in images)
        max_height = max(img.height for img in images)
        merged = Image.new("RGB", (total_width, max_height), (0, 0, 0))
        x_offset = 0
        for img in images:
            merged.paste(img, (x_offset, 0))
            x_offset += img.width
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.close()
        merged.save(tmp.name, "PNG")
        return tmp.name
    except Exception as exc:
        print(f"[DualVision] Görsel birleştirme hatası: {exc}")
        return filepaths[0]  # Fallback: ilk ekran


# ---------------------------------------------------------------------------
# Ollama Vision analizi
# ---------------------------------------------------------------------------

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "moondream:latest")


def _img_to_b64(filepath: str) -> str:
    with open(filepath, "rb") as fh:
        return base64.b64encode(fh.read()).decode("utf-8")


def _analyze_with_ollama(image_path: str, prompt: str) -> str:
    """Tek görsel için Ollama vision analizi."""
    img_b64 = _img_to_b64(image_path)
    payload = json.dumps({
        "model": VISION_MODEL,
        "prompt": prompt,
        "images": [img_b64],
        "stream": False,
        "options": {"temperature": 0.4, "num_predict": 600},
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            return data.get("response", "").strip() or "❌ Ollama boş yanıt döndü."
    except Exception as exc:
        return f"❌ Ollama bağlantı hatası: {exc}"


# ---------------------------------------------------------------------------
# Ana analiz fonksiyonları
# ---------------------------------------------------------------------------

def analyze_screen(
    monitor_index: int | None = None,
    prompt: str = "Bu ekranda ne görüyorsun? Her detayı Türkçe açıkla.",
    merge: bool = True,
) -> str:
    """
    Tek veya tüm monitörleri analiz eder.
    
    Args:
        monitor_index: None = tüm monitörler, int = belirtilen monitör
        prompt: Analiz sorusu
        merge: True ise tüm ekranlar birleştirilir, False ise ayrı ayrı analiz
    
    Returns:
        Analiz sonucu metni
    """
    count = get_monitor_count()
    
    if monitor_index is not None:
        # Tek monitör
        path = capture_monitor(monitor_index)
        if not path:
            return f"❌ Monitör {monitor_index} yakalanamadı."
        result = _analyze_with_ollama(path, prompt)
        try:
            os.unlink(path)
        except Exception:
            pass
        return f"🖥️ **Monitör {monitor_index} Analizi [{VISION_MODEL}]**\n\n{result}"
    
    # Tüm monitörler
    captures = capture_all_monitors()
    if not captures:
        return "❌ Hiçbir ekran yakalanamadı."
    
    header = f"🖥️ **{count} Monitör Analizi [{VISION_MODEL}]**\n"
    
    if merge and len(captures) > 1:
        # Birleştirerek tek seferde analiz et
        filepaths = [p for _, p in captures]
        merged_path = merge_screenshots(filepaths)
        if merged_path:
            result = _analyze_with_ollama(
                merged_path,
                prompt + f" (Not: Bu görsel {len(captures)} monitörün yan yana birleştirilmiş halidir.)",
            )
            for p in filepaths + [merged_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass
            return f"{header}\n{result}"
    
    # Her monitörü ayrı analiz et
    parts: list[str] = [header]
    for idx, path in captures:
        label = "Tüm Ekranlar" if idx == 0 else f"Monitör {idx}"
        result = _analyze_with_ollama(path, prompt)
        parts.append(f"\n**— {label} —**\n{result}")
        try:
            os.unlink(path)
        except Exception:
            pass
    return "\n".join(parts)


def handle_vision_command(cmd: str, args: str) -> str:
    """
    bridge.py dispatcher — /ekrantara ve /ekrananaliz komutları.
    """
    cmd = cmd.lower().strip("/").strip()
    args = args.strip()
    
    if cmd in ("ekrantara", "screenshot", "ekran"):
        # /ekrantara 2  → 2. monitör
        # /ekrantara    → tüm monitörler
        if args.isdigit():
            return analyze_screen(monitor_index=int(args))
        return analyze_screen()
    
    elif cmd in ("ekrananaliz", "ekran-analiz", "screenanalysis"):
        prompt = args if args else "Bu ekranda ne görüyorsun? Detaylı açıkla."
        return analyze_screen(prompt=prompt)
    
    count = get_monitor_count()
    return (
        f"🖥️ *Dual Monitor Vision — {count} monitör algılandı*\n"
        "/ekrantara → Tüm ekranları analiz et\n"
        "/ekrantara [1/2] → Belirli monitörü analiz et\n"
        "/ekrananaliz [soru] → Ekrana bakarak soruyu yanıtla"
    )


__all__ = [
    "get_monitor_count",
    "capture_monitor",
    "capture_all_monitors",
    "analyze_screen",
    "handle_vision_command",
]
