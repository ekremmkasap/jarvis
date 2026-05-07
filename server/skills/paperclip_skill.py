import os, subprocess

REPO_DIR = r"C:\Users\sergen\Desktop\jarvis-mission-control\external-repos\paperclip"

def run_paperclip(args=""):
    repo_ok = os.path.exists(REPO_DIR)
    has_pkg = os.path.exists(os.path.join(REPO_DIR, "package.json"))
    has_docker = os.path.exists(os.path.join(REPO_DIR, "docker-compose.yml")) or \
                 os.path.exists(os.path.join(REPO_DIR, "Dockerfile"))

    lines = [
        "📎 **Paperclip** — AI ile İş Yönetimi",
        "",
        f"📁 Repo: {'✅' if repo_ok else '❌'} `external-repos/paperclip`",
        f"📦 package.json: {'✅' if has_pkg else '❌'}",
        f"🐳 Docker: {'✅' if has_docker else '❌'}",
        "",
        "**Ne yapar:**",
        "• 'runs your business' — otonom iş yönetim sistemi",
        "• Task yönetimi + ajan orkestrasyonu",
        "• Jarvis'in görev sistemiyle entegre edilebilir",
        "",
        "**Kurulum:**",
        f"`/cmd cd {REPO_DIR} && npm install`",
        f"`/cmd cd {REPO_DIR} && npm run dev`",
        "",
        "**Jarvis Entegrasyonu:**",
        "Paperclip → Jarvis task_bus.py ile köprü kurulabilir.",
        "Telegram'dan görev ver → Paperclip takip et.",
    ]

    if args:
        lines.append("")
        lines.append(f"💬 Görev: `{args}`")

    return chr(10).join(lines)
