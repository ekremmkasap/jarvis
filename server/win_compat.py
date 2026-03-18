"""
win_compat.py — Windows/Pinokio uyumluluk katmanı
bridge.py'nin başında import edilir.
"""
import os
import platform
import subprocess
from pathlib import Path

# ── Proje kök dizini (bridge.py'nin bulunduğu yer) ──────────────────
BASE_DIR = Path(__file__).parent.resolve()
JARVIS_DIR = BASE_DIR          # /opt/jarvis/ → artık server/ klasörü
SKILLS_DIR = BASE_DIR / "skills"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
MEMORY_DIR = BASE_DIR / "memory"
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"

# Gerekli dizinleri oluştur
for _d in [SKILLS_DIR, KNOWLEDGE_DIR, MEMORY_DIR, LOGS_DIR, DATA_DIR,
           MEMORY_DIR / "working_memory", MEMORY_DIR / "project_memory"]:
    _d.mkdir(parents=True, exist_ok=True)

IS_WINDOWS = platform.system() == "Windows"

def load_dotenv():
    """Basit .env yükleyici (python-dotenv gerekmez)"""
    env_file = BASE_DIR / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

load_dotenv()

# ── Sistem bilgisi (Windows/Linux uyumlu) ───────────────────────────
def get_cpu_usage() -> str:
    if IS_WINDOWS:
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip() + "%"
        except:
            return "N/A"
    else:
        r = subprocess.run("top -bn1 | grep 'Cpu' | awk '{print $2}'",
                           shell=True, capture_output=True, text=True)
        return r.stdout.strip() + "%"

def get_ram_usage() -> str:
    if IS_WINDOWS:
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "$os=Get-WmiObject Win32_OperatingSystem;"
                 "$used=[math]::Round(($os.TotalVisibleMemorySize-$os.FreePhysicalMemory)/1MB,1);"
                 "$total=[math]::Round($os.TotalVisibleMemorySize/1MB,1);"
                 "Write-Output \"${used}GB/${total}GB\""],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip()
        except:
            return "N/A"
    else:
        r = subprocess.run("free -h | awk '/^Mem:/ {print $3\"/\"$2}'",
                           shell=True, capture_output=True, text=True)
        return r.stdout.strip()

def get_disk_usage() -> str:
    if IS_WINDOWS:
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "$d=Get-PSDrive C;"
                 "$used=[math]::Round($d.Used/1GB,1);"
                 "$total=[math]::Round(($d.Used+$d.Free)/1GB,1);"
                 "Write-Output \"${used}GB/${total}GB\""],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip()
        except:
            return "N/A"
    else:
        r = subprocess.run("df -h / | awk 'NR==2 {print $3\"/\"$2}'",
                           shell=True, capture_output=True, text=True)
        return r.stdout.strip()

def get_service_status(svc: str) -> str:
    """Windows'ta process adı kontrol eder, Linux'ta systemctl kullanır."""
    if IS_WINDOWS:
        svc_map = {
            "jarvis":          "python",
            "ollama":          "ollama",
            "n8n":             "node",
            "tenant_manager":  "python",
        }
        proc = svc_map.get(svc, svc)
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 f"if (Get-Process -Name '{proc}' -ErrorAction SilentlyContinue) {{'active'}} else {{'inactive'}}"],
                capture_output=True, text=True, timeout=5
            )
            return r.stdout.strip()
        except:
            return "unknown"
    else:
        r = subprocess.run(f"systemctl is-active {svc}.service",
                           shell=True, capture_output=True, text=True)
        return r.stdout.strip()

def run_shell_safe(cmd: str) -> str:
    """
    Windows'ta PowerShell, Linux'ta bash ile çalıştırır.
    '!! ' prefix'li komutlar buraya gelir.
    """
    DANGER = ["rm -rf /", "mkfs", "> /dev/sd", "dd if=/dev/zero",
              "Remove-Item -Recurse -Force C:\\", "Format-Volume"]
    if any(d.lower() in cmd.lower() for d in DANGER):
        return "HATA: Bu komut tehlikeli, çalıştırılmıyor."
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                ["powershell", "-Command", cmd],
                capture_output=True, text=True, timeout=30
            )
        else:
            # Linux: sudo varsa parolasız çalıştır (artık hard-coded parola yok)
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = result.stdout[:3000] or result.stderr[:1000] or "Çıktı yok."
        return out
    except subprocess.TimeoutExpired:
        return "Komut zaman aşımına uğradı (30s)."
    except Exception as e:
        return f"Hata: {e}"
