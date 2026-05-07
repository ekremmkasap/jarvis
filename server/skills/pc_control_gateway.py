from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from server.security.policy_gate import evaluate_pc_action, format_policy_block_message


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "pc_control_whitelist.yaml"
LOG_PATH = ROOT / "logs" / "pc_control_audit.jsonl"
TMP_DIR = ROOT / "tmp"
_TRANSLATION = str.maketrans({
    "ı": "i", "İ": "I",
    "ç": "c", "Ç": "C",
    "ğ": "g", "Ğ": "G",
    "ö": "o", "Ö": "O",
    "ş": "s", "Ş": "S",
    "ü": "u", "Ü": "U",
})

LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: str) -> str:
    # Translate Turkish chars first (before .lower() so İ→I→i, ı→i, etc.)
    clean = str(value or "").strip().translate(_TRANSLATION).lower()
    clean = re.sub(r"[^a-z0-9/_.:\\\-\s]", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def _sanitize_argument(value: str | None) -> str:
    return str(value or "").strip().strip('"').strip("'")


def load_whitelist_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {"commands": {}}
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {"commands": {}}


def _command_rules() -> dict[str, Any]:
    payload = load_whitelist_config()
    commands = payload.get("commands") if isinstance(payload, dict) else {}
    return commands if isinstance(commands, dict) else {}


def _resolve_home_relative(path_value: str) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    home = Path.home()
    return (home / candidate).resolve(strict=False)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _resolve_allowed_file(path_value: str, rule: dict[str, Any]) -> Path:
    candidate = _resolve_home_relative(path_value)
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"Dosya bulunamadi: {candidate}")

    allowed_dirs = []
    for raw_dir in rule.get("allowed_dirs") or []:
        allowed_root = _resolve_home_relative(str(raw_dir))
        allowed_dirs.append(allowed_root)
    if not allowed_dirs:
        raise PermissionError("Allowed dir tanimi yok")

    if not any(_is_relative_to(candidate, allowed_root) for allowed_root in allowed_dirs):
        raise PermissionError("Dosya whitelist disinda")
    return candidate


def check_whitelist(command_key: str, args: str | None = None) -> tuple[bool, str, dict[str, Any]]:
    normalized_key = _normalize_text(command_key).replace("/", "")
    commands = _command_rules()
    raw_rule = commands.get(normalized_key)
    rule = raw_rule if isinstance(raw_rule, dict) else {}
    if not rule:
        return False, "command_not_whitelisted", {}

    clean_args = _sanitize_argument(args)
    if bool(rule.get("args_required")) and not clean_args:
        return False, "args_required", rule

    if normalized_key == "ac":
        apps = rule.get("apps") if isinstance(rule.get("apps"), dict) else {}
        app_name = _normalize_text(clean_args)
        if app_name not in apps:
            return False, "app_not_whitelisted", rule
        return True, "approved", rule

    if normalized_key == "dosya-gonder":
        try:
            _resolve_allowed_file(clean_args, rule)
        except (FileNotFoundError, PermissionError):
            return False, "file_not_whitelisted", rule
        return True, "approved", rule

    return True, "approved", rule


def get_system_status() -> dict[str, Any]:
    import psutil  # type: ignore

    cpu_percent = float(psutil.cpu_percent(interval=0.2))
    ram = psutil.virtual_memory()
    disk_root = Path.home().anchor or str(Path.home().drive) or str(Path.home())
    disk = psutil.disk_usage(disk_root)

    jarvis_processes: list[str] = []
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            lowered = cmdline.lower()
            if "jarvis-mission-control" in lowered or any(
                token in lowered for token in ("bridge.py", "hey_jarvis.py", "master_launcher.py")
            ):
                label = proc.info.get("name") or cmdline or str(proc.pid)
                if label not in jarvis_processes:
                    jarvis_processes.append(str(label))
        except (psutil.Error, OSError):
            continue

    return {
        "cpu_percent": round(cpu_percent, 1),
        "ram_used_mb": int(ram.used / 1024 / 1024),
        "ram_total_mb": int(ram.total / 1024 / 1024),
        "disk_used_gb": round(disk.used / 1024 / 1024 / 1024, 1),
        "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
        "jarvis_processes": jarvis_processes,
        "ts": _now_iso(),
    }


