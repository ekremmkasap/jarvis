import os

SANDBOX_DIR = r"C:\Users\sergen\Desktop\OpenSandbox"

def run_in_sandbox(kodu=""):
    exists = os.path.exists(SANDBOX_DIR)

    if not exists:
        return (
            "❌ OpenSandbox bulunamadı.\n"
            "`/cmd git clone https://github.com/alibaba/OpenSandbox "
            r"C:\Users\sergen\Desktop\OpenSandbox`"
        )

    readme = os.path.join(SANDBOX_DIR, "README.md")
    has_docker = os.path.exists(os.path.join(SANDBOX_DIR, "docker-compose.yml")) or \
                 os.path.exists(os.path.join(SANDBOX_DIR, "Dockerfile"))

    return (
        "🔒 **OpenSandbox**\n\n"
        f"📁 Repo: ✅\n"
        f"🐳 Docker: {'✅' if has_docker else '⚠️ docker-compose bulunamadı'}\n\n"
        f"```python\n{kodu[:500]}\n```\n\n"
        "▶️ Başlatmak için:\n"
        f"`/cmd cd {SANDBOX_DIR} && pip install opensandbox && python -c \"import opensandbox; print('OK')\"`"
    )
