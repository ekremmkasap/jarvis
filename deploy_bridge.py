"""
Deploy the real Jarvis bridge.py to the SSH server at /opt/jarvis/openclaw/bridge.py
"""
import paramiko

host = "192.168.1.109"
username = "userk"
password = "userk1"
src = r"C:\Users\sergen\Desktop\jarvis-mission-control\src\runtime\dev\bridge.py"
dst = "/opt/jarvis/openclaw/bridge.py"

transport = None
try:
    print("Connecting via SFTP...")
    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    # Backup old bridge.py
    try:
        sftp.rename(dst, dst + ".stub.bak")
        print(f"Backup: {dst}.stub.bak")
    except:
        pass

    # Upload new bridge.py
    sftp.put(src, dst)
    print(f"SUCCESS: bridge.py uploaded to {dst}")

    sftp.close()

    # Restart services via SSH
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, timeout=10)

    # Stop old openclaw service (placeholder bridge)
    client.exec_command("echo 'userk1' | sudo -S systemctl stop openclaw.service 2>/dev/null")

    # Stop old Telegram gateway
    client.exec_command("echo 'userk1' | sudo -S systemctl stop gateway.service 2>/dev/null")
    client.exec_command("pkill -f telegram_gateway.py 2>/dev/null")

    # Install dependencies
    _, so, se = client.exec_command("pip3 install requests 2>&1 | tail -3")
    print(so.read().decode())

    # Start the new bridge.py directly (includes Telegram + Web)
    client.exec_command(
        f"nohup python3 {dst} > /home/userk/.jarvis/startup.log 2>&1 &"
    )
    print("Jarvis bridge.py started!")

    import time
    time.sleep(3)

    # Check startup log
    _, so2, _ = client.exec_command("cat /home/userk/.jarvis/startup.log 2>/dev/null | head -20")
    log = so2.read().decode()
    print("\n=== Startup Log ===")
    print(log if log else "(log boş — başlatılıyor olabilir)")

    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
finally:
    if transport:
        transport.close()
    print("\nDone.")
