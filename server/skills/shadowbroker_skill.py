import os
import subprocess

SHADOWBROKER_DIR = r"C:\Users\sergen\Desktop\Shadowbroker"

def run_osint(target=""):
    exists = os.path.exists(SHADOWBROKER_DIR)

    if not exists:
        return (
            "❌ Shadowbroker bulunamadı. Telegram'dan klon:\n"
            "`/cmd git clone https://github.com/BigBodyCobain/Shadowbroker "
            r"C:\Users\sergen\Desktop\Shadowbroker`"
        )

    # docker-compose var mı kontrol et
    compose_ok = os.path.exists(os.path.join(SHADOWBROKER_DIR, "docker-compose.yml"))

    return (
        f"🕵️ **OSINT: `{target}`**\n\n"
        f"📁 Shadowbroker: ✅\n"
        f"🐳 docker-compose: {'✅' if compose_ok else '❌'}\n\n"
        "**Veri kaynakları:** Uçak (ADS-B), Gemi (AIS), Uydu, Deprem, CCTV, GPS jamming\n\n"
        "▶️ Başlatmak için:\n"
        f"`/cmd cd {SHADOWBROKER_DIR} && docker-compose up -d`\n"
        "Sonra: http://localhost:3000"
    )
