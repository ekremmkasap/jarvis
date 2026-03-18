import telebot
import subprocess
import os

# Telegram Bot Token'ı (Önceki Emerald Alpha token'ı veya yeni)
# TODO: Kullanıcıdan token alınacak veya .env'den yüklenecek
BOT_TOKEN = "8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k"
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🌟 Emerald Alpha Gateway'e Hoş Geldin!\nJarvis Sunucusuna (192.168.1.109) bağlandın. Komutlarını dinliyorum.")

@bot.message_handler(commands=['status'])
def check_status(message):
    try:
        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)'", shell=True).decode('utf-8')
        ram = subprocess.check_output("free -h", shell=True).decode('utf-8')
        bot.reply_to(message, f"📊 Sunucu Durumu:\n\nCPU:\n{cpu}\nRAM:\n{ram}")
    except Exception as e:
        bot.reply_to(message, f"Hata: {e}")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    # Gelen mesajı doğrudan Jarvis'in orkestrasyon betiğine (run.ts veya CLI) yönlendir
    # FAZ 1 MVP: Şimdilik mesajı loglayıp cevap veriyoruz.
    user_msg = message.text
    
    # Burada asıl Jarvis Core Agent'a (openclaw) istek atılacak
    response = f"Jarvis Core'a iletildi: '{user_msg}'\n(Şu an Gateway test modunda çalışıyor.)"
    bot.reply_to(message, response)

if __name__ == "__main__":
    print("Gateway Bot Başlatılıyor...")
    bot.infinity_polling()
