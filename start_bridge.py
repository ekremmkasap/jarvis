"""
Start the Jarvis bridge.py on the server with proper nohup handling.
"""
import paramiko, time

host, username, password = "192.168.1.109", "userk", "userk1"
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    
    # Make sure .jarvis dir exists
    client.exec_command("mkdir -p /home/userk/.jarvis")
    
    # Kill any old Telegram bots to free the API token
    client.exec_command("pkill -f telegram_gateway.py 2>/dev/null")
    client.exec_command("pkill -f bridge.py 2>/dev/null")
    time.sleep(1)
    
    # Start bridge.py with nohup
    start_cmd = "cd /opt/jarvis/openclaw && nohup python3 bridge.py > /home/userk/.jarvis/jarvis.log 2>&1 &"
    _, so, se = client.exec_command(start_cmd, get_pty=True)
    so.channel.recv_exit_status()
    time.sleep(4)
    
    # Check if running
    _, ps_out, _ = client.exec_command("ps aux | grep bridge.py | grep -v grep")
    ps = ps_out.read().decode()
    print("Processes:", ps if ps.strip() else "NOT RUNNING")
    
    # Check log
    _, log_out, _ = client.exec_command("cat /home/userk/.jarvis/jarvis.log | head -30")
    log = log_out.read().decode()
    print("\nLog:", log if log.strip() else "(empty)")
    
    # Check port 8080
    _, port_out, _ = client.exec_command("ss -tlnp | grep 8080")
    port = port_out.read().decode()
    print("\nPort 8080:", port if port.strip() else "(not listening)")
    
    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