def format_system_status_text(payload: dict[str, Any]) -> str:
    return (
        "PC DURUM\n"
        f"CPU: {payload.get('cpu_percent', 0)}%\n"
        f"RAM: {payload.get('ram_used_mb', 0)}MB / {payload.get('ram_total_mb', 0)}MB\n"
        f"Disk: {payload.get('disk_used_gb', 0)}GB / {payload.get('disk_total_gb', 0)}GB\n"
        f"Jarvis processleri: {', '.join(payload.get('jarvis_processes') or []) or 'yok'}"
    )


def take_screenshot() -> str:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    target = TMP_DIR / f"pc-screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"

    try:
        import pyautogui  # type: ignore

        image = pyautogui.screenshot()
        image.save(target)
        return str(target)
    except Exception:
        from PIL import ImageGrab  # type: ignore

        image = ImageGrab.grab()
        image.save(target)
        return str(target)


def _launch_app(app_name: str, rule: dict[str, Any]) -> str:
    app_key = _normalize_text(app_name)
    apps = rule.get("apps") if isinstance(rule.get("apps"), dict) else {}
    app_rule = apps.get(app_key) if isinstance(apps.get(app_key), dict) else {}
    command = app_rule.get("command") if isinstance(app_rule, dict) else None
    if not isinstance(command, list) or not command:
        raise RuntimeError(f"Komut tanimi yok: {app_key}")
    subprocess.Popen(command, cwd=str(ROOT))
    return app_key


def _start_jarvis() -> str:
    launcher = ROOT / "JARVIS_BASLAT.bat"
    if not launcher.exists():
        raise FileNotFoundError(f"Launcher bulunamadi: {launcher}")
    subprocess.Popen(["cmd", "/c", "start", "", str(launcher)], cwd=str(ROOT))
    return str(launcher.name)


def _stop_jarvis() -> dict[str, Any]:
    import psutil  # type: ignore

    stopped: list[str] = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = " ".join(proc.info.get("cmdline") or [])
            lowered = cmdline.lower()
            if "jarvis-mission-control" not in lowered and not any(
                token in lowered for token in ("bridge.py", "hey_jarvis.py", "master_launcher.py")
            ):
                continue
            proc.terminate()
            stopped.append(str(proc.info.get("name") or proc.info.get("pid")))
        except (psutil.Error, OSError):
            continue
    return {"stopped": stopped, "count": len(stopped)}


