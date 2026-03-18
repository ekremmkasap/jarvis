#!/usr/bin/env python3
"""
Jarvis eBay Skill — Ürün Araştırma ve Analiz Motoru
Kullanım: python3 ebay_research.py "şarj adaptörü"
"""

import json
import re
import subprocess
from urllib.request import urlopen, Request
from urllib.parse import urlencode, quote_plus

OLLAMA_URL = "http://127.0.0.1:11434"

# eBay arama (public RSS/API - ücretsiz)
EBAY_SEARCH_URL = "https://www.ebay.com/sch/i.html?_nkw={query}&_sop=12&rt=nc&LH_Sold=1&LH_Complete=1"

def ask_ollama(prompt: str, model: str = "llama3.2:latest") -> str:
    """Ollama'ya soru sor"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "system": """Sen uzman bir eBay dropshipping danışmanısın.
Piyasa analizi yapıyor, karlı ürünler buluyor, listing optimizasyonu yapıyorsun.
Net, pratik ve Türkçe cevap ver. Rakamlar ve verilerle destekle.""",
        "options": {"temperature": 0.6, "num_predict": 800}
    }
    data = json.dumps(payload).encode()
    req = Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            return result.get("message", {}).get("content", "Yanıt alınamadı")
    except Exception as e:
        return f"Hata: {e}"

def analyze_product(query: str) -> dict:
    """Ürün analizi yap"""
    
    # 1. Pazar analizi
    market_prompt = f"""eBay'de "{query}" için detaylı pazar analizi yap:

1. **Pazar Büyüklüğü**: Tahmini aylık satış hacmi
2. **Fiyat Aralığı**: Min/max/ortalama satış fiyatı (USD)
3. **Tedarik Maliyeti**: AliExpress/Amazon'dan temin fiyatı  
4. **Kar Marjı**: Tahmini net kar marjı %
5. **Rekabet Seviyesi**: Düşük/Orta/Yüksek + neden
6. **En İyi Satış Zamanı**: Mevsimsel mi?
7. **eBay Kategori**: Hangi kategoriye girmeli
8. **Risk**: Potansiyel sorunlar"""

    market_analysis = ask_ollama(market_prompt)
    
    # 2. Listing başlığı önerisi
    title_prompt = f"""eBay'de "{query}" için SEO optimize edilmiş 5 farklı listing başlığı yaz.
Her başlık max 80 karakter olsun.
Anahtar kelimeleri doğal yerleştir.
Format: 1. [Başlık]"""
    
    titles = ask_ollama(title_prompt)
    
    # 3. Tedarikçi önerileri
    supplier_prompt = f""""{query}" için en iyi tedarikçi kaynakları:
1. AliExpress'te arama terimleri (TR değil, İngilizce)
2. Amazon FBM tedarikçisi araması nasıl yapılır
3. Wholesale/toptan kaynaklar
4. Minimum sipariş miktarı önerileri
Kısa ve pratik yaz."""
    
    suppliers = ask_ollama(supplier_prompt)
    
    return {
        "query": query,
        "market_analysis": market_analysis,
        "listing_titles": titles,
        "suppliers": suppliers
    }

def format_report(result: dict) -> str:
    """Analizi formatla"""
    return f"""🛒 *eBay Ürün Analizi: {result['query']}*
━━━━━━━━━━━━━━━━━━━━

📊 *PAZAR ANALİZİ*
{result['market_analysis']}

━━━━━━━━━━━━━━━━━━━━
📝 *LİSTİNG BAŞLIKLARI*
{result['listing_titles']}

━━━━━━━━━━━━━━━━━━━━
🏭 *TEDARİKÇİ KAYNAKLARI*
{result['suppliers']}

━━━━━━━━━━━━━━━━━━━━
💡 Hızlı test: Ürünü AliExpress'ten 1 adet sipariş et, eBay'e al, sat."""

def quick_opportunity_scan() -> str:
    """Hızlı fırsat taraması — 5 trend ürün bul"""
    prompt = """Şu an eBay'de trend olan, az rekabetli ve yüksek kar marjlı 5 ürün kategori öner.
Her biri için:
- Ürün adı
- Tahmini kar marjı %
- Neden şu an fırsat
Bir paragraf maks, sadece liste. Türkçe."""
    
    return ask_ollama(prompt)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"\nAnaliz yapılıyor: {query}...\n")
        result = analyze_product(query)
        print(format_report(result))
    else:
        print("Hızlı Fırsat Taraması:\n")
        print(quick_opportunity_scan())
