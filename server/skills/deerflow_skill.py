import os

DEERFLOW_DIR = r"C:\Users\sergen\Desktop\deer-flow"

def run_deerflow(topic=""):
    exists = os.path.exists(DEERFLOW_DIR)

    if not exists:
        return (
            "❌ deer-flow bulunamadı.\n"
            "`/cmd git clone https://github.com/bytedance/deer-flow "
            r"C:\Users\sergen\Desktop\deer-flow`"
        )

    has_req     = os.path.exists(os.path.join(DEERFLOW_DIR, "requirements.txt"))
    has_pyproj  = os.path.exists(os.path.join(DEERFLOW_DIR, "pyproject.toml"))
    has_main    = os.path.exists(os.path.join(DEERFLOW_DIR, "main.py"))
    has_docker  = os.path.exists(os.path.join(DEERFLOW_DIR, "docker-compose.yml"))
    readme      = os.path.exists(os.path.join(DEERFLOW_DIR, "README.md"))

    readme_snippet = ""
    if readme:
        try:
            with open(os.path.join(DEERFLOW_DIR, "README.md"), encoding="utf-8", errors="ignore") as f:
                readme_snippet = f.read()[:300]
        except Exception:
            pass

    topic_line = f"🔎 Araştırma konusu: `{topic}`\n\n" if topic else ""

    return (
        f"🦌 **DeerFlow — Derin Araştırma Orkestratörü**\n\n"
        + topic_line
        + f"📁 Repo: ✅\n"
        f"📦 requirements.txt: {'✅' if has_req else '❌'}\n"
        f"📦 pyproject.toml: {'✅' if has_pyproj else '❌'}\n"
        f"🐍 main.py: {'✅' if has_main else '❌'}\n"
        f"🐳 docker-compose: {'✅' if has_docker else '❌'}\n\n"
        + (f"📖 README:\n```\n{readme_snippet}\n```\n\n" if readme_snippet else "")
        + "▶️ Başlatmak için:\n"
        f"`/cmd cd {DEERFLOW_DIR} && pip install -r requirements.txt`\n"
        f"`/cmd cd {DEERFLOW_DIR} && python main.py`"
    )
