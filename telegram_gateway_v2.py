"""
Jarvis Telegram Gateway v2
Her mesajı JarvisRouter'a iletir.
Özel komutlar: /status, /memory, /tasks, /help, /cmd
"""
import telebot
import logging
import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
from env_utils import get_int_env, load_env_files

load_env_files(ROOT_DIR / ".env", ROOT_DIR / "server" / ".env")

sys.path.insert(0, '/opt/jarvis/core')
sys.path.insert(0, '/home/userk')
sys.path.insert(0, '/opt/jarvis/skills/execution')
from jarvis_router import get_router
import run_command as terminal_skill

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/opt/jarvis/logs/gateway.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("telegram.gateway")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
AUTHORIZED_CHAT_ID = get_int_env("TELEGRAM_CHAT_ID", 0)

if not BOT_TOKEN or not AUTHORIZED_CHAT_ID:
    raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required for telegram_gateway_v2.py")

bot = telebot.TeleBot(BOT_TOKEN)
router = get_router()


def is_authorized(message) -> bool:
    return message.chat.id == AUTHORIZED_CHAT_ID


def send(chat_id: int, text: str):
    """Uzun mesajları bölerek gönder"""
    if not text:
        return
    max_len = 4000
    for i in range(0, len(text), max_len):
        bot.send_message(chat_id, text[i:i+max_len])


# --- Komutlar ---

@bot.message_handler(commands=["start", "help"])
def cmd_help(message):
    if not is_authorized(message):
        return
    text = (
        "🤖 *Jarvis Mission Control*\n\n"
        "Her mesajınızı AI olarak işliyorum.\n\n"
        "Özel komutlar:\n"
        "/status — Sunucu durumu\n"
        "/memory — Son konuşmalar\n"
        "/tasks — Son görevler\n"
        "/cmd <komut> — Terminal komutu çalıştır\n"
        "/kabul — AnyDesk bağlantı isteğini kabul et\n"
        "/help — Bu mesaj\n\n"
        "Veya doğrudan yazın: 'sunucu durumu', 'kod yaz', 'planla...'"
    )
    bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(commands=["status"])
def cmd_status(message):
    if not is_authorized(message):
        return
    bot.send_chat_action(message.chat.id, "typing")
    resp = router.handle("sunucu durumu")
    send(message.chat.id, resp)


@bot.message_handler(commands=["memory"])
def cmd_memory(message):
    if not is_authorized(message):
        return
    summary = router.get_memory_summary()
    send(message.chat.id, f"📝 Son Konuşmalar:\n\n{summary}")


@bot.message_handler(commands=["tasks"])
def cmd_tasks(message):
    if not is_authorized(message):
        return
    summary = router.get_tasks_summary()
    send(message.chat.id, f"📋 Son Görevler:\n\n{summary}")


@bot.message_handler(commands=["kabul", "onayla", "accept"])
def cmd_anydesk_accept(message):
    if not is_authorized(message):
        return
    bot.send_chat_action(message.chat.id, "typing")
    log.info("AnyDesk kabul isteği alındı.")

    # WSL üzerinden Windows PowerShell'i çağır
    result = terminal_skill.run(
        "powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden "
        "-File 'C:\\Users\\sergen\\Desktop\\anydesk_kabul.ps1'",
        timeout=15
    )

    stdout = (result.get("stdout") or "").strip()
    stderr = (result.get("stderr") or "").strip()
    ok = result.get("returncode", -1) == 0

    if ok or "kabul edildi" in stdout.lower() or "accepted" in stdout.lower():
        send(message.chat.id, f"✅ AnyDesk bağlantısı kabul edildi!\n{stdout}")
    else:
        msg = stdout or stderr or "Pencere bulunamadı veya hata oluştu."
        send(message.chat.id, f"❌ AnyDesk kabul başarısız:\n{msg}")


@bot.message_handler(commands=["cmd", "terminal", "run"])
def cmd_terminal(message):
    if not is_authorized(message):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        bot.reply_to(message, "⚠️ Kullanım: `/cmd <komut>`\nÖrnek: `/cmd git clone https://...`", parse_mode="Markdown")
        return

    command = parts[1].strip()
    log.info(f"Terminal komutu: {command[:80]}")
    bot.send_chat_action(message.chat.id, "typing")

    result = terminal_skill.run(command, timeout=60)

    if result.get("error") == "policy_blocked":
        send(message.chat.id, f"🚫 Engellendi: `{command}`\nNeden: {result['stderr']}")
        return

    stdout = result.get("stdout", "").strip()
    stderr = result.get("stderr", "").strip()
    returncode = result.get("returncode", -1)

    output_parts = []
    if stdout:
        output_parts.append(f"```\n{stdout[:3000]}\n```")
    if stderr:
        output_parts.append(f"⚠️ stderr:\n```\n{stderr[:1000]}\n```")

    status = "✅" if returncode == 0 else f"❌ (exit {returncode})"
    header = f"{status} `{command[:60]}`\n\n"

    if output_parts:
        send(message.chat.id, header + "\n".join(output_parts))
    else:
        send(message.chat.id, header + "_(çıktı yok)_")


# --- Tüm mesajlar ---

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    if not is_authorized(message):
        log.warning(f"Yetkisiz erişim: {message.chat.id}")
        return

    user_text = message.text or ""
    log.info(f"Mesaj alındı: {user_text[:60]}")

    bot.send_chat_action(message.chat.id, "typing")

    try:
        response = router.handle(user_text)
        send(message.chat.id, response)
    except Exception as e:
        log.error(f"Router hatası: {e}")
        bot.reply_to(message, f"Hata: {e}")


# --- Başlat ---

if __name__ == "__main__":
    log.info("Jarvis Telegram Gateway v2 başlatıldı.")
    try:
        bot.send_message(
            AUTHORIZED_CHAT_ID,
            "🚀 *Jarvis v2 aktif!* Artık tüm mesajlarınızı AI ile işliyorum.\n"
            "/help yazarak başlayabilirsiniz.",
            parse_mode="Markdown"
        )
    except Exception as e:
        log.warning(f"Başlangıç mesajı gönderilemedi: {e}")

    bot.infinity_polling()
