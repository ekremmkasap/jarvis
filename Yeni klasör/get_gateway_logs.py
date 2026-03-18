import paramiko

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    print("--- gateway.log head/tail (Checking for errors) ---")
    
    # Read last 50 lines to find the crash trace
    cmd = "cat /home/userk/gateway.log | tail -n 50"
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    
    if out:
        print(out)
    if err:
        print(f"Stderr: {err}")
        
    print("--- Process Check ---")
    cmd2 = "ps aux | grep telegram_gateway"
    stdin, stdout, stderr = client.exec_command(cmd2, get_pty=True)
    out2 = stdout.read().decode('utf-8')
    print(out2)

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
