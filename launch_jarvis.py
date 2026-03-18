"""
Permanently start Jarvis bridge.py and verify.
"""
import paramiko, time

host, username, password = "192.168.1.109", "userk", "userk1"
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    
    # Kill anything conflicting
    client.exec_command("pkill -f bridge.py 2>/dev/null; pkill -f telegram_gateway.py 2>/dev/null")
    time.sleep(2)
    
    # Start permanently
    client.exec_command("mkdir -p /home/userk/.jarvis")
    client.exec_command(
        "nohup python3 /opt/jarvis/openclaw/bridge.py > /home/userk/.jarvis/jarvis.log 2>&1 &"
    )
    time.sleep(5)
    
    # Verify
    _, ps, _ = client.exec_command("ps aux | grep bridge.py | grep -v grep | awk '{print $2, $11}'")
    pid = ps.read().decode().strip()
    print(f"PID: {pid}")
    
    _, log, _ = client.exec_command("tail -15 /home/userk/.jarvis/jarvis.log")
    print(log.read().decode())
    
    _, port, _ = client.exec_command("ss -tlnp | grep 8080")
    print("Port 8080:", port.read().decode() or "still loading...")
    
    client.close()
except Exception as e:
    print(f"Error: {e}")
