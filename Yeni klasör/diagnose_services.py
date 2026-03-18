import paramiko

host = "192.168.1.109"
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    
    # Step 1: Check what Ollama models exist
    print("=== Step 1: Check Ollama models ===")
    _, so, _ = client.exec_command("ollama list 2>&1", get_pty=True)
    ollama_models = so.read().decode()
    print(ollama_models)
    
    # Step 2: Check Telegram bot crash reason
    print("\n=== Step 2: Telegram Gateway crash log ===")
    _, so2, _ = client.exec_command("journalctl -u gateway.service -n 20 --no-pager", get_pty=True)
    print(so2.read().decode()[:1000])
    
    # Step 3: Check if the real openclaw (node) binary exists
    print("\n=== Step 3: Find the real OpenClaw binary ===")
    _, so3, _ = client.exec_command("which openclaw && openclaw --version 2>/dev/null", get_pty=True)
    print(so3.read().decode())
    
    # Step 4: Check if the real openclaw-gateway process is running
    print("\n=== Step 4: Real OpenClaw gateway process ===")
    _, so4, _ = client.exec_command("ps aux | grep -E 'node|openclaw' | grep -v grep", get_pty=True)
    print(so4.read().decode())
    
    # Step 5: Check the openclaw gateway user service
    print("\n=== Step 5: User-level openclaw-gateway service ===")
    _, so5, _ = client.exec_command("systemctl --user status openclaw-gateway.service --no-pager 2>/dev/null", get_pty=True)
    print(so5.read().decode()[:500])

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
