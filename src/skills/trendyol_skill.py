#!/usr/bin/env python3
"""
Jarvis Trendyol Skill — TR Pazar Araştırması
Trendyol'da ürün araştırması, fiyat analizi ve fırsat tespiti yapar.
"""

import json
import time
import re
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote

OLLAMA_URL = "http://127.0.0.1:11434"

TRENDYOL_SEARCH_API = "https://public.trendyol.com/discovery-sfint-service/api/infinite-scroll/sr/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.trendyol.com/",
    "Origin": "https://www.trendyol.com"
}

def search_trendyol(query: str, page: int = 1) -> dict:
    """Trendyol'da ürün ara"""
    params = {
        "q": query,
        "qt": query,
        "st": query,
        "os": 1,
        "sst": "BEST_SELLER",
        "pi": page,
        "pSize": 24,
    }
    
    url = f"{TRENDYOL_SEARCH_API}?{urlencode(params)}"
    
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def analyze_trendyol_results(data: dict, query: str) -> dict:
    """Trendyol sonuçlarını analiz et"""
    if "error" in data:
        return data
    
    products = []
    try:
        items = data.get("result", {}).get("products", [])
        
        for item in items[:10]:
            price = item.get("price", {})
            product = {
                "name": item.get("name", ""),
                "brand": item.get("brand", {}).get("name", ""),
                "price": price.get("discountedPrice", {}).get("value", 0),
                "orig_price": price.get("originalPrice", {}).get("value", 0),
                "discount": price.get("discountRatio", 0),
                "rating": item.get("ratingScore", {}).get("averageRating", 0),
                "reviews": item.get("ratingScore", {}).get("totalRatingCount", 0),
                "category": item.get("categoryHierarchy", ""),
                "seller": item.get("merchantName", ""),
            }
            products.append(product)
    except:
        pass
    
    if not products:
        return {"error": "Ürün bulunamadı"}
    
    prices = [p["price"] for p in products if p["price"] > 0]
    
    return {
        "query": query,
        "count": len(products),
        "avg_price": round(sum(prices) / len(prices), 2) if prices else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "products": products
    }

def ask_ollama_trendyol(query: str, market_data: dict) -> str:
    """Trendyol verilerini AI ile analiz et"""
    products_summary = ""
    for i, p in enumerate(market_data.get("products", [])[:5], 1):
        products_summary += f"\n{i}. {p['name'][:50]} | {p['price']} TL | ⭐{p['rating']} ({p['reviews']} yorum) | {p['seller']}"
    
    prompt = f"""Trendyol'da "{query}" arama sonuçları:

Fiyat Aralığı: {market_data.get('min_price')} - {market_data.get('max_price')} TL (Ort: {market_data.get('avg_price')} TL)
Toplam Sonuç: {market_data.get('count')} ürün

İlk 5 Ürün:{products_summary}

Bu verilere dayanarak:
1. Bu ürün kategorisinde dropshipping fırsatı var mı?
2. AliExpress'ten getirip Trendyol'da satmak karlı mı?
3. Rekabet nasıl?
4. Fiyatlandırma önerisi nedir?
5. En büyük satıcı kim, nasıl rakabet edebiliriz?

Kısa ve pratik analiz yap. Türkçe, 5-6 cümle max."""

    payload = {
        "model": "llama3.2:latest",
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "system": "Sen bir e-ticaret uzmanısın. Veriye dayalı, pratik analizler yaparsın.",
        "options": {"temperature": 0.6, "num_predict": 600}
    }
    
    try:
        data = json.dumps(payload).encode()
        req = Request(
            f"{OLLAMA_URL}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "")
    except Exception as e:
        return f"AI analizi hatası: {e}"

def full_trendyol_analysis(query: str) -> str:
    """Tam Trendyol analizi yap ve formatla"""
    print(f"Trendyol'da aranıyor: {query}...")
    
    raw_data = search_trendyol(query)
    market_data = analyze_trendyol_results(raw_data, query)
    
    if "error" in market_data:
        # API çalışmıyorsa sadece AI analizi yap
        ai_prompt = f"""Trendyol'da "{query}" kategorisi için AI destekli pazar analizi yap:
1. Tahmini fiyat aralığı (TL)
2. Rekabet durumu
3. AliExpress karşılaştırması
4. Dropshipping fırsatı var mı?
Türkçe, kısa."""
        payload = {
            "model": "llama3.2:latest",
            "messages": [{"role": "user", "content": ai_prompt}],
            "stream": False,
            "options": {"num_predict": 400}
        }
        data = json.dumps(payload).encode()
        req = Request(f"{OLLAMA_URL}/api/chat", data=data,
                     headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            ai_text = result.get("message", {}).get("content", "")
        return f"🇹🇷 *Trendyol AI Analizi: {query}*\n\n{ai_text}"
    
    ai_analysis = ask_ollama_trendyol(query, market_data)
    
    products_text = ""
    for i, p in enumerate(market_data.get("products", [])[:5], 1):
        discount_str = f" (-%{p['discount']})" if p.get("discount") else ""
        products_text += f"\n{i}. *{p['name'][:45]}...*\n   💰 {p['price']} TL{discount_str} | ⭐{p['rating']} | 🏪 {p['seller']}"
    
    return f"""🇹🇷 *Trendyol Analizi: {query}*
━━━━━━━━━━━━━━━
📊 Fiyat: {market_data['min_price']}₺ — {market_data['max_price']}₺ (ort. {market_data['avg_price']}₺)
📦 Bulunan: {market_data['count']} ürün

🏆 *En İyi 5 Ürün*{products_text}

━━━━━━━━━━━━━━━
🤖 *Jarvis Analizi*
{ai_analysis}

━━━━━━━━━━━━━━━
🔗 Detay: trendyol.com/sr?q={quote(query)}"""

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "bluetooth kulaklık"
    print(full_trendyol_analysis(query))
