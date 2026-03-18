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

    cmds = {
        "openclaw.json (current config)": "cat /home/userk/.openclaw/openclaw.json",
        "openclaw-gateway.log (errors)": "cat /home/userk/openclaw-gateway.log | tail -50",
        "openclaw today log": "cat /tmp/openclaw/openclaw-2026-02-28.log | tail -50",
        "Available Ollama models": "ollama list",
        "Extensions list": "ls /usr/lib/node_modules/openclaw/extensions/",
    }

    for title, cmd in cmds.items():
        print(f"\n{'='*20}\n=== {title} ===\n{'='*20}")
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        out = stdout.read().decode('utf-8')
        print(out if out else "(no output)")

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
