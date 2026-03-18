"""
Deploy soul.md, heartbeat.py, ebay_research.py to the server.
Then update bridge.py to load soul.md as the master system prompt.
Also set up cron job for heartbeat at 08:00.
"""
import paramiko
import time

host, username, password = "192.168.1.109", "userk", "userk1"

files_to_upload = [
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\soul.md", 
     "/opt/jarvis/soul.md"),
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\heartbeat.py", 
     "/opt/jarvis/skills/heartbeat.py"),
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\ebay_research.py", 
     "/opt/jarvis/skills/ebay_research.py"),
]

transport = None
try:
    print("Connecting via SFTP...")
    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # Upload all files
    for src, dst in files_to_upload:
        sftp.put(src, dst)
        print(f"  ✅ {dst}")

    sftp.close()
    transport.close()
    transport = None

    # SSH for additional setup
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, timeout=10)

    # Make skills executable
    client.exec_command("chmod +x /opt/jarvis/skills/heartbeat.py /opt/jarvis/skills/ebay_research.py")

    # Set up cron job for heartbeat at 08:00 daily
    cron_cmd = (
        '(crontab -l 2>/dev/null | grep -v heartbeat; '
        'echo "0 8 * * * /usr/bin/python3 /opt/jarvis/skills/heartbeat.py >> /home/userk/.jarvis/heartbeat.log 2>&1") '
        '| crontab -'
    )
    client.exec_command(cron_cmd)
    time.sleep(1)

    # Verify cron
    _, co, _ = client.exec_command("crontab -l | grep heartbeat")
    cron_verify = co.read().decode().strip()
    print(f"\n  Cron: {cron_verify or 'not set'}")

    # Update bridge.py to load soul.md
    # Read current bridge.py SOUL_PROMPT section and add soul.md loading
    soul_patch = '''
# Load soul.md from disk if available
import os as _os
_SOUL_PATH = "/opt/jarvis/soul.md"
try:
    with open(_SOUL_PATH, "r") as _f:
        JARVIS_SOUL = _f.read()
    print(f"[soul] soul.md loaded ({len(JARVIS_SOUL)} chars)")
except:
    JARVIS_SOUL = "Sen Jarvis\\'sin, Ekrem\\'in AI asistanı."
'''
    # Write a small patcher
    sftp2 = client.open_sftp()
    with sftp2.file("/tmp/apply_soul.py", "w") as f:
        f.write(f'''
bridge_path = "/opt/jarvis/openclaw/bridge.py"
with open(bridge_path, "r") as f:
    content = f.read()

# Add soul loading after the CONFIG block if not already there
if "JARVIS_SOUL" not in content:
    insert_after = "log = logging.getLogger(\\"jarvis\\")"
    soul_code = """
# ─── SOUL (Kimlik) ────────────────────────────────────────────
try:
    with open("/opt/jarvis/soul.md", "r") as _f:
        JARVIS_SOUL = _f.read()
    log.info(f"✅ soul.md yüklendi")
except Exception as _e:
    JARVIS_SOUL = "Sen Jarvis\\'sin, Ekrem\\'in AI asistanı. Zeki, pratik, Tony Stark tarzı."
    log.warning(f"soul.md bulunamadı: {{_e}}")
"""
    content = content.replace(insert_after, insert_after + soul_code)
    
    # Update the chat MODEL_ROUTES system prompt to use JARVIS_SOUL
    content = content.replace(
        '"system": "Sen Jarvis\\'sin — Tony Stark\\'ın AI asistanı gibi zeki, yardımsever ve pratik bir AI. Türkçe ve İngilizce konuşabilirsin."',
        '"system": JARVIS_SOUL'
    )
    
    with open(bridge_path, "w") as f:
        f.write(content)
    print("bridge.py patched with soul.md")
else:
    print("bridge.py already has JARVIS_SOUL")
''')
    sftp2.close()

    _, sp_out, sp_err = client.exec_command("python3 /tmp/apply_soul.py", get_pty=True)
    sp_out.channel.recv_exit_status()
    print("\n  Soul patch:", sp_out.read().decode().strip())

    # Test heartbeat immediately
    print("\nTesting heartbeat (sending to Telegram)...")
    client.exec_command("python3 /opt/jarvis/skills/heartbeat.py &")
    
    # Restart jarvis service to pick up soul patch
    time.sleep(2)
    client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
    time.sleep(3)

    _, st, _ = client.exec_command("systemctl is-active jarvis.service")
    status = st.read().decode().strip()
    print(f"\n  jarvis.service: {status}")

    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
finally:
    if transport:
        transport.close()

print("\n✅ All done!")
