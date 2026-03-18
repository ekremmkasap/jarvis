import paramiko

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host} for debugging...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    print("--- Process List ---")
    stdin, stdout, stderr = client.exec_command("ps aux | grep telegram", get_pty=True)
    print(stdout.read().decode('utf-8'))
    
    print("--- gateway.log ---")
    stdin, stdout, stderr = client.exec_command("cat /home/userk/gateway.log", get_pty=True)
    print(stdout.read().decode('utf-8'))

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
