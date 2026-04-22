#!/usr/bin/env python3
"""
JARVIS master launcher.

Single entrypoint for the local voice stack:
- bridge HTTP surface
- voice assistant
- optional desktop hologram
"""

import atexit
import json
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.request import urlopen


COLORS = {
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
    "RED": "\033[91m",
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
}

COMPONENT_COLORS = {
    "BRIDGE": COLORS["CYAN"],
    "GATEWAY": COLORS["MAGENTA"],
    "VOICE": COLORS["GREEN"],
    "TEAM": COLORS["BLUE"],
    "WATCHDOG": COLORS["YELLOW"],
    "HOLOGRAM": COLORS["GREEN"],
    "SLACK": COLORS["BLUE"],
    "SYSTEM": COLORS["BOLD"],
}


class LogWriter(threading.Thread):
    """Read child-process output and prefix it with the component name."""

    def __init__(self, stream, component_name, color):
        super().__init__(daemon=True)
        self.stream = stream
        self.component_name = component_name
        self.color = color

    def run(self):
        try:
            while True:
                line = self.stream.readline()
                if not line:
                    break
                line = line.decode("utf-8", errors="replace").rstrip()
                if not line:
                    continue
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(
                    f"{self.color}[{timestamp} {self.component_name}]"
                    f"{COLORS['RESET']} {line}"
                )
        except Exception as exc:
            print(f"{COLORS['RED']}[ERROR {self.component_name}] {exc}{COLORS['RESET']}")


