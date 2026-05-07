import os, subprocess

REPO_DIR = r"C:\Users\sergen\Desktop\jarvis-mission-control\external-repos\ClawRouter"

def run_clawrouter(args=""):
    repo_ok = os.path.exists(REPO_DIR)
    has_pkg = os.path.exists(os.path.join(REPO_DIR, "package.json"))
    has_cargo = os.path.exists(os.path.join(REPO_DIR, "Cargo.toml"))
    has_docker = os.path.exists(os.path.join(REPO_DIR, "Dockerfile")) or \
                 os.path.exists(os.path.join(REPO_DIR, "docker-compose.yml"))

    lines = [
        "⚡ **ClawRouter** — Agent-Native LLM Router",
        "",
        f"📁 Repo: {'✅' if repo_ok else '❌'} `external-repos/ClawRouter`",
        f"📦 package.json: {'✅' if has_pkg else '❌'}",
        f"🦀 Cargo.toml (Rust): {'✅' if has_cargo else '❌'}",
        f"🐳 Docker: {'✅' if has_docker else '❌'}",
        "",
        "**Ne yapar:**",
        "• Ajan'ların API key olmadan LLM kullanmasını sağlar",
        "• Cüzdan imzasıyla (crypto) kimlik doğrulama",
        "• Local routing — veriler dışarı çıkmaz",
        "• Jarvis'in model_router.yml'ine alternatif",
        "",
        "**Jarvis Kullanımı:**",
        "ClawRouter → Jarvis'in tüm LLM çağrılarını tek noktadan yönetir",
        "• API key sızdırma riski sıfır",
        "• Otomatik model fallback",
        "• Kullanım logları",
    ]

    return chr(10).join(lines)
