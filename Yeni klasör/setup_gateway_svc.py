import paramiko

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

# The bash script that will be executed on the Kali server 
setup_script = """#!/bin/bash
echo "=== Establishing Telegram Gateway Systemd Service ==="

SERVICE_FILE="/etc/systemd/system/gateway.service"

sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=Telegram Gateway Bot Service
After=network.target openclaw.service

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/userk
ExecStart=/usr/bin/python3 /home/userk/telegram_gateway.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=telegram_gateway

[Install]
WantedBy=multi-user.target
EOF

echo "userk1" | sudo -S systemctl daemon-reload
echo "userk1" | sudo -S systemctl enable gateway.service
echo "userk1" | sudo -S systemctl restart gateway.service
echo "userk1" | sudo -S systemctl status gateway.service --no-pager
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    sftp = client.open_sftp()
    with sftp.file('/home/userk/setup_gateway_service.sh', 'w') as f:
        f.write(setup_script)
    sftp.close()
    
    cmd = "chmod +x /home/userk/setup_gateway_service.sh && echo 'userk1' | sudo -S /home/userk/setup_gateway_service.sh"
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
