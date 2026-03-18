import paramiko

host = "192.168.1.109"
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)

    cmds = [
        ("Ollama status", "systemctl status ollama --no-pager 2>/dev/null || echo 'checking ollama serve...' && pgrep -a ollama"),
        ("Ollama models", "ollama list 2>/dev/null"),
        ("OpenClaw processes", "ps aux | grep -E 'openclaw|gateway' | grep -v grep"),
        ("OpenClaw start log", "cat /home/userk/openclaw-ollama.log 2>/dev/null | tail -20"),
        ("Telegram Gateway service", "echo 'userk1' | sudo -S systemctl status gateway.service --no-pager 2>/dev/null"),
        ("OpenClaw service", "echo 'userk1' | sudo -S systemctl status openclaw.service --no-pager 2>/dev/null"),
    ]

    for title, cmd in cmds:
        print(f"\n{'='*40}\n=== {title} ===\n{'='*40}")
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        print(stdout.read().decode('utf-8')[:500])

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
