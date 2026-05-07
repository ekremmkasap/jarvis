from __future__ import annotations

import json
import os
import threading
import tkinter as tk
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


BACKEND_URL = os.environ.get("JARVIS_BACKEND_URL", "http://127.0.0.1:8081").rstrip("/")
POLL_INTERVAL_MS = 3000
ANIMATION_INTERVAL_MS = 40
STATE_COLORS = {
    "IDLE": "#2f8cff",
    "LISTENING": "#00d9ff",
    "THINKING": "#8b7dff",
    "SPEAKING": "#27ff95",
    "MUTED": "#ffbf47",
    "OFFLINE": "#5f6d7a",
}


class HologramFallbackUI:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Jarvis Hologram Fallback")
        self.root.configure(bg="black")
        self.root.geometry("320x360")
        self.root.resizable(False, False)

        self.phase = "IDLE"
        self.detail = "Bridge baglantisi bekleniyor."
        self.angle = 0
        self.tray_icon = None

        shell = tk.Frame(self.root, bg="black")
        shell.pack(fill="both", expand=True, padx=18, pady=18)

        self.canvas = tk.Canvas(shell, width=220, height=220, bg="black", highlightthickness=0)
        self.canvas.pack(pady=(8, 16))

        self.status_label = tk.Label(
            shell,
            text=self.phase,
            fg="#d7ebff",
            bg="black",
            font=("Segoe UI", 16, "bold"),
        )
        self.status_label.pack()

        self.detail_label = tk.Label(
            shell,
            text=self.detail,
            fg="#8fb6d8",
            bg="black",
            wraplength=260,
            justify="center",
            font=("Segoe UI", 10),
        )
        self.detail_label.pack(pady=(10, 0))

        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)
        self._start_tray()
        self._animate()
        self._schedule_poll()

    def _hide_window(self) -> None:
        self.root.withdraw()

    def _show_window(self) -> None:
        self.root.deiconify()
        self.root.lift()

    def _quit(self) -> None:
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.root.quit()

    def _start_tray(self) -> None:
        try:
            import pystray
            from PIL import Image, ImageDraw
        except Exception:
            return

        def _build_image():
            image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            draw.ellipse((8, 8, 56, 56), outline="#2f8cff", width=4)
            draw.ellipse((24, 24, 40, 40), fill="#00d9ff")
            return image

        menu = pystray.Menu(
            pystray.MenuItem("Goster", lambda: self.root.after(0, self._show_window)),
            pystray.MenuItem("Gizle", lambda: self.root.after(0, self._hide_window)),
            pystray.MenuItem("Cikis", lambda: self.root.after(0, self._quit)),
        )
        self.tray_icon = pystray.Icon("jarvis-hologram", _build_image(), "Jarvis Hologram", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True, name="jarvis-hologram-tray").start()

    def _fetch_health_payload(self) -> dict:
        request = Request(f"{BACKEND_URL}/health", headers={"User-Agent": "Jarvis-Hologram-Fallback"})
        with urlopen(request, timeout=4) as response:
            return json.loads(response.read().decode("utf-8", errors="replace"))

    def _schedule_poll(self) -> None:
        threading.Thread(target=self._poll_bridge_once, daemon=True, name="jarvis-hologram-poll").start()
        self.root.after(POLL_INTERVAL_MS, self._schedule_poll)

    def _poll_bridge_once(self) -> None:
        try:
            payload = self._fetch_health_payload()
            live = payload.get("live", {}) if isinstance(payload.get("live"), dict) else {}
            voice = live.get("voice", {}) if isinstance(live.get("voice"), dict) else {}
            phase = str(payload.get("voice_state") or voice.get("phase") or "IDLE").strip().upper() or "IDLE"
            detail = str(payload.get("voice_detail") or voice.get("detail") or "Bridge bagli").strip() or "Bridge bagli"
        except URLError:
            phase = "OFFLINE"
            detail = "Bridge erisilemiyor."
        except Exception as exc:
            phase = "OFFLINE"
            detail = f"Hata: {str(exc)[:120]}"
        self.root.after(0, lambda: self._apply_state(phase, detail))

    def _apply_state(self, phase: str, detail: str) -> None:
        self.phase = phase if phase in STATE_COLORS else "IDLE"
        self.detail = detail
        self.status_label.configure(text=self.phase)
        self.detail_label.configure(text=self.detail)

    def _animate(self) -> None:
        self.canvas.delete("all")
        color = STATE_COLORS.get(self.phase, STATE_COLORS["IDLE"])
        self.canvas.create_oval(28, 28, 192, 192, outline="#12324c", width=2)
        self.canvas.create_arc(
            28,
            28,
            192,
            192,
            start=self.angle,
            extent=270,
            style="arc",
            outline=color,
            width=8,
        )
        self.canvas.create_oval(72, 72, 148, 148, outline="#254f73", width=2)
        self.canvas.create_oval(92, 92, 128, 128, fill=color, outline="")
        self.angle = (self.angle + 4) % 360
        self.root.after(ANIMATION_INTERVAL_MS, self._animate)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    HologramFallbackUI().run()


if __name__ == "__main__":
    main()
