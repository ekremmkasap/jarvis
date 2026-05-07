import os

REPO_DIR = r"C:\Users\sergen\Desktop\jarvis-mission-control\external-repos\cline"

def run_cline(args=""):
    repo_ok = os.path.exists(REPO_DIR)
    has_pkg = os.path.exists(os.path.join(REPO_DIR, "package.json"))

    lines = [
        "🔵 **Cline** — VS Code AI Coding Agent",
        "",
        f"📁 Repo: {'✅' if repo_ok else '❌'} `external-repos/cline`",
        f"📦 package.json: {'✅' if has_pkg else '❌'}",
        "",
        "**Kurulum (2 yol):**",
        "1. VS Code Extensions → 'Cline' ara → Yükle",
        "2. Kaynak kod:",
        f"   `/cmd cd {REPO_DIR} && npm install && npm run build`",
        "",
        "**Özellikler:**",
        "• VS Code içinde çalışır (terminal + dosya + tarayıcı erişimi)",
        "• Claude / GPT-4o / Ollama ile otonom kod geliştirme",
        "• Dosya okuma/yazma, terminal komut çalıştırma, PR açma",
        "• Plan modu: değişiklikleri göster, onayla, uygula",
        "",
        "**Not:** Cline VS Code extension'ı — terminalde değil VS Code'da kullanılır.",
        "Jarvis ile entegrasyonu: Cline'ın sonuçlarını Telegram'a yönlendir.",
    ]

    return chr(10).join(lines)
