"""
Deploy Printify skill to Jarvis server and add /printify command to bridge.py
"""
import paramiko, time

host, username, password = "192.168.1.109", "userk", "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname=host, username=username, password=password, timeout=10)
sftp = client.open_sftp()

# Upload printify skill
sftp.put(
    r"C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\printify_skill.py",
    "/opt/jarvis/skills/printify_skill.py"
)
print("✅ printify_skill.py uploaded")

# Read bridge.py
with sftp.file("/opt/jarvis/openclaw/bridge.py", "r") as f:
    content = f.read().decode()

# Add /printify command handler
if "/printify" not in content:
    OLD = '''    elif command == "/trendyol":'''
    NEW = '''    elif command == "/printify":
        query = args or "genel"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            import importlib, os
            token = ""
            try:
                with open("/opt/jarvis/printify_token.txt") as f:
                    token = f.read().strip()
            except:
                pass
            if not token:
                return "Printify token gerekli. /printify_setup komutu ile ayarla veya token\u2019\u0131 /opt/jarvis/printify_token.txt dosyas\u0131na yaz."
            from printify_skill import format_overview, analyze_product_opportunity
            if query in ("genel", "durum", "status", "shop"):
                return format_overview(token)
            else:
                return analyze_product_opportunity(token, query)
        except Exception as e:
            return f"Printify hatas\u0131: {e}"

    elif command == "/trendyol":'''

    if OLD in content:
        content = content.replace(OLD, NEW)
        print("✅ /printify command added to bridge.py")

    # Also add to help text
    OLD_HELP = "  `/trendyol [urun]` -> Trendyol TR analizi"
    NEW_HELP = "  `/printify [niyet]` -> Printify POD analizi\n  `/trendyol [urun]` -> Trendyol TR analizi"
    content = content.replace(OLD_HELP, NEW_HELP)

    with sftp.file("/opt/jarvis/openclaw/bridge.py", "w") as f:
        f.write(content)
    print("✅ bridge.py updated")

sftp.close()

# Syntax check + restart
_, sy, _ = client.exec_command("python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo OK 2>&1", get_pty=True)
sy_out = sy.read().decode().strip()
print(f"Syntax: {sy_out}")

if "OK" in sy_out:
    client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
    time.sleep(4)
    _, st, _ = client.exec_command("systemctl is-active jarvis.service")
    print(f"Service: {st.read().decode().strip()}")

client.close()
print("\nDone!")
print("\nArtık /opt/jarvis/printify_token.txt dosyasına Printify token yazınca /printify komutu çalışır.")
print("Token almak için: https://printify.com/app/account/connections")
