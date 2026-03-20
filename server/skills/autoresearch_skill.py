import os
import subprocess

AUTORESEARCH_DIR = r"C:\Users\sergen\Desktop\autoresearch"
NOTEBOOKLM_DIR  = r"C:\Users\sergen\Desktop\notebooklm-py"

def run_deep_research(topic=""):
    autoresearch_ok = os.path.exists(AUTORESEARCH_DIR)
    notebooklm_ok   = os.path.exists(NOTEBOOKLM_DIR)

    durum = []
    durum.append(f"📁 autoresearch: {'✅' if autoresearch_ok else '❌ bulunamadı'}")
    durum.append(f"📁 notebooklm-py: {'✅' if notebooklm_ok else '❌ bulunamadı'}")

    program_md_path = os.path.join(AUTORESEARCH_DIR, "program.md")
    program_md = ""
    if os.path.exists(program_md_path):
        try:
            with open(program_md_path, encoding="utf-8") as f:
                program_md = f.read()[:400]
        except Exception:
            pass

    return (
        f"📚 **Derin Araştırma: `{topic}`**\n\n"
        + "\n".join(durum)
        + (f"\n\n📄 program.md:\n```\n{program_md}\n```" if program_md else "")
        + "\n\n💡 Telegram'dan çalıştır:\n"
        f"`/cmd cd {AUTORESEARCH_DIR} && python train.py`\n"
        f"`/cmd cd {NOTEBOOKLM_DIR} && python -m notebooklm_py --help`"
    )
