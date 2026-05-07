#!/usr/bin/env python3
"""
JARVIS Team Launcher — Tum agent'lari 1 pencerede baslatir
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AGENTS = [
    ("Demir", "demir", "Backend API"),
    ("Selin", "selin", "Voice+Hologram"),
    ("Kaan", "kaan", "Video+Workspace"),
    ("Celik", "celik", "Security"),
]

_lock = threading.Lock()
_processes = {}


def log_agent(agent_name: str, message: str):
    with _lock:
        print(f"[{agent_name.upper()}] {message}")


def run_agent(agent_name: str, agent_code: str, agent_desc: str):
    log_agent(agent_name, f"({agent_desc}) baslatiliyor...")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(ROOT / "server" / "agents" / "agent_runner.py"), agent_code],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        _processes[agent_name] = proc
        log_agent(agent_name, "Aktif")

        for line in proc.stdout or []:
            log_agent(agent_name, line.strip())

        proc.wait()
        returncode = proc.returncode
        if returncode != 0:
            log_agent(agent_name, f"Hata: exit code {returncode}")
        else:
            log_agent(agent_name, "Kapandi")
    except Exception as e:
        log_agent(agent_name, f"HATA: {e}")
    finally:
        _processes.pop(agent_name, None)


def main():
    print("\n" + "=" * 50)
    print("   JARVIS TEAM LAUNCHER")
    print("=" * 50 + "\n")

    threads = []
    for agent_name, agent_code, agent_desc in AGENTS:
        thread = threading.Thread(
            target=run_agent,
            args=(agent_name, agent_code, agent_desc),
            daemon=False,
            name=f"launcher_{agent_name}",
        )
        threads.append(thread)
        thread.start()
        time.sleep(0.5)

    log_agent("LAUNCHER", "Tum agent'lar baslatildi. Kapatmak icin Ctrl+C basiniz.")
    print()

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\n\n[!] Kapatiliyor...")
        for agent_name, proc in list(_processes.items()):
            try:
                log_agent(agent_name, "Durduriliyor...")
                proc.terminate()
                proc.wait(timeout=5)
            except Exception as e:
                log_agent(agent_name, f"Kill hatasi: {e}")
        sys.exit(0)


if __name__ == "__main__":
    main()
