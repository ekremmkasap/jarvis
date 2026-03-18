import paramiko
import time

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

# The updated bot code with Chat ID constraint
bot_code = """import telebot
import subprocess

BOT_TOKEN = "8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k"
AUTHORZIED_CHAT_ID = 5847386182

bot = telebot.TeleBot(BOT_TOKEN)

def is_authorized(message):
    return message.chat.id == AUTHORZIED_CHAT_ID

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if not is_authorized(message): return
    bot.reply_to(message, "🌟 Emerald Alpha Gateway Aktif!\\nJarvis Sunucusuna (192.168.1.109) bağlandın. Komutlarını dinliyorum. (Durum için /status)")

@bot.message_handler(commands=['status'])
def check_status(message):
    if not is_authorized(message): return
    try:
        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)'", shell=True).decode('utf-8')
        ram = subprocess.check_output("free -h", shell=True).decode('utf-8')
        bot.reply_to(message, f"📊 Sunucu Durumu:\\n\\nCPU:\\n{cpu}\\nRAM:\\n{ram}")
    except Exception as e:
        bot.reply_to(message, f"Hata: {e}")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    if not is_authorized(message):
        print(f"Yetkisiz erişim denemesi: {message.chat.id}")
        return
        
    user_msg = message.text
    print(f"Received from Telegram: {user_msg}")
    
    if user_msg == "s":
        bot.reply_to(message, "Jarvis Core'a iletildi: 's'\\n(Sistem analiz ve uygulama modunda.)")
    else:
        response = f"Jarvis Core'a iletildi: '{user_msg}'\\n(Sistem analiz ve uygulama modunda.)"
        bot.reply_to(message, response)

if __name__ == "__main__":
    print("Telegram Gateway Başlatıldı...")
    try:
        # Send proactive message to the user that the bot is back online
        bot.send_message(AUTHORZIED_CHAT_ID, "✅ **Emerald Alpha Gateway Güncellendi ve Yeniden Başlatıldı!**\\nArtık sadece sana (Chat ID: 5847386182) özel şifreli bağlantı ile çalışıyorum. /status yazarak test edebilirsin.", parse_mode="Markdown")
    except Exception as e:
        print(f"Baslangic mesaji gonderilemedi: {e}")
        
    bot.infinity_polling()
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    print("Connection successful! Deploying updated bot...")
    
    # create file via SFTP
    sftp = client.open_sftp()
    with sftp.file('/home/userk/telegram_gateway.py', 'w') as f:
        f.write(bot_code)
    sftp.close()
    
    # kill any existing instances, and run
    cmd = "pkill -f telegram_gateway.py; nohup python3 /home/userk/telegram_gateway.py > /home/userk/gateway.log 2>&1 &"
    client.exec_command(cmd)
    
    print("Bot updated with Chat ID and restarted. It should send you a message shortly!")
except Exception as e:
    print(f"Failed to deploy: {e}")
finally:
    client.close()
