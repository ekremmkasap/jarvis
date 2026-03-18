import paramiko
import json

host = "192.168.1.109"
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    
    print("=== Reading openclaw.json ===")
    stdin, stdout, stderr = client.exec_command("cat /home/userk/.openclaw/openclaw.json", get_pty=True)
    config_raw = stdout.read().decode('utf-8')
    print(config_raw[:3000])
    
    print("\n=== Reading openclaw.json.bak (original) ===")
    stdin2, stdout2, _ = client.exec_command("cat /home/userk/.openclaw/openclaw.json.bak", get_pty=True)
    print(stdout2.read().decode('utf-8')[:2000])
    
    print("\n=== Ollama models available ===")
    stdin3, stdout3, _ = client.exec_command("ollama list 2>/dev/null || echo 'Ollama not responding'", get_pty=True)
    print(stdout3.read().decode('utf-8'))
    
    print("\n=== OpenClaw config keys (looking for model/provider settings) ===")
    stdin4, stdout4, _ = client.exec_command("cat /home/userk/.openclaw/openclaw.json | python3 -c \"import sys,json; d=json.load(sys.stdin); print(json.dumps(d, indent=2))\" 2>/dev/null | head -80", get_pty=True)
    print(stdout4.read().decode('utf-8'))

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
