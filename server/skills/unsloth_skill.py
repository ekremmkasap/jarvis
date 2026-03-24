import os
import glob

UNSLOTH_DIR = r"C:\Users\sergen\Desktop\unsloth"

def run_finetune(model=""):
    exists = os.path.exists(UNSLOTH_DIR)

    if not exists:
        return (
            "❌ unsloth bulunamadı.\n"
            "`/cmd git clone https://github.com/unslothai/unsloth "
            r"C:\Users\sergen\Desktop\unsloth`"
        )

    has_req    = os.path.exists(os.path.join(UNSLOTH_DIR, "requirements.txt"))
    has_setup  = os.path.exists(os.path.join(UNSLOTH_DIR, "setup.py"))
    has_pyproj = os.path.exists(os.path.join(UNSLOTH_DIR, "pyproject.toml"))
    readme     = os.path.exists(os.path.join(UNSLOTH_DIR, "README.md"))

    # Notebook say
    notebooks = glob.glob(os.path.join(UNSLOTH_DIR, "**", "*.ipynb"), recursive=True)
    nb_count  = len(notebooks)
    nb_names  = [os.path.basename(n) for n in notebooks[:5]]

    readme_snippet = ""
    if readme:
        try:
            with open(os.path.join(UNSLOTH_DIR, "README.md"), encoding="utf-8", errors="ignore") as f:
                readme_snippet = f.read()[:300]
        except Exception:
            pass

    model_line = f"🧠 Fine-tune hedefi: `{model}`\n\n" if model else ""

    nb_section = ""
    if nb_count:
        nb_section = f"📓 Notebooks ({nb_count} adet):\n" + "\n".join(f"  - {n}" for n in nb_names) + "\n\n"

    return (
        f"⚡ **Unsloth — Hızlı LLM Fine-Tuning**\n\n"
        + model_line
        + f"📁 Repo: ✅\n"
        f"📦 requirements.txt: {'✅' if has_req else '❌'}\n"
        f"📦 setup.py: {'✅' if has_setup else '❌'}\n"
        f"📦 pyproject.toml: {'✅' if has_pyproj else '❌'}\n\n"
        + nb_section
        + (f"📖 README:\n```\n{readme_snippet}\n```\n\n" if readme_snippet else "")
        + "▶️ Kullanmak için:\n"
        f"`/cmd cd {UNSLOTH_DIR} && pip install unsloth`\n"
        "Sonra notebook'u Jupyter ile aç veya train script'i çalıştır."
    )
