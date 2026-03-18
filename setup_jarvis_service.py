"""
Convert Jarvis bridge.py to a systemd service.
"""
import paramiko
import time

host, username, password = "192.168.1.109", "userk", "userk1"

SERVICE = """[Unit]
Description=Jarvis Mission Control v2.0 - Multi-Model AI Gateway
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=userk
WorkingDirectory=/opt/jarvis/openclaw
ExecStart=/usr/bin/python3 /opt/jarvis/openclaw/bridge.py
Restart=always
RestartSec=5
StandardOutput=append:/home/userk/.jarvis/jarvis.log
StandardError=append:/home/userk/.jarvis/jarvis.log
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    print("Connected.")

    # Step 1: Kill existing bridge process
    print("\n[1/6] Stopping existing bridge process...")
    client.exec_command("pkill -f bridge.py 2>/dev/null")
    time.sleep(2)

    # Step 2: Disable old conflicting services
    print("[2/6] Disabling old openclaw/gateway services...")
    client.exec_command("echo 'userk1' | sudo -S systemctl stop openclaw.service gateway.service 2>/dev/null")
    client.exec_command("echo 'userk1' | sudo -S systemctl disable openclaw.service gateway.service 2>/dev/null")

    # Step 3: Upload new service file
    print("[3/6] Creating jarvis.service...")
    sftp = client.open_sftp()
    with sftp.file("/tmp/jarvis.service", "w") as f:
        f.write(SERVICE)
    sftp.close()

    # Move to systemd
    client.exec_command("echo 'userk1' | sudo -S cp /tmp/jarvis.service /etc/systemd/system/jarvis.service")
    client.exec_command("echo 'userk1' | sudo -S chmod 644 /etc/systemd/system/jarvis.service")

    time.sleep(1)

    # Step 4: Reload systemd
    print("[4/6] Reloading systemd daemon...")
    _, so, _ = client.exec_command("echo 'userk1' | sudo -S systemctl daemon-reload", get_pty=True)
    so.channel.recv_exit_status()

    # Step 5: Enable + start
    print("[5/6] Enabling and starting jarvis.service...")
    _, so2, _ = client.exec_command("echo 'userk1' | sudo -S systemctl enable jarvis.service 2>&1", get_pty=True)
    print("  Enable:", so2.read().decode().strip())

    _, so3, _ = client.exec_command("echo 'userk1' | sudo -S systemctl start jarvis.service 2>&1", get_pty=True)
    print("  Start:", so3.read().decode().strip() or "OK")

    time.sleep(4)

    # Step 6: Verify
    print("[6/6] Verifying service status...")
    _, so4, _ = client.exec_command("systemctl status jarvis.service --no-pager -l", get_pty=True)
    status = so4.read().decode()
    print(status[:1500])

    # Check port
    _, so5, _ = client.exec_command("ss -tlnp | grep 8080")
    port = so5.read().decode()
    print("\nPort 8080:", port if port.strip() else "(not yet ready)")

    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()

print("\nDone.")
