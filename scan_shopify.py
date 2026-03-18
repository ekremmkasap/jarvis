"""
Shopify Store Scanner for Jarvis Training
Store: vn3i8c-ks.myshopify.com
"""
import json
import time
from urllib.request import urlopen, Request
from urllib.error import URLError

STORE = "vn3i8c-ks.myshopify.com"
CLIENT_ID = "658472d581c8894deb450f7f6f9de137"
CLIENT_SECRET = "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"

def fetch_public_products():
    """Public Shopify products.json endpoint - no auth needed"""
    all_products = []
    page = 1
    
    while True:
        url = f"https://{STORE}/products.json?limit=250&page={page}"
        try:
            req = Request(url, headers={"User-Agent": "Jarvis/1.0"})
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
                products = data.get("products", [])
                if not products:
                    break
                all_products.extend(products)
                print(f"  Page {page}: {len(products)} products fetched")
                if len(products) < 250:
                    break
                page += 1
                time.sleep(0.5)
        except Exception as e:
            print(f"  Public API error: {e}")
            break
    
    return all_products

def try_catalog_api_token():
    """Try to get access token with client credentials"""
    try:
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
            data = json.loads(resp.read())
            token = data.get("access_token")
            if token:
                print(f"  Got access token: {token[:20]}...")
                return token
    except Exception as e:
        print(f"  Token exchange: {e}")
    return None

def format_knowledge(products):
    """Format product data for Jarvis knowledge base"""
    lines = ["# Shopify Mağaza Ürün Kataloğu", f"# Store: {STORE}", f"# Toplam: {len(products)} ürün", ""]
    
    # Summary stats
    total_variants = sum(len(p.get("variants", [])) for p in products)
    vendors = list(set(p.get("vendor", "") for p in products if p.get("vendor")))
    types = list(set(p.get("product_type", "") for p in products if p.get("product_type")))
    
    lines.append(f"## Özet")
    lines.append(f"- Toplam Ürün: {len(products)}")
    lines.append(f"- Toplam Varyant: {total_variants}")
    lines.append(f"- Tedarikçiler: {', '.join(vendors[:10]) or 'Belirtilmemiş'}")
    lines.append(f"- Kategoriler: {', '.join(types[:10]) or 'Belirtilmemiş'}")
    lines.append("")
    lines.append("## Ürün Listesi")
    
    for i, p in enumerate(products, 1):
        variants = p.get("variants", [])
        prices = [float(v.get("price", 0)) for v in variants if v.get("price")]
        min_price = min(prices) if prices else 0
        max_price = max(prices) if prices else 0
        
        stock = sum(v.get("inventory_quantity", 0) for v in variants)
        
        price_str = f"${min_price:.2f}" if min_price == max_price else f"${min_price:.2f} - ${max_price:.2f}"
        
        lines.append(f"\n### {i}. {p.get('title', 'Ürün')}")
        lines.append(f"- **Fiyat:** {price_str}")
        lines.append(f"- **Stok:** {stock} adet")
        lines.append(f"- **Tür:** {p.get('product_type', '-')}")
        lines.append(f"- **Tedarikçi:** {p.get('vendor', '-')}")
        lines.append(f"- **Etiketler:** {p.get('tags', '-')}")
        lines.append(f"- **Handle:** {p.get('handle', '-')}")
        
        if variants and len(variants) > 1:
            lines.append(f"- **Varyantlar:** {len(variants)} adet")
            for v in variants[:3]:
                lines.append(f"  - {v.get('title', '')} — ${v.get('price', '?')} (Stok: {v.get('inventory_quantity', '?')})")
    
    return "\n".join(lines)

print(f"=== Shopify Store Scanner ===")
print(f"Store: {STORE}")
print()

# Try catalog API token first
print("[1] Catalog API token deneniyor...")
token = try_catalog_api_token()

# Fetch public products
print("[2] Public products API çekiliyor...")
products = fetch_public_products()

if products:
    print(f"\n✅ {len(products)} ürün bulundu!")
    
    # Save raw JSON
    with open(r"C:\Users\sergen\Desktop\jarvis-mission-control\knowledge\shopify_raw.json", "w", encoding="utf-8") as f:
        json.dump({"store": STORE, "products": products}, f, ensure_ascii=False, indent=2)
    print("  shopify_raw.json kaydedildi")
    
    # Save formatted knowledge
    knowledge_text = format_knowledge(products)
    with open(r"C:\Users\sergen\Desktop\jarvis-mission-control\knowledge\shopify_store.md", "w", encoding="utf-8") as f:
        f.write(knowledge_text)
    print("  shopify_store.md kaydedildi")
    
    # Print summary
    print("\n=== Ürün Özeti ===")
    for p in products[:5]:
        variants = p.get("variants", [])
        prices = [v.get("price", "?") for v in variants[:1]]
        print(f"  - {p.get('title', '?')} | ${prices[0] if prices else '?'}")
    if len(products) > 5:
        print(f"  ... ve {len(products)-5} tane daha")
else:
    print("\n⚠️ Public API'dan ürün gelmedi — mağaza passwordlu olabilir")
    print("Admin API token gerekiyor.")
    
    # Try with client secret as admin token
    print("\n[3] Storefront API deneniyor...")
    try:
        url = f"https://{STORE}/api/2024-01/products.json?limit=10"
        req = Request(url, headers={
            "X-Shopify-Access-Token": CLIENT_SECRET,
            "Content-Type": "application/json"
        })
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            prods = data.get("products", [])
            print(f"  Storefront: {len(prods)} ürün!")
    except Exception as e:
        print(f"  Storefront: {e}")

print("\nDone!")
