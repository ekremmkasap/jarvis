"""
Run bridge.py directly to see Python errors.
"""
import paramiko, time

host, username, password = "192.168.1.109", "userk", "userk1"
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    
    # Run bridge.py directly for 5 seconds and capture output
    print("Running bridge.py directly (5 sec timeout)...")
    stdin, stdout, stderr = client.exec_command(
        "timeout 5 python3 /opt/jarvis/openclaw/bridge.py 2>&1 || true",
        get_pty=True
    )
    out = stdout.read().decode()
    print("Output:\n", out[:2000] if out else "(empty)")
    
    # Also check python3 syntax errors
    print("\n--- Syntax check ---")
    _, sy_out, sy_err = client.exec_command("python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo OK", get_pty=True)
    print(sy_out.read().decode())
    print(sy_err.read().decode())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
