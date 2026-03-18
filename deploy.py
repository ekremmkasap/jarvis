#!/usr/bin/env python3
"""
deploy.py — Jarvis Mission Control Deploy Aracı
Kullanım:
  python deploy.py                  → server/ klasörünün tamamını sunucuya gönder
  python deploy.py skills/          → sadece skills/ alt klasörünü gönder
  python deploy.py --dry-run        → ne gönderileceğini göster (gönderme)
  python deploy.py skills/ --dry-run
"""

import os
import sys
import hashlib
import paramiko
import stat
import time

# ─────────────────────────────────────────────
# AYARLAR
# ─────────────────────────────────────────────
SERVER_IP   = "192.168.1.109"
SERVER_USER = "userk"
SERVER_PASS = "userk1"
REMOTE_BASE = "/opt/jarvis"
LOCAL_BASE  = os.path.join(os.path.dirname(__file__), "server")
SERVICE     = "jarvis.service"

SKIP_DIRS  = {".git", "__pycache__", "node_modules", ".pytest_cache", "logs", "memory"}
SKIP_EXTS  = {".db", ".sqlite", ".log", ".pyc", ".pyo", ".b64"}
SKIP_FILES = {"jarvis.log"}

# ─────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
# ─────────────────────────────────────────────
def md5(filepath):
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def remote_md5(sftp, remote_path):
    try:
        with sftp.open(remote_path, "rb") as f:
            h = hashlib.md5()
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
            return h.hexdigest()
    except Exception:
        return None

def ensure_remote_dir(sftp, remote_dir):
    parts = remote_dir.split("/")
    path = ""
    for part in parts:
        if not part:
            path = "/"
            continue
        path = path.rstrip("/") + "/" + part
        try:
            sftp.stat(path)
        except FileNotFoundError:
            sftp.mkdir(path)

def collect_files(local_root, subpath=""):
    """local_root altındaki tüm dosyaları topla, (local_abs, relative) tuple'ları döndür"""
    scan_root = os.path.join(local_root, subpath) if subpath else local_root
    results = []
    for root, dirs, files in os.walk(scan_root):
        # Atlanacak klasörleri filtrele
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname in SKIP_FILES:
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in SKIP_EXTS:
                continue
            local_abs = os.path.join(root, fname)
            # server/ den itibaren relative path
            relative = os.path.relpath(local_abs, local_root).replace("\\", "/")
            results.append((local_abs, relative))
    return results

# ─────────────────────────────────────────────
# ANA FONKSİYON
# ─────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    subpath = args[0].strip("/\\") if args else ""

    if dry_run:
        print("=" * 55)
        print("  DRY RUN MODU — Hiçbir şey gönderilmeyecek")
        print("=" * 55)
    else:
        print("=" * 55)
        print("  Jarvis Deploy — Sunucuya bağlanılıyor...")
        print("=" * 55)

    # Dosyaları topla
    files = collect_files(LOCAL_BASE, subpath)
    print(f"  Tarandı: {len(files)} dosya")

    if dry_run:
        print(f"\n  Gönderilecek dosyalar:")
        for _, rel in sorted(files):
            print(f"    {rel}")
        print(f"\n  TOPLAM: {len(files)} dosya (dry-run, gönderilmedi)")
        return

    # SSH/SFTP bağlantısı
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(SERVER_IP, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    except Exception as e:
        print(f"\n  HATA: Sunucuya bağlanılamadı — {e}")
        sys.exit(1)

    sftp = client.open_sftp()

    updated = 0
    skipped = 0
    errors  = []

    print(f"\n  Dosyalar karşılaştırılıyor ve gönderiliyor...\n")

    for local_abs, relative in sorted(files):
        remote_abs = REMOTE_BASE + "/" + relative

        # Remote klasörü oluştur
        remote_dir = "/".join(remote_abs.split("/")[:-1])
        try:
            ensure_remote_dir(sftp, remote_dir)
        except Exception as e:
            errors.append(f"mkdir fail: {remote_dir}: {e}")
            continue

        # MD5 karşılaştır
        local_hash  = md5(local_abs)
        remote_hash = remote_md5(sftp, remote_abs)

        if local_hash == remote_hash:
            skipped += 1
            continue

        # Gönder
        try:
            sftp.put(local_abs, remote_abs)
            updated += 1
            print(f"  + {relative}")
        except Exception as e:
            errors.append(f"put fail: {relative}: {e}")

    sftp.close()

    # Özet
    print(f"\n  ─────────────────────────────────────────────")
    print(f"  Güncellendi : {updated} dosya")
    print(f"  Atlandı     : {skipped} dosya (değişmemiş)")
    if errors:
        print(f"  HATALAR     : {len(errors)}")
        for e in errors[:5]:
            print(f"    ! {e}")
    print(f"  ─────────────────────────────────────────────")

    if updated == 0:
        print(f"\n  Sunucu zaten güncel. Restart atlanıyor.")
        client.close()
        return

    # Servisi yeniden başlat
    print(f"\n  Servis yeniden başlatılıyor: {SERVICE}...")
    stdin, stdout, stderr = client.exec_command(
        f"echo {SERVER_PASS} | sudo -S systemctl restart {SERVICE}"
    )
    stdout.channel.recv_exit_status()
    time.sleep(3)

    # Servis durumu kontrol
    stdin, stdout, stderr = client.exec_command(
        f"systemctl is-active {SERVICE}"
    )
    status = stdout.read().decode().strip()

    if status == "active":
        print(f"  Servis durumu : AKTIF")
    else:
        print(f"  Servis durumu : {status.upper()} (!)  stderr: {stderr.read().decode().strip()}")

    client.close()
    print(f"\n  Deploy tamamlandı!")

if __name__ == "__main__":
    main()
