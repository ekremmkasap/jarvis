"""
JARVIS System Tray
==================
Runs in the system tray and starts JARVIS on demand.
"""

import atexit
import ctypes
import os
import subprocess
import sys
import threading

import pystray
from PIL import Image, ImageDraw

JARVIS_DIR = os.path.dirname(os.path.abspath(__file__))
# Debug için python.exe kullan (pythonw.exe yerine) - konsol hataları görmek için
PYTHON = sys.executable.replace("pythonw.exe", "python.exe")
SCRIPT = os.path.join(JARVIS_DIR, "hey_jarvis.py")
TRAY_MUTEX = "Local\\JarvisTraySingleton"
DEFAULT_ARGS = []  # Ses modu (mikrofon açık)

_proc = None
_proc_args = None
_lock = threading.Lock()
_mutex_handle = None


def _show_message(text: str):
    ctypes.windll.user32.MessageBoxW(None, text, "JARVIS Tray", 0x40)


def _acquire_single_instance() -> bool:
    global _mutex_handle
    _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, TRAY_MUTEX)
    if not _mutex_handle:
        return True
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None
        return False
    return True


def _release_single_instance():
    global _mutex_handle
    if _mutex_handle:
        ctypes.windll.kernel32.CloseHandle(_mutex_handle)
        _mutex_handle = None


atexit.register(_release_single_instance)


def make_icon(active: bool) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (0, 200, 80) if active else (120, 120, 120)
    draw.ellipse([4, 4, 60, 60], fill=color)
    draw.rectangle([26, 14, 34, 44], fill="white")
    draw.rectangle([18, 44, 34, 52], fill="white")
    draw.rectangle([18, 44, 26, 52], fill=color)
    return img


def is_running() -> bool:
    return _proc is not None and _proc.poll() is None


def _start_process(icon, extra_args=None):
    global _proc, _proc_args
    with _lock:
        if is_running():
            return
        _proc_args = list(extra_args or DEFAULT_ARGS)
        _proc = subprocess.Popen(
            [PYTHON, SCRIPT, *_proc_args],
            cwd=JARVIS_DIR,
            env=os.environ.copy(),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
    icon.icon = make_icon(True)
    icon.title = "JARVIS - Active"
    update_menu(icon)


def start_jarvis(icon, item=None):
    _start_process(icon, DEFAULT_ARGS)


def start_jarvis_voice(icon, item=None):
    _start_process(icon, [])


def stop_jarvis(icon, item=None):
    global _proc, _proc_args
    with _lock:
        if _proc and _proc.poll() is None:
            _proc.terminate()
        _proc = None
        _proc_args = None
    icon.icon = make_icon(False)
    icon.title = "JARVIS - Idle"
    update_menu(icon)


def restart_jarvis(icon, item=None):
    args = list(_proc_args or DEFAULT_ARGS)
    stop_jarvis(icon)
    _start_process(icon, args)


def exit_app(icon, item=None):
    stop_jarvis(icon)
    icon.stop()


def update_menu(icon):
    running = is_running()
    icon.menu = pystray.Menu(
        pystray.MenuItem("🤖 JARVIS Sesli Asistan", lambda *_: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("▶ Başlat (Ses)", start_jarvis_voice, enabled=not running),
        pystray.MenuItem("▶ Başlat (Yazı)", start_jarvis, enabled=not running),
        pystray.MenuItem("■ Durdur", stop_jarvis, enabled=running),
        pystray.MenuItem("↺ Yeniden Başlat", restart_jarvis, enabled=running),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("✕ Çıkış", exit_app),
    )


def main():
    if not _acquire_single_instance():
        _show_message("JARVIS Tray zaten çalışıyor.")
        return

    icon = pystray.Icon(
        "jarvis",
        icon=make_icon(False),
        title="JARVIS - Bekliyor",
    )
    update_menu(icon)
    # Tray açılınca otomatik ses modunda başlat
    icon.run()


if __name__ == "__main__":
    main()
