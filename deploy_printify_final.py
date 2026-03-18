import json, paramiko
from urllib.request import urlopen, Request
from urllib.error import HTTPError

# Read and clean token
with open(r'C:\Users\sergen\Desktop\printify_token.txt.txt', 'r', encoding='utf-8') as f:
    token = f.read().strip().replace(' ', '').replace('\n', '').replace('\r', '')

print(f"Token length: {len(token)}")

# Test API
print("[1] Testing API...")
try:
    req = Request("https://api.printify.com/v1/shops.json",
                  headers={"Authorization": f"Bearer {token}"})
    with urlopen(req, timeout=20) as resp:
        shops = json.loads(resp.read())
    print(f"✅ Shops: {shops}")
except HTTPError as e:
    body = e.read().decode()
    print(f"❌ HTTP {e.code}: {body[:200]}")
    exit(1)
except Exception as e:
    print(f"❌ {e}")
    exit(1)

# Save to server
print("\n[2] Uploading to server...")
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)
sftp = client.open_sftp()

with sftp.file("/opt/jarvis/printify_token.txt", "w") as f:
    f.write(token)
print("  ✅ Token saved")

# Fetch products for each shop
shop_list = shops if isinstance(shops, list) else shops.get("data", [])
all_lines = ["# Printify Mağaza Ürünleri\n"]

for shop in shop_list:
    sid = str(shop.get("id", ""))
    sname = shop.get("title", "")
    print(f"\n[3] Products for shop: {sname} ({sid})")
    
    try:
        req2 = Request(f"https://api.printify.com/v1/shops/{sid}/products.json?limit=100",
                       headers={"Authorization": f"Bearer {token}"})
        with urlopen(req2, timeout=20) as resp:
            data = json.loads(resp.read())
        products = data.get("data", []) if isinstance(data, dict) else data
        print(f"  {len(products)} products")
        
        all_lines.append(f"\n## {sname} (ID: {sid})")
        for p in products:
            title = p.get("title", "-")
            variants = len(p.get("variants", []))
            visible = "✅ Yayında" if p.get("visible") else "📝 Taslak"
            all_lines.append(f"- {title} | {variants} varyant | {visible}")
    except Exception as e:
        print(f"  ⚠️ {e}")

with sftp.file("/opt/jarvis/knowledge/printify_store.md", "w") as f:
    f.write("\n".join(all_lines))
print("\n✅ printify_store.md saved!")

sftp.close()
client.close()
print("ALL DONE!")
