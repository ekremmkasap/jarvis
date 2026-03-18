"""
Verify the Jarvis bridge.py is running correctly.
"""
import paramiko, time

host, username, password = "192.168.1.109", "userk", "userk1"
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    
    cmds = [
        ("Bridge process running?", "ps aux | grep bridge.py | grep -v grep"),
        ("Startup log", "cat /home/userk/.jarvis/startup.log 2>/dev/null"),
        ("Jarvis log", "cat /home/userk/.jarvis/jarvis.log 2>/dev/null | tail -20"),
        ("Port 8080 listening?", "ss -tlnp | grep 8080"),
    ]
    
    for title, cmd in cmds:
        print(f"\n=== {title} ===")
        _, so, _ = client.exec_command(cmd, get_pty=True)
        out = so.read().decode()
        print(out if out.strip() else "(boş)")

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
