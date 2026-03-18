import paramiko
import re

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    # 1. Search for typical token patterns in .env files, standard locations, and openclaw folders
    # Telegram tokens look like "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ"
    search_cmd = """
echo "=== Searching for Telegram Tokens & Chat IDs ==="
find ~ /opt /etc /var/www -type f \( -name "*.env" -o -name "*.js" -o -name "*.py" -o -name "*.json" \) 2>/dev/null | xargs grep -iE 'telegram|token|bot.*token|chat.*id|chat_id' | head -n 50
echo "=== Search Complete ==="
"""
    stdin, stdout, stderr = client.exec_command(search_cmd, get_pty=True)
    result = stdout.read().decode('utf-8')
    print(result)

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
