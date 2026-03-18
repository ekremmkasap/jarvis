import paramiko

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

bot_code = """import telebot
import subprocess

BOT_TOKEN = "8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k"
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "🌟 Emerald Alpha Gateway Aktif!\\nJarvis Sunucusuna (192.168.1.109) bağlandın. Komutlarını dinliyorum. (Durum için /status)")

@bot.message_handler(commands=['status'])
def check_status(message):
    try:
        cpu = subprocess.check_output("top -bn1 | grep 'Cpu(s)'", shell=True).decode('utf-8')
        ram = subprocess.check_output("free -h", shell=True).decode('utf-8')
        bot.reply_to(message, f"📊 Sunucu Durumu:\\n\\nCPU:\\n{cpu}\\nRAM:\\n{ram}")
    except Exception as e:
        bot.reply_to(message, f"Hata: {e}")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_msg = message.text
    # Log the incoming message explicitly
    print(f"Received from Telegram: {user_msg}")
    response = f"Jarvis Core'a iletildi: '{user_msg}'\\n(Sistem analiz ve uygulama modunda.)"
    bot.reply_to(message, response)

if __name__ == "__main__":
    print("Telegram Gateway Başlatıldı...")
    bot.infinity_polling()
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    print("Connection successful! Deploying bot...")
    
    # create file via SFTP
    sftp = client.open_sftp()
    with sftp.file('/home/userk/telegram_gateway.py', 'w') as f:
        f.write(bot_code)
    sftp.close()
    
    # kill any existing instances, install dependency and run
    cmd = "pkill -f telegram_gateway.py; pip3 install pyTelegramBotAPI --break-system-packages || pip3 install pyTelegramBotAPI; nohup python3 /home/userk/telegram_gateway.py > /home/userk/gateway.log 2>&1 &"
    stdin, stdout, stderr = client.exec_command(cmd)
    
    print("Deploy command triggered! The bot should be running on the server now.")
except Exception as e:
    print(f"Failed to deploy: {e}")
finally:
    client.close()
