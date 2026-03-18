"""
Printify Skill for Jarvis
Manages print-on-demand products, shops, orders via Printify API
"""
import json
import os
from urllib.request import urlopen, Request
from urllib.error import URLError

PRINTIFY_API = "https://api.printify.com/v1"

def get_headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Jarvis/2.1"
    }

def _get(token: str, endpoint: str) -> dict:
    """Make a GET request to Printify API"""
    try:
        req = Request(
            f"{PRINTIFY_API}{endpoint}",
            headers=get_headers(token)
        )
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except URLError as e:
        return {"error": str(e)}

def get_shops(token: str) -> list:
    """Get all shops connected to Printify account"""
    data = _get(token, "/shops.json")
    if "error" in data:
        return []
    return data if isinstance(data, list) else data.get("data", [])

def get_products(token: str, shop_id: str, limit: int = 20) -> list:
    """Get all products in a shop"""
    data = _get(token, f"/shops/{shop_id}/products.json?limit={limit}")
    if "error" in data:
        return []
    return data.get("data", [])

def get_orders(token: str, shop_id: str, limit: int = 10) -> list:
    """Get recent orders"""
    data = _get(token, f"/shops/{shop_id}/orders.json?limit={limit}")
    if "error" in data:
        return []
    return data.get("data", [])

def get_catalog_blueprints(token: str) -> list:
    """Get available print products (t-shirts, mugs, etc.)"""
    data = _get(token, "/catalog/blueprints.json")
    if "error" in data:
        return []
    return data if isinstance(data, list) else []

def get_product_details(token: str, shop_id: str, product_id: str) -> dict:
    """Get detailed info about a specific product"""
    return _get(token, f"/shops/{shop_id}/products/{product_id}.json")

def format_overview(token: str) -> str:
    """Full Printify account overview for Jarvis"""
    shops = get_shops(token)
    if not shops:
        return "❌ Printify'a bağlanılamadı. Token geçerli mi?"

    lines = ["**Printify Mağaza Durumu**\n"]

    for shop in shops:
        shop_id = str(shop.get("id", ""))
        shop_title = shop.get("title", "Mağaza")
        sales_channel = shop.get("sales_channel", "-")

        lines.append(f"🏪 **{shop_title}** ({sales_channel})")

        # Products
        products = get_products(token, shop_id, limit=50)
        lines.append(f"  📦 Toplam Ürün: {len(products)}")

        if products:
            lines.append("  **Son Ürünler:**")
            for p in products[:5]:
                title = p.get("title", "-")
                visible = "Yayında" if p.get("visible") else "Gizli"
                variants = len(p.get("variants", []))
                lines.append(f"  - {title} | {variants} varyant | {visible}")

        # Orders
        orders = get_orders(token, shop_id, limit=5)
        if orders:
            lines.append(f"\n  📋 Son Siparişler: {len(orders)}")
            for o in orders:
                order_id = o.get("id", "-")
                status = o.get("status", "-")
                total = o.get("total_price", "?")
                lines.append(f"  - #{order_id} | {status} | ${total}")

        lines.append("")

    return "\n".join(lines)

def analyze_product_opportunity(token: str, niche: str) -> str:
    """Analyze a product niche for Printify opportunities"""
    blueprints = get_catalog_blueprints(token)

    niche_map = {
        "tshirt": ["t-shirt", "tee", "shirt"],
        "mug": ["mug", "cup", "kupa"],
        "hoodie": ["hoodie", "sweatshirt"],
        "poster": ["poster", "print", "art"],
        "phone_case": ["phone", "case", "telefon"],
        "tote": ["tote", "bag", "çanta"],
    }

    niche_lower = niche.lower()
    matching = []

    for bp in blueprints[:100]:
        title = bp.get("title", "").lower()
        if any(kw in title for kw in [niche_lower] + niche_map.get(niche_lower, [])):
            matching.append(bp)

    if not matching:
        matching = blueprints[:5]  # fallback

    lines = [f"**Printify '{niche}' Analizi**\n"]
    lines.append(f"Bulunan ürün tipi: {len(matching)}\n")
    for bp in matching[:5]:
        lines.append(f"- {bp.get('title', '-')} | ID: {bp.get('id', '-')}")
    lines.append("\n📌 Bu ürünleri Shopify mağazana ekleyebilirsin.")

    return "\n".join(lines)


# CLI test
if __name__ == "__main__":
    token = os.environ.get("PRINTIFY_TOKEN", "")
    if not token:
        print("PRINTIFY_TOKEN env variable gerekli")
    else:
        print(format_overview(token))
