import os, subprocess

REPO_DIR = r"C:\Users\sergen\Desktop\jarvis-mission-control\external-repos\CLI-Anything"

def run_cli_anything(args=""):
    repo_ok = os.path.exists(REPO_DIR)
    has_req = os.path.exists(os.path.join(REPO_DIR, "requirements.txt"))
    has_main = os.path.exists(os.path.join(REPO_DIR, "main.py")) or \
               os.path.exists(os.path.join(REPO_DIR, "cli_anything.py"))

    lines = [
        "🌐 **CLI-Anything** — Her Yazılımı Agent-Native Yap",
        "",
        f"📁 Repo: {'✅' if repo_ok else '❌'} `external-repos/CLI-Anything`",
        f"📦 requirements.txt: {'✅' if has_req else '❌'}",
        f"🐍 main.py: {'✅' if has_main else '❌'}",
        "",
        "**Ne yapar:**",
        "• Herhangi bir CLI aracını AI ajanı için sarmallar",
        "• 1839+ test geçen CLI entegrasyonları",
        "• CLI-Hub: topluluk tarafından yapılmış CLI'lar",
        "",
        "**Kurulum:**",
        f"`/cmd cd {REPO_DIR} && pip install -r requirements.txt`",
        "",
        "**Jarvis Kullanımı:**",
        "Jarvis'teki `/cmd` komutunu daha da güçlendirir.",
        "Herhangi bir terminal programı Telegram'dan çağrılabilir hale gelir.",
    ]

    if args:
        lines.append("")
        lines.append(f"💬 Sarmalanacak CLI: `{args}`")

    return chr(10).join(lines)
