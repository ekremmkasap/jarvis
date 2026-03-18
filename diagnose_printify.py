import paramiko, json

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)

# Check internet from server
print("[1] Server internet connectivity...")
_, out, _ = client.exec_command('curl -s -m 5 -o /dev/null -w "%{http_code}" https://google.com')
print(f"  google.com: {out.read().decode().strip()}")

_, out, _ = client.exec_command('curl -s -m 8 -o /dev/null -w "%{http_code}" https://api.printify.com')
print(f"  api.printify.com: {out.read().decode().strip()}")

# Check token integrity
print("\n[2] Token check...")
with open(r'C:\Users\sergen\Desktop\printify_token.txt.txt', 'rb') as f:
    raw = f.read()

# Show all non-standard chars
import re
token_clean = re.sub(rb'[^\x21-\x7E]', b'', raw)  # Remove ALL non-printable chars
print(f"  Raw size: {len(raw)}, Clean size: {len(token_clean)}")
print(f"  Token: {token_clean.decode()[:50]}...")

# Save clean token
token_str = token_clean.decode()
sftp = client.open_sftp()
with sftp.file('/opt/jarvis/printify_token.txt', 'w') as f:
    f.write(token_str)
sftp.close()

# Test with clean token
print("\n[3] API test with clean token...")
test = '''
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError

token = open('/opt/jarvis/printify_token.txt').read().strip()
print(f"Token len: {len(token)}")
try:
    req = Request(
        'https://api.printify.com/v1/shops.json',
        headers={
            'Authorization': 'Bearer ' + token,
            'User-Agent': 'Mozilla/5.0 Chrome/121 Safari/537.36',
            'Accept': 'application/json',
        }
    )
    with urlopen(req, timeout=10) as resp:
        print("OK:", resp.read().decode()[:200])
except HTTPError as e:
    print(f"HTTP {e.code}:", e.read().decode()[:200])
except Exception as e:
    print(f"ERR: {type(e).__name__}: {e}")
'''
sftp2 = client.open_sftp()
with sftp2.file('/tmp/test_p2.py', 'w') as f:
    f.write(test)
sftp2.close()

_, out, err = client.exec_command('timeout 15 python3 /tmp/test_p2.py 2>&1')
result = out.read().decode()
print(f"  {result}")

client.close()
