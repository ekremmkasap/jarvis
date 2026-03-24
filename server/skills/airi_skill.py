import os

AIRI_DIR = r"C:\Users\sergen\Desktop\airi"

def run_airi(param=""):
    exists = os.path.exists(AIRI_DIR)

    if not exists:
        return (
            "❌ airi bulunamadı.\n"
            "`/cmd git clone https://github.com/airi-project/airi "
            r"C:\Users\sergen\Desktop\airi`"
        )

    main_py   = os.path.exists(os.path.join(AIRI_DIR, "main.py"))
    app_py    = os.path.exists(os.path.join(AIRI_DIR, "app.py"))
    req_txt   = os.path.exists(os.path.join(AIRI_DIR, "requirements.txt"))
    readme    = os.path.exists(os.path.join(AIRI_DIR, "README.md"))

    entry = "main.py" if main_py else ("app.py" if app_py else "❓ giriş noktası bulunamadı")

    readme_snippet = ""
    if readme:
        try:
            with open(os.path.join(AIRI_DIR, "README.md"), encoding="utf-8", errors="ignore") as f:
                readme_snippet = f.read()[:300]
        except Exception:
            pass

    return (
        "🤖 **airi — AI Karakter/Ses Asistanı**\n\n"
        f"📁 Repo: ✅\n"
        f"📄 Giriş noktası: {entry}\n"
        f"📦 requirements.txt: {'✅' if req_txt else '❌'}\n\n"
        + (f"📖 README:\n```\n{readme_snippet}\n```\n\n" if readme_snippet else "")
        + "▶️ Başlatmak için:\n"
        f"`/cmd cd {AIRI_DIR} && pip install -r requirements.txt && python {entry}`"
    )
