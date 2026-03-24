"""
Jarvis Computer Control Skill
Mouse ve klavye kontrolü için pyautogui kullanır.
Telegram komutları:
  /mouse [x] [y]         -> Mouse'u konuma taşı
  /tıkla [x] [y]         -> Sol tıklama
  /çifttıkla [x] [y]     -> Çift tıklama
  /sağtıkla [x] [y]      -> Sağ tıklama
  /yaz [metin]           -> Klavyeden metin yaz
  /tuş [key]             -> Tek tuş bas (enter, tab, esc, win vb.)
  /kısayol [k1+k2]       -> Tuş kombinasyonu (ctrl+c, alt+f4 vb.)
  /ekranoku              -> Ekran görüntüsü al + koordinat bilgisi
  /scroll [yukarı/aşağı] [miktar] -> Scroll
"""

import subprocess
import sys

def _ensure_pyautogui():
    try:
        import pyautogui
        return pyautogui
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyautogui", "-q"], check=True)
        import pyautogui
        return pyautogui

def mouse_move(x: int, y: int) -> str:
    pag = _ensure_pyautogui()
    pag.moveTo(x, y, duration=0.3)
    return f"✅ Mouse ({x}, {y}) konumuna taşındı."

def mouse_click(x: int, y: int, button="left", clicks=1) -> str:
    pag = _ensure_pyautogui()
    pag.click(x, y, button=button, clicks=clicks, interval=0.15)
    label = {"left": "Sol tıklama", "right": "Sağ tıklama", "middle": "Orta tıklama"}.get(button, "Tıklama")
    return f"✅ {label} ({x}, {y})"

def keyboard_type(text: str) -> str:
    pag = _ensure_pyautogui()
    pag.write(text, interval=0.05)
    return f"✅ Yazıldı: {text[:50]}{'...' if len(text) > 50 else ''}"

def keyboard_press(key: str) -> str:
    pag = _ensure_pyautogui()
    key = key.lower().strip()
    pag.press(key)
    return f"✅ Tuş basıldı: {key}"

def keyboard_hotkey(combo: str) -> str:
    pag = _ensure_pyautogui()
    keys = [k.strip() for k in combo.replace("+", " ").split()]
    pag.hotkey(*keys)
    return f"✅ Kısayol: {combo}"

def scroll(direction: str, amount: int = 3) -> str:
    pag = _ensure_pyautogui()
    clicks = amount if direction.lower() in ("yukarı", "yukari", "up") else -amount
    pag.scroll(clicks)
    return f"✅ Scroll: {direction} x{amount}"

def get_screen_size() -> str:
    pag = _ensure_pyautogui()
    w, h = pag.size()
    x, y = pag.position()
    return f"🖥️ Ekran: {w}x{h}\n🖱️ Mouse: ({x}, {y})"

def run_computer_control(cmd: str, args: str) -> str:
    """bridge.py'den çağrılacak ana dispatcher"""
    try:
        cmd = cmd.lower().strip("/")
        parts = args.split()

        if cmd in ("mouse", "git"):
            if len(parts) < 2:
                return "Kullanım: /mouse [x] [y]"
            return mouse_move(int(parts[0]), int(parts[1]))

        elif cmd in ("tıkla", "tikla", "click"):
            if len(parts) < 2:
                return "Kullanım: /tıkla [x] [y]"
            return mouse_click(int(parts[0]), int(parts[1]), "left")

        elif cmd in ("çifttıkla", "cifttikla", "dblclick"):
            if len(parts) < 2:
                return "Kullanım: /çifttıkla [x] [y]"
            return mouse_click(int(parts[0]), int(parts[1]), "left", clicks=2)

        elif cmd in ("sağtıkla", "sagtikla", "rightclick"):
            if len(parts) < 2:
                return "Kullanım: /sağtıkla [x] [y]"
            return mouse_click(int(parts[0]), int(parts[1]), "right")

        elif cmd in ("yaz", "type", "yaz"):
            if not args:
                return "Kullanım: /yaz [metin]"
            return keyboard_type(args)

        elif cmd in ("tuş", "tus", "key", "press"):
            if not args:
                return "Kullanım: /tuş [enter/tab/esc/win/...]"
            return keyboard_press(args.strip())

        elif cmd in ("kısayol", "kisayol", "hotkey"):
            if not args:
                return "Kullanım: /kısayol [ctrl+c]"
            return keyboard_hotkey(args.strip())

        elif cmd in ("scroll",):
            direction = parts[0] if parts else "aşağı"
            amount = int(parts[1]) if len(parts) > 1 else 3
            return scroll(direction, amount)

        elif cmd in ("ekranoku", "konum", "nerede"):
            return get_screen_size()

        else:
            return (
                "*Computer Control Komutları:*\n"
                "/mouse [x] [y] → Mouse taşı\n"
                "/tıkla [x] [y] → Sol tıkla\n"
                "/çifttıkla [x] [y] → Çift tıkla\n"
                "/sağtıkla [x] [y] → Sağ tıkla\n"
                "/yaz [metin] → Klavyeye yaz\n"
                "/tuş [enter] → Tuş bas\n"
                "/kısayol [ctrl+c] → Kısayol\n"
                "/scroll [yukarı/aşağı] [miktar]\n"
                "/ekranoku → Ekran boyutu + mouse konumu"
            )
    except Exception as e:
        return f"❌ Computer control hatası: {e}"
