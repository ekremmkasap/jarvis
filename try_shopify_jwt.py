"""
Use the JWT token from Catalog API to try Admin API access
"""
import json
from urllib.request import urlopen, Request

STORE = "vn3i8c-ks.myshopify.com"
CLIENT_ID = "658472d581c8894deb450f7f6f9de137"
CLIENT_SECRET = "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"

# Step 1: Get JWT token
print("[1] Getting JWT token...")
payload = json.dumps({
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "grant_type": "client_credentials"
}).encode()

req = Request(
    "https://api.shopify.com/auth/access_token",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST"
)
with urlopen(req, timeout=10) as resp:
    token_data = json.loads(resp.read())

token = token_data.get("access_token", "")
print(f"  Token: {token[:40]}...")

# Step 2: Try Admin API with JWT
print("\n[2] Admin API denenecek sorular...")

endpoints = [
    f"https://{STORE}/admin/api/2024-01/shop.json",
    f"https://{STORE}/admin/api/2024-01/products.json?limit=5",
    f"https://admin.shopify.com/store/vn3i8c-ks/api/2024-01/products.json?limit=5",
]

for url in endpoints:
    try:
        req2 = Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        with urlopen(req2, timeout=8) as resp:
            data = json.loads(resp.read())
            print(f"  ✅ SUCCESS: {url}")
            print(f"     Data keys: {list(data.keys())}")
            if "products" in data:
                for p in data["products"][:3]:
                    print(f"     - {p['title']} | ${p['variants'][0]['price']}")
            break
    except Exception as e:
        print(f"  ❌ {url.split('/admin')[0]}: {str(e)[:60]}")

# Step 3: Try Catalog MCP endpoint for store products
print("\n[3] Catalog MCP deniyor...")
try:
    catalog_payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_global_products",
            "arguments": {
                "id": 1,
                "query": "",
                "context": f"shop:{STORE}",
                "limit": 10
            }
        }
    }).encode()
    
    req3 = Request(
        "https://discover.shopifyapps.com/global/mcp",
        data=catalog_payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        },
        method="POST"
    )
    with urlopen(req3, timeout=15) as resp:
        catalog_data = json.loads(resp.read())
        print(f"  Catalog result: {json.dumps(catalog_data, indent=2)[:500]}")
except Exception as e:
    print(f"  Catalog MCP: {e}")

print("\nDone.")