def _run_powershell(script: str, timeout: int = 10) -> tuple[int, str, str]:
    """Run an inline PowerShell snippet and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.returncode, (result.stdout or "").strip(), (result.stderr or "").strip()


_MEDIA_VK = {
    "play_pause": 0xB3,
    "next": 0xB0,
    "prev": 0xB1,
    "stop": 0xB2,
    "vol_up": 0xAF,
    "vol_down": 0xAE,
    "vol_mute": 0xAD,
}


def _press_virtual_key(vk_code: int, repeat: int = 1) -> None:
    """Send a Windows virtual-key keypress via user32.keybd_event (no extra deps)."""
    import ctypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    for _ in range(max(1, repeat)):
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _set_volume_percent(percent: int) -> int:
    """Set master volume to an exact percentage 0–100. Falls back to keypress steps."""
    percent = max(0, min(100, int(percent)))
    try:
        from ctypes import POINTER, cast  # type: ignore

        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
        return percent
    except Exception:
        # Fallback: step up/down with media keys (coarse, 2% per press)
        _press_virtual_key(_MEDIA_VK["vol_down"], repeat=50)  # floor to 0%
        steps = round(percent / 2.0)
        _press_virtual_key(_MEDIA_VK["vol_up"], repeat=steps)
        return percent


def _get_volume_percent() -> int | None:
    try:
        from ctypes import POINTER, cast  # type: ignore

        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return int(round(volume.GetMasterVolumeLevelScalar() * 100))
    except Exception:
        return None


def _handle_set_volume(clean_args: str) -> dict[str, Any]:
    arg = _normalize_text(clean_args)
    if arg in ("yukari", "up", "arttir", "artir", "ac", "yukselt"):
        _press_virtual_key(_MEDIA_VK["vol_up"], repeat=5)
        return {"direction": "up", "steps": 5, "message": "Ses artirildi."}
    if arg in ("asagi", "down", "azalt", "indir", "kis"):
        _press_virtual_key(_MEDIA_VK["vol_down"], repeat=5)
        return {"direction": "down", "steps": 5, "message": "Ses azaltildi."}
    # Numeric percent
    percent_match = re.search(r"(\d{1,3})", arg)
    if not percent_match:
        raise ValueError(f"Ses için yüzde veya yukari/asagi gerekli: '{clean_args}'")
    percent = int(percent_match.group(1))
    applied = _set_volume_percent(percent)
    return {"percent": applied, "message": f"Ses %{applied}."}


def _handle_toggle_mute() -> dict[str, Any]:
    _press_virtual_key(_MEDIA_VK["vol_mute"])
    return {"message": "Ses mute toggle."}


def _handle_media_key(rule: dict[str, Any]) -> dict[str, Any]:
    key = str(rule.get("key") or "play_pause").lower()
    vk = _MEDIA_VK.get(key)
    if vk is None:
        raise ValueError(f"Bilinmeyen media key: {key}")
    _press_virtual_key(vk)
    labels = {
        "play_pause": "Play/Pause tuşuna basıldı.",
        "next": "Sonraki parçaya geçildi.",
        "prev": "Önceki parçaya dönüldü.",
        "stop": "Durduruldu.",
    }
    return {"key": key, "message": labels.get(key, f"Media key gönderildi: {key}")}


def _handle_lock_screen() -> dict[str, Any]:
    subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
    return {"message": "Ekran kilitlendi."}


def _handle_sleep_pc() -> dict[str, Any]:
    # First flush hybrid-sleep flags, then suspend. 0=sleep, 1=force, 0=wake-armed
    subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
    return {"message": "PC uyku moduna alındı."}


def _handle_set_brightness(clean_args: str) -> dict[str, Any]:
    percent_match = re.search(r"(\d{1,3})", clean_args or "")
    if not percent_match:
        raise ValueError(f"Parlaklık için yüzde gerekli: '{clean_args}'")
    percent = max(0, min(100, int(percent_match.group(1))))
    script = (
        "$ErrorActionPreference='Stop';"
        f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{percent})"
    )
    rc, _, stderr = _run_powershell(script, timeout=8)
    if rc != 0:
        raise RuntimeError(f"Parlaklık ayarlanamadı (masaüstü monitörde desteklenmez): {stderr[:160]}")
    return {"percent": percent, "message": f"Parlaklık %{percent}."}


def _handle_open_url(clean_args: str) -> dict[str, Any]:
    url = (clean_args or "").strip()
    if not url:
        raise ValueError("URL gerekli.")
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    subprocess.Popen(["cmd", "/c", "start", "", url], cwd=str(ROOT))
    return {"url": url, "message": f"Tarayıcıda açıldı: {url}"}


def _handle_web_search(clean_args: str, rule: dict[str, Any]) -> dict[str, Any]:
    query = (clean_args or "").strip()
    if not query:
        raise ValueError("Arama için sorgu gerekli.")
    from urllib.parse import quote_plus

    engine = str(rule.get("engine") or "google").lower()
    if engine == "youtube":
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    else:
        url = f"https://www.google.com/search?q={quote_plus(query)}"
    subprocess.Popen(["cmd", "/c", "start", "", url], cwd=str(ROOT))
    return {"engine": engine, "query": query, "url": url, "message": f"{engine}: {query}"}


_VK = {
    "ctrl": 0x11,
    "alt": 0x12,
    "shift": 0x10,
    "win": 0x5B,
    "tab": 0x09,
    "f4": 0x73,
    "enter": 0x0D,
    "esc": 0x1B,
    "space": 0x20,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "a": 0x41, "b": 0x42, "c": 0x43, "d": 0x44, "e": 0x45, "f": 0x46,
    "g": 0x47, "h": 0x48, "i": 0x49, "j": 0x4A, "k": 0x4B, "l": 0x4C,
    "m": 0x4D, "n": 0x4E, "o": 0x4F, "p": 0x50, "q": 0x51, "r": 0x52,
    "s": 0x53, "t": 0x54, "u": 0x55, "v": 0x56, "w": 0x57, "x": 0x58,
    "y": 0x59, "z": 0x5A,
}


def _send_key_combo(*key_names: str) -> None:
    """Press a combo like _send_key_combo('ctrl', 't') — hold modifiers, press last, release in reverse."""
    import ctypes

    user32 = ctypes.windll.user32
    KEYEVENTF_KEYUP = 0x0002
    codes = []
    for name in key_names:
        code = _VK.get(name.lower())
        if code is None:
            raise ValueError(f"Bilinmeyen tuş: {name}")
        codes.append(code)
    for code in codes:
        user32.keybd_event(code, 0, 0, 0)
    for code in reversed(codes):
        user32.keybd_event(code, 0, KEYEVENTF_KEYUP, 0)


def _handle_clipboard_read() -> dict[str, Any]:
    rc, out, err = _run_powershell("Get-Clipboard -Raw", timeout=5)
    if rc != 0:
        raise RuntimeError(f"Pano okunamadı: {err[:160]}")
    content = (out or "").strip()
    if not content:
        return {"content": "", "message": "Pano boş."}
    preview = content if len(content) <= 500 else content[:500] + "..."
    return {"content": content, "length": len(content), "message": f"Pano içeriği:\n{preview}"}


def _handle_clipboard_write(clean_args: str) -> dict[str, Any]:
    text = clean_args or ""
    if not text:
        raise ValueError("Panoya yazılacak metin gerekli.")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", "$input | Set-Clipboard"],
        input=text,
        capture_output=True,
        text=True,
        timeout=5,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Panoya yazılamadı: {(result.stderr or '')[:160]}")
    preview = text if len(text) <= 100 else text[:100] + "..."
    return {"length": len(text), "message": f"Panoya kopyalandı ({len(text)} karakter):\n{preview}"}


def _handle_clipboard_clear() -> dict[str, Any]:
    # Set-Clipboard reddediyor empty string; null ile temizleriz.
    rc, _, err = _run_powershell("$null | Set-Clipboard", timeout=5)
    if rc != 0:
        raise RuntimeError(f"Pano temizlenemedi: {err[:160]}")
    return {"message": "Pano temizlendi."}


def _handle_type_text(clean_args: str) -> dict[str, Any]:
    text = clean_args or ""
    if not text:
        raise ValueError("Yazılacak metin gerekli.")
    # Try pyautogui first (ASCII). Fall back to clipboard-paste for full unicode/Türkçe.
    used = "clipboard"
    try:
        if all(ord(c) < 128 for c in text):
            import pyautogui  # type: ignore
            pyautogui.typewrite(text, interval=0.01)
            used = "pyautogui"
        else:
            raise RuntimeError("unicode → paste")
    except Exception:
        _handle_clipboard_write(text)
        _send_key_combo("ctrl", "v")
    preview = text if len(text) <= 100 else text[:100] + "..."
    return {"length": len(text), "method": used, "message": f"Yazıldı ({used}): {preview}"}


def _handle_new_tab() -> dict[str, Any]:
    _send_key_combo("ctrl", "t")
    return {"message": "Yeni sekme açıldı."}


def _handle_close_tab() -> dict[str, Any]:
    _send_key_combo("ctrl", "w")
    return {"message": "Sekme kapatıldı."}


def _handle_next_tab() -> dict[str, Any]:
    _send_key_combo("ctrl", "tab")
    return {"message": "Sonraki sekmeye geçildi."}


def _handle_prev_tab() -> dict[str, Any]:
    _send_key_combo("ctrl", "shift", "tab")
    return {"message": "Önceki sekmeye dönüldü."}


def _handle_close_window() -> dict[str, Any]:
    _send_key_combo("alt", "f4")
    return {"message": "Aktif pencere kapatıldı."}


def _handle_minimize_all() -> dict[str, Any]:
    _send_key_combo("win", "d")
    return {"message": "Masaüstü gösterildi."}


def _handle_maximize_window() -> dict[str, Any]:
    _send_key_combo("win", "up")
    return {"message": "Pencere büyütüldü."}


def _handle_focus_address_bar() -> dict[str, Any]:
    _send_key_combo("ctrl", "l")
    return {"message": "Adres çubuğuna odaklanıldı."}


def _handle_active_window() -> dict[str, Any]:
    try:
        import ctypes

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value or "(başlıksız)"
        return {"title": title, "hwnd": int(hwnd), "message": f"Aktif pencere: {title}"}
    except Exception as exc:
        raise RuntimeError(f"Aktif pencere alınamadı: {exc}")


def _append_audit_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False))
        handle.write("\n")


def _safe_obsidian_log(command_key: str, args: str | None, result: str) -> None:
    try:
        from obsidian_auto_writer import auto_write_pc_action
    except Exception:
        try:
            from server.skills.obsidian_auto_writer import auto_write_pc_action  # type: ignore
        except Exception:
            return
    try:
        auto_write_pc_action(command_key, result, args=args)
    except Exception:
        LOGGER.debug("Obsidian PC action write skipped", exc_info=True)


def execute_pc_command(
    command_key: str,
    args: str | None,
    persona_id: str,
    chat_id: int,
) -> dict[str, Any]:
    clean_args = _sanitize_argument(args)
    approved, reason, rule = check_whitelist(command_key, clean_args)
    base_entry = {
        "ts": _now_iso(),
        "command_key": _normalize_text(command_key).replace("/", ""),
        "args": clean_args or None,
        "persona_id": str(persona_id or "").strip() or "jarvis",
        "chat_id": int(chat_id),
        "whitelist_approved": bool(approved),
    }

    if not approved:
        payload = {
            **base_entry,
            "ok": False,
            "reason": reason,
            "result": f"Bu komuta izin verilmiyor: {command_key}",
        }
        _append_audit_log(payload)
        return {
            "ok": False,
            "action": rule.get("action") if isinstance(rule, dict) else None,
            "message": f"Bu komuta izin verilmiyor: {command_key}",
            "audit": payload,
        }

    action = str(rule.get("action") or "").strip()
    policy_decision = evaluate_pc_action(
        command_key,
        action=action,
        args=clean_args,
        persona_id=base_entry["persona_id"],
        chat_id=base_entry["chat_id"],
        rule=rule,
        source="pc_control_gateway.execute",
    )
    if not policy_decision.allowed:
        message = format_policy_block_message(policy_decision)
        payload = {
            **base_entry,
            "ok": False,
            "reason": policy_decision.reason,
            "result": message,
            "policy_status": policy_decision.status,
            "approval_id": policy_decision.approval_id,
        }
        _append_audit_log(payload)
        return {
            "ok": False,
            "action": action or None,
            "message": message,
            "audit": payload,
            "approval_id": policy_decision.approval_id,
            "risk": policy_decision.risk,
        }

    try:
        if action == "system_status":
            data = get_system_status()
            result_payload = {
                "ok": True,
                "action": action,
                "data": data,
                "message": format_system_status_text(data),
            }
        elif action == "screenshot":
            path = take_screenshot()
            result_payload = {
                "ok": True,
                "action": action,
                "path": path,
                "message": "Ekran goruntusu hazir.",
            }
        elif action == "open_app":
            app_name = _launch_app(clean_args, rule)
            result_payload = {
                "ok": True,
                "action": action,
                "app": app_name,
                "message": f"{app_name} acildi.",
            }
        elif action == "send_file":
            resolved_file = _resolve_allowed_file(clean_args, rule)
            result_payload = {
                "ok": True,
                "action": action,
                "path": str(resolved_file),
                "message": f"Dosya hazir: {resolved_file.name}",
            }
        elif action == "start_jarvis":
            launcher = _start_jarvis()
            result_payload = {
                "ok": True,
                "action": action,
                "launcher": launcher,
                "message": "Jarvis baslatildi.",
            }
        elif action == "stop_jarvis":
            stopped = _stop_jarvis()
            result_payload = {
                "ok": True,
                "action": action,
                "stopped": stopped,
                "message": f"Jarvis kapatildi ({stopped['count']} process).",
            }
        elif action == "set_volume":
            data = _handle_set_volume(clean_args)
            result_payload = {"ok": True, "action": action, **data}
        elif action == "toggle_mute":
            data = _handle_toggle_mute()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "media_key":
            data = _handle_media_key(rule)
            result_payload = {"ok": True, "action": action, **data}
        elif action == "lock_screen":
            data = _handle_lock_screen()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "sleep_pc":
            data = _handle_sleep_pc()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "set_brightness":
            data = _handle_set_brightness(clean_args)
            result_payload = {"ok": True, "action": action, **data}
        elif action == "open_url":
            data = _handle_open_url(clean_args)
            result_payload = {"ok": True, "action": action, **data}
        elif action == "web_search":
            data = _handle_web_search(clean_args, rule)
            result_payload = {"ok": True, "action": action, **data}
        elif action == "active_window":
            data = _handle_active_window()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "clipboard_read":
            data = _handle_clipboard_read()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "clipboard_write":
            data = _handle_clipboard_write(clean_args)
            result_payload = {"ok": True, "action": action, **data}
        elif action == "clipboard_clear":
            data = _handle_clipboard_clear()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "type_text":
            data = _handle_type_text(clean_args)
            result_payload = {"ok": True, "action": action, **data}
        elif action == "new_tab":
            data = _handle_new_tab()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "close_tab":
            data = _handle_close_tab()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "next_tab":
            data = _handle_next_tab()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "prev_tab":
            data = _handle_prev_tab()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "close_window":
            data = _handle_close_window()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "minimize_all":
            data = _handle_minimize_all()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "maximize_window":
            data = _handle_maximize_window()
            result_payload = {"ok": True, "action": action, **data}
        elif action == "focus_address_bar":
            data = _handle_focus_address_bar()
            result_payload = {"ok": True, "action": action, **data}
        else:
            raise RuntimeError(f"Desteklenmeyen action: {action}")

        audit_entry = {
            **base_entry,
            "ok": True,
            "action": result_payload.get("action"),
            "result": result_payload.get("message"),
            "policy_status": policy_decision.status,
            "policy_risk": policy_decision.risk,
            "policy_audit_id": policy_decision.audit_id,
        }
        _append_audit_log(audit_entry)
        if result_payload.get("action") != "system_status":
            _safe_obsidian_log(command_key, clean_args, str(result_payload.get("message") or ""))
        result_payload["audit"] = audit_entry
        return result_payload
    except Exception as exc:  # noqa: BLE001
        audit_entry = {
            **base_entry,
            "ok": False,
            "reason": "execution_failed",
            "result": str(exc),
        }
        _append_audit_log(audit_entry)
        return {
            "ok": False,
            "action": str(rule.get("action") or "").strip(),
            "message": f"PC komutu basarisiz: {exc}",
            "audit": audit_entry,
        }


def infer_pc_command(text: str) -> dict[str, str] | None:
    normalized = _normalize_text(text)
    if not normalized or normalized.startswith("/"):
        return None

    if any(phrase in normalized for phrase in ("pc durum", "pc durumu", "sistem durumu", "cpu ram", "ram disk")):
        return {"command_key": "pc-durum", "args": ""}
    if any(phrase in normalized for phrase in ("ekran goruntusu", "ekrani goster", "screenshot", "ekrana bak")):
        return {"command_key": "ekran-goruntusu", "args": ""}
    if any(phrase in normalized for phrase in ("jarvis baslat", "jarvisi baslat")):
        return {"command_key": "jarvis-baslat", "args": ""}
    if any(phrase in normalized for phrase in ("jarvis kapat", "jarvisi kapat")):
        return {"command_key": "jarvis-kapat", "args": ""}

    # --- Faz 1 doğal dil intentleri ---

    if any(phrase in normalized for phrase in ("ekrani kilitle", "ekran kilitle", "ekrani kilit", "lock screen", "pc kilitle")):
        return {"command_key": "kilit", "args": ""}
    if any(phrase in normalized for phrase in ("uyku moduna", "pc uyu", "pcyi uyut", "bilgisayari uyut")):
        return {"command_key": "uyku", "args": ""}
    if any(phrase in normalized for phrase in ("sustur", "sesi kapat", "sesi kes", "mute")):
        return {"command_key": "sustur", "args": ""}
    if any(phrase in normalized for phrase in ("sesi ac", "mute kaldir", "unmute")):
        return {"command_key": "sustur", "args": ""}
    if any(phrase in normalized for phrase in ("duraklat", "pause", "muzigi durdur")):
        return {"command_key": "duraklat", "args": ""}
    if any(phrase in normalized for phrase in ("devam ettir", "play", "oynat")):
        return {"command_key": "devam", "args": ""}
    if any(phrase in normalized for phrase in ("sonraki sarki", "sonraki parca", "next song", "bir sonraki")):
        return {"command_key": "sonraki", "args": ""}
    if any(phrase in normalized for phrase in ("onceki sarki", "onceki parca", "prev song", "bir onceki")):
        return {"command_key": "onceki", "args": ""}
    if any(phrase in normalized for phrase in ("aktif pencere", "hangi pencere", "current window")):
        return {"command_key": "aktif-pencere", "args": ""}

    vol_pct = re.search(r"\bses(?:i)?\s+(?:yuzde\s+)?(\d{1,3})\b", normalized)
    if vol_pct:
        return {"command_key": "ses", "args": vol_pct.group(1)}
    if re.search(r"\bses(?:i)?\s+(yukari|yukselt|arttir|artir)\b", normalized):
        return {"command_key": "ses", "args": "yukari"}
    if re.search(r"\bses(?:i)?\s+(asagi|azalt|kis|indir)\b", normalized):
        return {"command_key": "ses", "args": "asagi"}

    bright_match = re.search(r"\bparlaklik(?:i)?\s+(?:yuzde\s+)?(\d{1,3})\b", normalized)
    if bright_match:
        return {"command_key": "parlaklik", "args": bright_match.group(1)}

    if any(phrase in normalized for phrase in ("adres cubugu", "adres cubuguna", "url bar")):
        return {"command_key": "adres-cubugu", "args": ""}

    url_match = re.search(r"\b(?:url|site|adres)\s+(?!cubugu)(.+)$", normalized)
    if url_match:
        return {"command_key": "url", "args": url_match.group(1).strip()}

    yt_match = re.search(r"\byoutube(?:da|de)?\s+(?:ara\s+)?(.+)$", normalized)
    if yt_match:
        return {"command_key": "youtube-ara", "args": yt_match.group(1).strip()}

    search_match = re.search(r"\b(?:google(?:da|de)?\s+ara|web(?:de|da)?\s+ara|arat)\s+(.+)$", normalized)
    if search_match:
        return {"command_key": "ara", "args": search_match.group(1).strip()}

    _APP_VARIANTS = {
        "chrome": "chrome", "vscode": "vscode", "code": "vscode",
        "notepad": "notepad", "explorer": "explorer", "spotify": "spotify", "firefox": "firefox",
        "calc": "calc", "hesap": "calc", "hesapmakinesi": "calc", "hesap makinesi": "calc",
        "whatsapp": "whatsapp", "whatsaap": "whatsapp", "whatsap": "whatsapp", "wp": "whatsapp",
        "discord": "discord", "telegram": "telegram", "teams": "teams",
        "obsidian": "obsidian", "terminal": "terminal", "cmd": "cmd",
        "powershell": "powershell", "edge": "edge",
    }
    # whats[a-z]* → whatsapp/whatsaap/whatsapapi/whatsap tüm varyantları yakalar
    _APP_RE = r"(?:chrome|firefox|vscode|code|notepad|explorer|spotify|calc|hesap(?:\s+makinesi|makinesi)?|whats[a-z]*|wp|discord|telegram|teams|obsidian|terminal|cmd|powershell|edge)"

    # Sıra 1: "ac <app>" / "baslat <app>"
    open_match = re.search(rf"\b(?:ac|baslat)\s+({_APP_RE})\b", normalized)
    if not open_match:
        # Sıra 2 (Türkçe): "<app> (uygulamasini|programini)? (ac|baslat|cagir)"
        open_match = re.search(
            rf"\b({_APP_RE})(?:\s+(?:uygulamasi(?:ni)?|programi(?:ni)?))?\s+(?:ac|baslat|cagir)\b",
            normalized,
        )
    if open_match:
        raw = open_match.group(1)
        if raw.startswith("whats"):
            canonical = "whatsapp"
        elif raw.startswith("hesap"):
            canonical = "calc"
        else:
            canonical = _APP_VARIANTS.get(raw, raw)
        return {"command_key": "ac", "args": canonical}

    file_match = re.search(
        r"\b(?:dosya(?:yi)?\s+gonder|file\s+send)\s+(.+)$",
        normalized,
    )
    if file_match:
        return {"command_key": "dosya-gonder", "args": file_match.group(1).strip()}

    # --- Faz 2: pano, sekme, pencere intentleri ---

    if any(phrase in normalized for phrase in ("pano oku", "panoyu oku", "clipboard oku", "panoda ne var")):
        return {"command_key": "pano-oku", "args": ""}
    if any(phrase in normalized for phrase in ("pano temizle", "panoyu temizle", "clipboard temizle")):
        return {"command_key": "pano-temizle", "args": ""}

    # Türkçe sıra 1: "panoya yaz <content>" / "clipboard yaz <content>"
    pano_match = re.search(r"\b(?:panoya\s+(?:yaz|kopyala)|clipboard(?:a)?\s+yaz)\s+(.+)$", normalized)
    if not pano_match:
        # Türkçe sıra 2: "panoya <content> yaz/kopyala"
        pano_match = re.search(r"\bpanoya\s+(.+?)\s+(?:yaz|kopyala)\b", normalized)
    if pano_match:
        return {"command_key": "pano-yaz", "args": pano_match.group(1).strip()}

    yaz_match = re.search(r"\b(?:yaz|type)\s+(.+)$", normalized)
    if yaz_match and not normalized.startswith("yazilim"):
        candidate = yaz_match.group(1).strip()
        if len(candidate) >= 2:
            return {"command_key": "yaz", "args": candidate}

    if any(phrase in normalized for phrase in ("yeni sekme", "sekme ac", "new tab")):
        return {"command_key": "sekme-ac", "args": ""}
    if any(phrase in normalized for phrase in ("sekmeyi kapat", "sekme kapat", "close tab")):
        return {"command_key": "sekme-kapat", "args": ""}
    if any(phrase in normalized for phrase in ("sonraki sekme", "next tab")):
        return {"command_key": "sonraki-sekme", "args": ""}
    if any(phrase in normalized for phrase in ("onceki sekme", "prev tab", "geri sekme")):
        return {"command_key": "onceki-sekme", "args": ""}
    if any(phrase in normalized for phrase in ("pencereyi kapat", "pencere kapat", "alt f4", "close window")):
        return {"command_key": "pencere-kapat", "args": ""}
    if any(phrase in normalized for phrase in ("masaustu goster", "masaustune don", "show desktop")):
        return {"command_key": "masaustu", "args": ""}
    if any(phrase in normalized for phrase in ("pencereyi buyut", "pencere buyut", "tam ekran")):
        return {"command_key": "pencere-buyut", "args": ""}

    return None


__all__ = [
    "check_whitelist",
    "execute_pc_command",
    "format_system_status_text",
    "get_system_status",
    "infer_pc_command",
    "load_whitelist_config",
    "take_screenshot",
]
