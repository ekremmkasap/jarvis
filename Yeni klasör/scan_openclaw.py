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
        "OpenClaw locations": "find / -name 'openclaw*' -type f 2>/dev/null | head -20",
        "OpenClaw logs (journalctl)": "journalctl -u openclaw.service -n 30 --no-pager",
        "Ollama status": "ollama list 2>/dev/null && echo 'Ollama OK'",
        "Existing env/config files": "find /opt /home -name '*.env' -o -name '*.conf' -o -name 'config.*' 2>/dev/null | grep -i 'openclaw\\|gateway\\|jarvis' | head -20",
        "Running processes": "ps aux | grep -E 'openclaw|gateway|jarvis' | grep -v grep",
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
