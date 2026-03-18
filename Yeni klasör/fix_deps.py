import paramiko

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host} to fix dependencies...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    print("--- Installing pyTelegramBotAPI ---")
    # Forcing pip install with break-system-packages. Using full paths.
    install_cmd = "python3 -m pip install pyTelegramBotAPI --break-system-packages"
    stdin, stdout, stderr = client.exec_command(install_cmd, get_pty=True)
    
    for line in iter(stdout.readline, ""):
        print(line, end="")
        
    print("--- Restarting Bot ---")
    start_cmd = "nohup python3 /home/userk/telegram_gateway.py > /home/userk/gateway.log 2>&1 &"
    client.exec_command(start_cmd)
    print("Bot restarted.")

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
