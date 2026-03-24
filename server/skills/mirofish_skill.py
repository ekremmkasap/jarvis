import os

MIROFISH_DIR = r"C:\Users\sergen\Desktop\MiroFish"

def run_mirofish(param=""):
    exists = os.path.exists(MIROFISH_DIR)

    if not exists:
        return (
            "❌ MiroFish bulunamadı.\n"
            r"`/cmd git clone https://github.com/MiroFish/MiroFish C:\Users\sergen\Desktop\MiroFish`"
        )

    has_main    = os.path.exists(os.path.join(MIROFISH_DIR, "main.py"))
    has_app     = os.path.exists(os.path.join(MIROFISH_DIR, "app.py"))
    has_req     = os.path.exists(os.path.join(MIROFISH_DIR, "requirements.txt"))
    has_docker  = os.path.exists(os.path.join(MIROFISH_DIR, "docker-compose.yml")) or \
                  os.path.exists(os.path.join(MIROFISH_DIR, "Dockerfile"))
    readme      = os.path.exists(os.path.join(MIROFISH_DIR, "README.md"))

    readme_snippet = ""
    if readme:
        try:
            with open(os.path.join(MIROFISH_DIR, "README.md"), encoding="utf-8", errors="ignore") as f:
                readme_snippet = f.read()[:400]
        except Exception:
            pass

    entry = "main.py" if has_main else ("app.py" if has_app else "❓")

    return (
        "🐟 **MiroFish**\n\n"
        f"📁 Repo: ✅\n"
        f"📄 Giriş noktası: {entry}\n"
        f"📦 requirements.txt: {'✅' if has_req else '❌'}\n"
        f"🐳 Docker: {'✅' if has_docker else '❌'}\n\n"
        + (f"📖 README:\n```\n{readme_snippet}\n```\n\n" if readme_snippet else "⚠️ README bulunamadı.\n\n")
        + "▶️ Başlatmak için:\n"
        f"`/cmd cd {MIROFISH_DIR} && pip install -r requirements.txt && python {entry}`"
    )
