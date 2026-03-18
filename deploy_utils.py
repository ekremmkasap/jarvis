"""
Deploy utils_skill.py to server and add commands to bridge.py:
/hava, /haber, /altin, /kur, /hesap
"""
import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)
sftp = client.open_sftp()

# Upload utils_skill.py
sftp.put(
    r'C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\utils_skill.py',
    '/opt/jarvis/skills/utils_skill.py'
)
print("✅ utils_skill.py uploaded")

# Read bridge.py
with sftp.file('/opt/jarvis/openclaw/bridge.py', 'r') as f:
    content = f.read().decode()

# Add utility commands before /printify section
MARKER = '    elif command == "/printify":'
NEW_CMDS = '''    elif command == "/hava":
        city = args or "Istanbul"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_weather
            return get_weather(city)
        except Exception as e:
            return f"Hava hatası: {e}"

    elif command == "/haber":
        topic = args or "turkiye"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_rss_news
            return get_rss_news(topic)
        except Exception as e:
            return f"Haber hatası: {e}"

    elif command == "/altin":
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_gold_price
            return get_gold_price()
        except Exception as e:
            return f"Altın hatası: {e}"

    elif command == "/kur":
        parts = args.split() if args else []
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_currency
            if len(parts) >= 3:
                return get_currency(float(parts[0]), parts[1], parts[2])
            elif len(parts) == 2:
                return get_currency(1, parts[0], parts[1])
            else:
                return get_currency(1, "USD", "TRY")
        except Exception as e:
            return f"Kur hatası: {e}"

    elif command == "/hesap":
        if not args:
            return "Kullanım: /hesap 2+2 veya /hesap sqrt(144)"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import calculate
            return calculate(args)
        except Exception as e:
            return f"Hesap hatası: {e}"

    elif command == "/printify":'''

if MARKER in content and '/hava' not in content:
    content = content.replace(MARKER, NEW_CMDS)
    print("✅ Commands added to bridge.py")
elif '/hava' in content:
    print("ℹ️ Commands already exist")
else:
    print("⚠️ Marker not found, adding at end...")
    # Find a good place to insert
    FALLBACK = '    elif command == "/trendyol":'
    if FALLBACK in content:
        content = content.replace(FALLBACK, NEW_CMDS.replace('    elif command == "/printify":', '    elif command == "/trendyol":'))

# Update help text
OLD_HELP = '  `/printify [niyet]` -> Printify POD analizi'
NEW_HELP = ('  `/hava [şehir]` -> Hava durumu\n'
            '  `/haber [konu]` -> Son haberler\n'
            '  `/altin` -> Altın & döviz fiyatları\n'
            '  `/kur [100 USD TRY]` -> Döviz çevirici\n'
            '  `/hesap [işlem]` -> Hesap makinesi\n'
            '  `/printify [niyet]` -> Printify POD analizi')
if OLD_HELP in content:
    content = content.replace(OLD_HELP, NEW_HELP)
    print("✅ Help text updated")

with sftp.file('/opt/jarvis/openclaw/bridge.py', 'w') as f:
    f.write(content)

sftp.close()

# Syntax check + restart
_, so, _ = client.exec_command('python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo SYNTAX_OK')
result = so.read().decode().strip()
print(f"Syntax: {result}")

if 'OK' in result:
    client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
    time.sleep(3)
    _, ss, _ = client.exec_command('systemctl is-active jarvis.service')
    print(f"Service: {ss.read().decode().strip()}")

client.close()
print("\n✅ Done! New commands: /hava /haber /altin /kur /hesap")
