import paramiko, json

# Read token
with open(r'C:\Users\sergen\Desktop\printify_token.txt.txt', 'r') as f:
    token = f.read().strip().replace(' ', '').replace('\n','').replace('\r','')

print(f"Token: {token[:40]}... ({len(token)} chars)")

# Connect to server
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)

# Save token to server
sftp = client.open_sftp()
with sftp.file('/opt/jarvis/printify_token.txt', 'w') as f:
    f.write(token)
sftp.close()
print('Token saved to server!')

# Write test script to server
test_script = '''
import json
from urllib.request import urlopen, Request

token = open('/opt/jarvis/printify_token.txt').read().strip()
req = Request('https://api.printify.com/v1/shops.json', headers={
    'Authorization': 'Bearer ' + token,
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
})
try:
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    print("SUCCESS:", json.dumps(data)[:400])
except Exception as e:
    print("FAIL:", e)
'''

sftp2 = client.open_sftp()
with sftp2.file('/tmp/test_printify.py', 'w') as f:
    f.write(test_script)
sftp2.close()

# Run test from server
print("\nRunning test from server...")
stdin, stdout, stderr = client.exec_command('python3 /tmp/test_printify.py')
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:", out)
if err:
    print("STDERR:", err[:200])

client.close()
