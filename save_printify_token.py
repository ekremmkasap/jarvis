"""
Save Printify token to server and test the connection
"""
import paramiko, json
from urllib.request import urlopen, Request

# Token from screenshot (removing display whitespace)
TOKEN = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9."
    ".OWb_GpXOBZHNxXdRuCWSF5lSlQaDWgUq0"
    "cqSd9coSERFBf15aiCvvBjTq67-L1DnvoT-enyhFcRXl5TbNoz47MPL3iJoTnBhDe3_8G5VAU"
    "vAKBPQGCnggVsvsWPORkmApZyKForS8pCCSw3iNPB8OMldXfYlTnPje5wxwC4ZPR7W"
    "uKMvm7WEyeku7fllw30MUJmX6vSdjm5KRSrqdhpaSr65n1DgcSwlfx5rjOkwbGDU07-C6"
    "KbzDszVaX3JAs_6jxN2i15LTc79guW2PS21sdChFIUfDA4yQri--2hn5-6SLRCDGOZGRdz_o"
    "Plxb1vAlvZXn7BgA9mxmw03p-iKnKVbHN1yYtw-tqu4k8bu773XZgNDZuzeRP46yykUB46b"
    "0vrmB5s549l7Nmm9k-WXSHcvoxl_73JueAn8-Zm1LwveIVJXG_mdJGN70MqOblRorQh7"
    "HAsK7fcT0GvCe_Jvd7KwcVCiZ0hLcfiheHwYB-EdC4V7SvUIZOUWwbJ2MHe8IsyQkRE6"
    "MJ2LkB7lLujPzfMZ07bagHe55k5BvnfrN-Bu9symJW1SQ2W8tJ_RbJiDylFMlrd4_Cq9c1UF"
    "C4d0sZp5fm5sPKH3hfJ8a8CPCsr8xYjib17slhBd9AmXjBaPaZ1GnpzOW4dXmNJeH2BleE"
    "wlJlGayer0rlVN4qxjG6aY"
)

print("[1] Testing Printify API connection...")
try:
    req = Request(
        "https://api.printify.com/v1/shops.json",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
    )
    with urlopen(req, timeout=15) as resp:
        shops = json.loads(resp.read())
    print(f"✅ Connected! Shops: {shops}")
    success = True
except Exception as e:
    print(f"❌ API error: {e}")
    success = False

if success:
    print("\n[2] Saving token to server...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)
    sftp = client.open_sftp()
    with sftp.file("/opt/jarvis/printify_token.txt", "w") as f:
        f.write(TOKEN)
    print("  ✅ Token saved to /opt/jarvis/printify_token.txt")

    # Fetch and save all products
    print("\n[3] Fetching products...")
    all_products = []
    for shop in (shops if isinstance(shops, list) else [shops]):
        shop_id = str(shop.get("id", ""))
        shop_name = shop.get("title", "Shop")
        print(f"  Shop: {shop_name} (ID: {shop_id})")
        
        req2 = Request(
            f"https://api.printify.com/v1/shops/{shop_id}/products.json?limit=100",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )
        with urlopen(req2, timeout=20) as resp:
            products = json.loads(resp.read())
        
        prods = products.get("data", []) if isinstance(products, dict) else products
        all_products.extend(prods)
        print(f"  {len(prods)} products found")
    
    # Create knowledge file
    lines = ["# Printify Mağaza Verileri", f"# Toplam: {len(all_products)} ürün", ""]
    for p in all_products:
        title = p.get("title", "-")
        variants = len(p.get("variants", []))
        visible = "Yayında" if p.get("visible") else "Taslak"
        lines.append(f"- **{title}** | {variants} varyant | {visible}")
    
    knowledge = "\n".join(lines)
    with sftp.file("/opt/jarvis/knowledge/printify_store.md", "w") as f:
        f.write(knowledge)
    print("  ✅ Knowledge saved: /opt/jarvis/knowledge/printify_store.md")
    
    sftp.close()
    client.close()

print("\nDone!")
