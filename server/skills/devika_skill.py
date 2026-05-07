import os, subprocess

REPO_DIR = r"C:\Users\sergen\Desktop\jarvis-mission-control\external-repos\devika"

def run_devika(args=""):
    repo_ok = os.path.exists(REPO_DIR)
    has_req = os.path.exists(os.path.join(REPO_DIR, "requirements.txt"))
    has_main = os.path.exists(os.path.join(REPO_DIR, "devika.py")) or \
               os.path.exists(os.path.join(REPO_DIR, "src", "devika.py"))
    has_docker = os.path.exists(os.path.join(REPO_DIR, "docker-compose.yaml")) or \
                 os.path.exists(os.path.join(REPO_DIR, "docker-compose.yml"))

    lines = [
        "👩‍💻 **Devika** — Agentic AI Software Engineer",
        "",
        f"📁 Repo: {'✅' if repo_ok else '❌'} `external-repos/devika`",
        f"📦 requirements.txt: {'✅' if has_req else '❌'}",
        f"🐍 devika.py: {'✅' if has_main else '❌'}",
        f"🐳 docker-compose: {'✅' if has_docker else '❌'}",
        "",
        "⚠️ Not: Devika erken-aşama projedir. Yeni versiyonu: **Opcode** (opcode.sh)",
        "",
        "**Kurulum:**",
        f"`/cmd cd {REPO_DIR} && pip install -r requirements.txt`",
        f"`/cmd cd {REPO_DIR} && python devika.py`",
        "",
        "**Özellikler:**",
        "• Web araştırması + planlama + terminal entegrasyonu",
        "• Alt-ajan orkestrasyonu (planner, coder, tester)",
        "• Playwright ile tarayıcı kontrolü",
    ]

    if args:
        lines.append("")
        lines.append(f"💬 Görev: `{args}`")

    return chr(10).join(lines)
