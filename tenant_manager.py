#!/usr/bin/env python3
"""
JARVIS — tenant_manager.py
Tum tenant'lari yonetir. Her aktif tenant icin jarvis_tenant_bot.py'yi subprocess olarak calistirir.
Kullanim: python3 /opt/jarvis/tenant_manager.py
"""

import os, sys, json, time, logging, subprocess, signal
from datetime import datetime
from pathlib import Path

TENANTS_DIR  = "/opt/jarvis/tenants"
BOT_SCRIPT   = "/opt/jarvis/jarvis_tenant_bot.py"
PYTHON       = sys.executable
CHECK_INTERVAL = 30   # saniyede bir tenant durumlarini kontrol et

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [manager] %(message)s",
    handlers=[
        logging.FileHandler("/opt/jarvis/tenants/manager.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("manager")

# tenant_id -> subprocess.Popen
PROCESSES: dict[str, subprocess.Popen] = {}


def load_tenant_configs() -> list[dict]:
    """Tum tenant config.json dosyalarini yukle"""
    configs = []
    tenants_path = Path(TENANTS_DIR)
    for config_path in tenants_path.glob("*/config.json"):
        tenant_id = config_path.parent.name
        if tenant_id.startswith("_"):  # _template gibi ozel klasorler
            continue
        try:
            with open(config_path) as f:
                cfg = json.load(f)
            cfg["_config_path"] = str(config_path)
            configs.append(cfg)
        except Exception as e:
            log.error(f"Config yuklenemedi: {config_path} — {e}")
    return configs


def is_payment_valid(cfg: dict) -> bool:
    """Odeme gecerliligi kontrolu (simdilik basit tarih kontrolu)"""
    expires_at = cfg.get("expires_at")
    if expires_at is None:
        return True  # Surekli aktif (owner gibi)
    try:
        exp = datetime.fromisoformat(expires_at)
        return exp > datetime.now()
    except Exception:
        return False


def start_tenant(cfg: dict):
    """Tenant bot'unu baslat"""
    tid = cfg["tenant_id"]
    config_path = cfg["_config_path"]

    proc = subprocess.Popen(
        [PYTHON, BOT_SCRIPT, "--config", config_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    PROCESSES[tid] = proc
    log.info(f"[{tid}] BASLATILDI — PID:{proc.pid} Plan:{cfg.get('plan','?')}")


def stop_tenant(tid: str, reason: str = ""):
    """Tenant bot'unu durdur"""
    proc = PROCESSES.get(tid)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.info(f"[{tid}] DURDURULDU{' — ' + reason if reason else ''}")
    PROCESSES.pop(tid, None)


def check_and_sync():
    """Tenant durumlarini kontrol et ve gerekirse baslat/durdur"""
    configs = load_tenant_configs()
    active_ids = set()

    for cfg in configs:
        tid = cfg["tenant_id"]

        # Aktif degil veya odeme gecersiz
        if not cfg.get("active", False):
            if tid in PROCESSES:
                stop_tenant(tid, "aktif degil")
            continue

        if not is_payment_valid(cfg):
            if tid in PROCESSES:
                stop_tenant(tid, "odeme suresi doldu")
            continue

        active_ids.add(tid)

        # Hali hazirda calisiyor mu?
        proc = PROCESSES.get(tid)
        if proc and proc.poll() is None:
            continue  # Saglıklı calisiyor

        # Olmus veya hic baslatilmamis — baslat
        if proc:
            log.warning(f"[{tid}] Beklenmedik sekilde kapandi, yeniden baslatiliyor...")
        start_tenant(cfg)

    # Artik aktif olmayan eski processleri temizle
    for tid in list(PROCESSES.keys()):
        if tid not in active_ids:
            stop_tenant(tid, "config'den kaldirildi")


def graceful_shutdown(signum, frame):
    log.info("Kapatma sinyali alindi, tum tenant'lar durduruluyor...")
    for tid in list(PROCESSES.keys()):
        stop_tenant(tid, "manager kapaniyor")
    sys.exit(0)


def print_status():
    """Mevcut tenant durumlarini logla"""
    log.info("-" * 50)
    configs = load_tenant_configs()
    for cfg in configs:
        tid = cfg["tenant_id"]
        proc = PROCESSES.get(tid)
        if proc and proc.poll() is None:
            status = f"CALISIYOR (PID:{proc.pid})"
        elif not cfg.get("active", False):
            status = "PASIF"
        elif not is_payment_valid(cfg):
            status = "ODEME_SURESI_DOLDU"
        else:
            status = "DURDU"
        log.info(f"  [{tid}] {cfg.get('name','?')[:30]} — {status} — Plan:{cfg.get('plan','?')}")
    log.info("-" * 50)


def main():
    log.info("=" * 55)
    log.info("  JARVIS Tenant Manager — Basliyor")
    log.info(f"  Tenants dizini: {TENANTS_DIR}")
    log.info(f"  Bot script: {BOT_SCRIPT}")
    log.info("=" * 55)

    signal.signal(signal.SIGTERM, graceful_shutdown)
    signal.signal(signal.SIGINT, graceful_shutdown)

    tick = 0
    while True:
        check_and_sync()
        if tick % 10 == 0:  # Her 5 dakikada bir durum logla
            print_status()
        tick += 1
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