class MasterLauncher:
    def __init__(self):
        self.root = Path(__file__).parent
        self.server_dir = self.root / "server"
        self.processes = {}
        self.running = True

        self.bridge_port = 8081
        self.gateway_port = 8082
        self.bridge_health_url = f"http://127.0.0.1:{self.bridge_port}/health"
        self.bridge_status_url = f"http://127.0.0.1:{self.bridge_port}/api/status"
        self.bridge_lock_file = self.server_dir / "data" / "bridge.lock"
        self.bridge_heartbeat_file = self.server_dir / "data" / "bridge_heartbeat.json"
        self.mark_xxxv_dir = self.root / "external-repos" / "Mark-XXXV"
        self._shutdown_started = False
        self.enable_hologram = os.environ.get("JARVIS_ENABLE_HOLOGRAM", "0").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        self.wait_for_gateway = os.environ.get("JARVIS_WAIT_FOR_GATEWAY", "0").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        self.voice_runtime = os.environ.get("JARVIS_VOICE_RUNTIME", "mark_xxxv").strip().lower() or "mark_xxxv"
        self.obsidian_auto_open = os.environ.get("JARVIS_OBSIDIAN_AUTO_OPEN", "1").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        self.enable_slack = os.environ.get("JARVIS_ENABLE_SLACK", "0").strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }

        self.python = r"C:\Program Files\Python311\python.exe"
        if not Path(self.python).exists():
            self.python = "python"

        self.obsidian_vault_dir = self._prepare_obsidian_environment()
        atexit.register(self._cleanup_at_exit)

    def log_system(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(
            f"{COMPONENT_COLORS['SYSTEM']}[{timestamp} SYSTEM]{COLORS['RESET']} {message}"
        )

    def start_process(self, name, command, env=None, cwd=None):
        self.log_system(f"Baslatiliyor: {name}...")

        process_env = os.environ.copy()
        if env:
            process_env.update(env)

        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

            proc = subprocess.Popen(
                command,
                cwd=str(cwd or self.root),
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                shell=False,
                creationflags=creationflags,
            )

            LogWriter(
                proc.stdout,
                name,
                COMPONENT_COLORS.get(name, COLORS["RESET"]),
            ).start()

            self.processes[name] = proc
            self.log_system(f"{name} basladi (PID: {proc.pid})")
            return proc
        except Exception as exc:
            self.log_system(f"{name} baslatilamadi: {exc}")
            return None

    def wait_for_service(self, host, port, timeout=30, name=""):
        import socket

        start = time.time()
        while time.time() - start < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()
                if result == 0:
                    self.log_system(f"{name} hazir ({host}:{port})")
                    return True
            except Exception:
                pass
            time.sleep(0.5)

        self.log_system(f"{name} timeout ({host}:{port} - {timeout}s)")
        return False

    def is_service_ready(self, host, port):
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def start_hologram_fallback(self):
        fallback_path = self.root / "server" / "ui" / "hologram_ui.py"
        if not fallback_path.exists():
            self.log_system(f"Hologram fallback bulunamadi: {fallback_path}")
            return None
        self.log_system("Electron hologram baslatilamadi; tkinter fallback aciliyor.")
        return self.start_process(
            "HOLOGRAM",
            [self.python, str(fallback_path)],
            cwd=self.root,
        )

    def _prepare_obsidian_environment(self):
        configured = os.environ.get("OBSIDIAN_VAULT_PATH", "").strip()
        if configured:
            return Path(configured).expanduser()
        try:
            from server.skills.obsidian_sync_skill import ensure_local_obsidian_vault

            vault_dir = ensure_local_obsidian_vault(self.root / "wiki")
        except Exception:
            vault_dir = self.root / "wiki"
            vault_dir.mkdir(parents=True, exist_ok=True)
        os.environ["OBSIDIAN_VAULT_PATH"] = str(vault_dir)
        return vault_dir

    def _maybe_open_obsidian(self):
        if not self.obsidian_auto_open:
            self.log_system("Obsidian auto-open kapali (JARVIS_OBSIDIAN_AUTO_OPEN=0).")
            return

        try:
            from server.skills.obsidian_sync_skill import open_obsidian_vault

            result = open_obsidian_vault(self.obsidian_vault_dir)
        except Exception as exc:
            result = f"Obsidian auto-open hatasi: {exc}"
        self.log_system(result)

    def _voice_process_spec(self):
        runtime = self.voice_runtime
        if runtime in {"mark", "mark_xxxv", "mark-xxxv", "fatihmakes"} and self.mark_xxxv_dir.exists():
            voice_env = {
                "JARVIS_RUNTIME_UI": "bridge",
                "BRIDGE_URL": f"http://127.0.0.1:{self.bridge_port}",
                "PYTHONPATH": os.pathsep.join(
                    [
                        str(self.root),
                        os.environ.get("PYTHONPATH", ""),
                    ]
                ).rstrip(os.pathsep),
            }
            return (
                "Mark-XXXV live runtime",
                [self.python, "main.py"],
                voice_env,
                self.mark_xxxv_dir,
            )

        return (
            "hey_jarvis runtime",
            [self.python, "hey_jarvis.py"],
            None,
            self.root,
        )

    def _slack_process_spec(self):
        slack_env = {
            "BRIDGE_URL": f"http://127.0.0.1:{self.bridge_port}",
            "PYTHONPATH": os.pathsep.join(
                [
                    str(self.root),
                    os.environ.get("PYTHONPATH", ""),
                ]
            ).rstrip(os.pathsep),
        }
        return [self.python, "server\\slack_bridge.py"], slack_env, self.root

    def _fetch_json(self, url, timeout=3):
        try:
            with urlopen(url, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except Exception:
            return None

    def _bridge_is_healthy(self):
        for url in (self.bridge_status_url, self.bridge_health_url):
            data = self._fetch_json(url)
            if not isinstance(data, dict):
                continue
            if str(data.get("status", "")).lower() in {"online", "healthy"}:
                return True, url
        return False, ""

    def _pid_exists(self, pid):
        if not pid or pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except PermissionError:
            return True
        except OSError:
            return False
        return True

    def _clear_stale_bridge_state(self):
        candidate_pids = set()

        try:
            if self.bridge_lock_file.exists():
                candidate_pids.add(int(self.bridge_lock_file.read_text(encoding="utf-8").strip()))
        except Exception:
            candidate_pids.add(0)

        try:
            if self.bridge_heartbeat_file.exists():
                heartbeat = json.loads(
                    self.bridge_heartbeat_file.read_text(encoding="utf-8")
                )
                candidate_pids.add(int(heartbeat.get("pid", 0)))
        except Exception:
            candidate_pids.add(0)

        live_pids = {pid for pid in candidate_pids if self._pid_exists(pid)}
        if live_pids:
            self.log_system(f"Bridge state files point to live PID(s): {sorted(live_pids)}")
            return

        removed = []
        for path in (self.bridge_lock_file, self.bridge_heartbeat_file):
            try:
                if path.exists():
                    path.unlink()
                    removed.append(path.name)
            except Exception as exc:
                self.log_system(f"Stale bridge state temizlenemedi ({path.name}): {exc}")

        if removed:
            self.log_system(f"Stale bridge state temizlendi: {', '.join(removed)}")

    def _terminate_process(self, proc):
        if proc.poll() is not None:
            return True

        if os.name == "nt":
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                proc.wait(timeout=5)
                return True
            except Exception:
                return proc.poll() is not None

        try:
            proc.terminate()
            proc.wait(timeout=5)
            return True
        except subprocess.TimeoutExpired:
            proc.kill()
            return True
        except Exception:
            return proc.poll() is not None

    def launch_all(self):
        self.log_system("")
        self.log_system(f"{COLORS['BOLD']}{'=' * 61}{COLORS['RESET']}")
        self.log_system(f"{COLORS['BOLD']}  JARVIS MASTER LAUNCHER - TEK GIRIS NOKTASI{COLORS['RESET']}")
        self.log_system(f"{COLORS['BOLD']}{'=' * 61}{COLORS['RESET']}")
        self.log_system("")
        self.log_system(f"Baslangic saati: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log_system(f"Python: {self.python}")
        self.log_system(f"Root: {self.root}")
        self.log_system(f"Obsidian vault: {self.obsidian_vault_dir}")
        self.log_system("")

        self._clear_stale_bridge_state()
        bridge_healthy, bridge_source = self._bridge_is_healthy()
        if bridge_healthy:
            self.log_system(f"Bridge zaten aktif; mevcut 8081 ornegi kullanilacak ({bridge_source})")
        elif self.is_service_ready("127.0.0.1", self.bridge_port):
            self.log_system(
                "8081 dinliyor ama Jarvis health dogrulanamadi; cakismayi buyutmemek icin yeni bridge baslatilmadi."
            )
        else:
            # --web-only Telegram'ı devre dışı bırakır — sadece hologram modunda kullan
            _bridge_args = [self.python, "server\\bridge.py"]
            if os.environ.get("JARVIS_WEB_ONLY", "0") == "1":
                _bridge_args.append("--web-only")
            self.start_process("BRIDGE", _bridge_args)
            if self.wait_for_service("127.0.0.1", self.bridge_port, timeout=30, name="Bridge HTTP"):
                bridge_healthy, bridge_source = self._bridge_is_healthy()
                if bridge_healthy:
                    self.log_system(f"Bridge health dogrulandi ({bridge_source})")
                else:
                    self.log_system("Bridge portu acildi ama health endpoint dogrulanamadi.")
            else:
                self.log_system("Bridge hazir degil; voice runtime yerel Ollama fallback ile devam edecek.")
        time.sleep(2)

        if self.wait_for_gateway:
            if not self.wait_for_service("127.0.0.1", self.gateway_port, timeout=30, name="Gateway"):
                self.log_system("Gateway hazir degil ama devam ediliyor.")
            time.sleep(2)
        else:
            self.log_system("Gateway recovery boot disinda tutuldu (JARVIS_WAIT_FOR_GATEWAY=0).")

        if self.enable_slack:
            slack_command, slack_env, slack_cwd = self._slack_process_spec()
            self.start_process("SLACK", slack_command, env=slack_env, cwd=slack_cwd)
            time.sleep(1)
        else:
            self.log_system("Slack bridge kapali (JARVIS_ENABLE_SLACK=0).")

        voice_label, voice_command, voice_env, voice_cwd = self._voice_process_spec()
        self.log_system(f"Voice runtime secildi: {voice_label}")
        self.start_process(
            "VOICE",
            voice_command,
            env=voice_env,
            cwd=voice_cwd,
        )
        time.sleep(1)

        hologram_path = self.root / "apps" / "desktop-hologram"
        if self.enable_hologram and hologram_path.exists():
            npm_cmd = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
            hologram_env = os.environ.copy()
            # Swarm modu — tek pencerede 7 ajan (ayrı BrowserWindow YOK)
            if os.environ.get("JARVIS_SWARM_HOLOGRAM", "0") == "1":
                hologram_env["JARVIS_SWARM_HOLOGRAM"] = "1"
                self.log_system("Hologram: SWARM modu aktif (tek pencere, 7 ajan)")
            hologram_proc = self.start_process(
                "HOLOGRAM",
                [npm_cmd, "start"],
                cwd=hologram_path,
                env=hologram_env,
            )
            time.sleep(3)
            if hologram_proc is None or hologram_proc.poll() is not None:
                self.processes.pop("HOLOGRAM", None)
                self.start_hologram_fallback()
        elif not self.enable_hologram:
            self.log_system("Hologram kapali (JARVIS_ENABLE_HOLOGRAM=0).")
        else:
            self.log_system(f"Hologram bulunamadi: {hologram_path}")
            self.start_hologram_fallback()

        self._maybe_open_obsidian()

        self.log_system("")
        self.log_system(f"{COLORS['BOLD']}Canonical recovery stack baslatildi.{COLORS['RESET']}")
        self.log_system("Yazili komutlar: /takim, /ses, /help")
        self.log_system("Gateway/OpenCode varsayilan recovery boot disinda tutulur.")
        self.log_system(f"{COLORS['RED']}Cikmak: Ctrl+C{COLORS['RESET']}")
        self.log_system("")

    def monitor(self):
        while self.running:
            time.sleep(5)
            dead = []
            for name, proc in list(self.processes.items()):
                if proc.poll() is not None:
                    dead.append(name)
                    self.processes.pop(name, None)

            if dead:
                self.log_system(f"Kapanan bilesen: {', '.join(dead)}")

    def _cleanup_at_exit(self):
        if self._shutdown_started or not self.processes:
            return
        self.shutdown()

    def _handle_signal(self, signum, frame):
        self.shutdown(signum=signum, frame=frame)
        raise SystemExit(0)

    def shutdown(self, signum=None, frame=None):
        if self._shutdown_started:
            return
        self._shutdown_started = True
        self.running = False
        self.log_system("")
        self.log_system(f"{COLORS['RED']}Kapatiliyor...{COLORS['RESET']}")
        self.log_system("")

        for name in reversed(list(self.processes.keys())):
            proc = self.processes[name]
            self.log_system(f"Kapatiliyor: {name} (PID: {proc.pid})")
            try:
                if self._terminate_process(proc):
                    self.log_system(f"{name} kapatildi")
                else:
                    self.log_system(f"{name} kapatilamadi")
            except Exception as exc:
                self.log_system(f"{name} kapatilamadi: {exc}")

        self.log_system("")
        self.log_system(f"{COLORS['GREEN']}JARVIS kapatildi.{COLORS['RESET']}")

    def run(self):
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        try:
            self.launch_all()
            self.monitor()
        except KeyboardInterrupt:
            self.shutdown()


if __name__ == "__main__":
    launcher = MasterLauncher()
    launcher.run()
