import os, subprocess, sys

REPO_DIR = r"C:\Users\sergen\Desktop\jarvis-mission-control\external-repos\aider"

def run_aider(args=""):
    repo_ok = os.path.exists(REPO_DIR)

    # pip ile kurulu mu?
    try:
        result = subprocess.run(
            ["aider", "--version"], capture_output=True, text=True, timeout=5
        )
        installed = result.returncode == 0
        version = result.stdout.strip() or result.stderr.strip()
    except Exception:
        installed = False
        version = "bulunamadı"

    if args and installed:
        return (
            f"🤖 **Aider** — terminal AI pair programmer\n\n"
            f"Çalıştırılıyor: `aider {args}`\n\n"
            f"Terminalde şu komutu gir:\n"
            f"`aider {args}`"
        )

    lines = [
        "🤖 **Aider** — AI Pair Programming (Terminal)",
        "",
        f"📁 Repo: {'✅' if repo_ok else '❌'} `external-repos/aider`",
        f"⚙️ Kurulum: {'✅ ' + version if installed else '❌ pip install aider-chat'}",
        "",
        "**Kurulum:**",
        "`pip install aider-chat`",
        "",
        "**Kullanım:**",
        "`/aider` — durum",
        "`/cmd aider --model claude-sonnet-4-6 --yes`  — Claude ile başlat",
        "`/cmd aider --model ollama/llama3.2 --yes`  — Ollama ile başlat (ücretsiz)",
        "",
        "**Özellikler:**",
        "• Tüm Git reposunu okur, dosya değiştirir, commit yazar",
        "• Claude / GPT-4o / DeepSeek / Ollama destekler",
        "• `/add dosya.py` ile dosya ekle, `/run test` ile test çalıştır",
    ]
    return chr(10).join(lines)
