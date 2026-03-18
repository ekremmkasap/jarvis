import paramiko

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

# Script to create the systemd service for openclaw
setup_script = """#!/bin/bash
echo "=== Establishing OpenClaw Systemd Service ==="

SERVICE_FILE="/etc/systemd/system/openclaw.service"

sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=OpenClaw AI Orchestrator Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/jarvis/openclaw
ExecStart=/usr/bin/python3 /opt/jarvis/openclaw/bridge.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=openclaw

[Install]
WantedBy=multi-user.target
EOF

# Placeholder for bridge.py 
cat > /opt/jarvis/openclaw/bridge.py << EOF
import time
print("OpenClaw Bridge Starting...")
while True:
    time.sleep(60)
    print("OpenClaw heartbeat...")
EOF

echo "userk1" | sudo -S systemctl daemon-reload
echo "userk1" | sudo -S systemctl enable openclaw.service
echo "userk1" | sudo -S systemctl start openclaw.service
echo "userk1" | sudo -S systemctl status openclaw.service --no-pager
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    sftp = client.open_sftp()
    with sftp.file('/home/userk/setup_openclaw.sh', 'w') as f:
        f.write(setup_script)
    sftp.close()
    
    cmd = "chmod +x /home/userk/setup_openclaw.sh && echo 'userk1' | sudo -S /home/userk/setup_openclaw.sh"
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    
    print(out)
    if err:
        print(f"Errors: {err}")

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
