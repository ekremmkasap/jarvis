"""
Jarvis Telegram Gateway v2
Her mesajı JarvisRouter'a iletir.
Özel komutlar: /status, /memory, /tasks, /help
"""
import telebot
import logging
import sys
sys.path.insert(0, '/opt/jarvis/core')
sys.path.insert(0, '/home/userk')
from jarvis_router import get_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/opt/jarvis/logs/gateway.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("telegram.gateway")

BOT_TOKEN = "8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k"
AUTHORIZED_CHAT_ID = 5847386182

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
