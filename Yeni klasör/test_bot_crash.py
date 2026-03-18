import paramiko

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host} for synchronous crash test...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    print("--- Running Bot Synchronously ---")
    # This will block and print whatever Python outputs before crashing
    stdin, stdout, stderr = client.exec_command("python3 /home/userk/telegram_gateway.py", get_pty=True)
    
    # Check output
    for _ in range(30): # Read up to 30 lines
        line = stdout.readline()
        if not line: break
        print(line.strip())

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
