#!/usr/bin/env python3
"""
Jarvis eBay Skill — Ürün Araştırma ve Analiz Motoru
Gerçek eBay sold listings verisi + model_router üzerinden hızlı AI analizi.
"""

import re
import logging
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

EBAY_SOLD_URL = (
    "https://www.ebay.com/sch/i.html?_nkw={query}&_sop=12&LH_Sold=1&LH_Complete=1&rt=nc"
)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ── LLM helper ──────────────────────────────────────────────────────────────


def _ask_model(prompt: str, system: str = "") -> str:
    """model_router varsa kullan, yoksa Ollama fallback."""
    try:
        import sys

        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "server"))
        from model_router import build_model_router

        router = build_model_router(
            root_dir=root,
            default_ollama_url="http://127.0.0.1:11434",
            request_timeout=60,
        )
        response, _trace = router.chat(
            route_name="default",
            primary_model="gemma4:e2b",
            fallback_model=None,
            messages=[{"role": "user", "content": prompt}],
            system=system or _EBAY_SYSTEM,
            max_tokens=600,
            num_ctx=8192,
        )
        return response
    except Exception:
        pass
    # Ollama fallback
    import json
    from urllib.request import urlopen, Request

    payload = json.dumps(
        {
            "model": "gemma4:e2b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 600},
        }
    ).encode()
    try:
        req = Request(
            "http://127.0.0.1:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=60) as r:
            import json as _j

            return _j.loads(r.read()).get("message", {}).get("content", "")
    except Exception as e:
        return f"Model hatası: {e}"


_EBAY_SYSTEM = (
    "Sen uzman bir eBay dropshipping danışmanısın. "
    "Piyasa analizi yapıyor, karlı ürünler buluyor, listing optimizasyonu yapıyorsun. "
    "Net, pratik ve Türkçe cevap ver. Rakamlar ve verilerle destekle."
)


# ── Gerçek eBay verisi ───────────────────────────────────────────────────────


def fetch_ebay_sold_prices(query: str, max_items: int = 20) -> dict:
    """
    eBay Sold Listings sayfasını scrape eder.
    Returns: {min_price, max_price, avg_price, count, prices: list[float]}
    Hata durumunda: {error: str}
    """
    try:
        from bs4 import BeautifulSoup

        url = EBAY_SOLD_URL.format(query=quote_plus(query))
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        soup = BeautifulSoup(html, "html.parser")
        price_tags = soup.select("span.s-item__price")
        prices = []
        for tag in price_tags[:max_items]:
            text = tag.get_text()
            # "$12.99" veya "$10.00 to $15.00" — ilk sayıyı al
            nums = re.findall(r"\d[\d,.]*", text.replace(",", ""))
            if nums:
                try:
                    prices.append(float(nums[0]))
                except ValueError:
                    pass

        if not prices:
            return {"error": "Fiyat verisi bulunamadı (scrape başarısız)"}

        return {
            "min_price": round(min(prices), 2),
            "max_price": round(max(prices), 2),
            "avg_price": round(sum(prices) / len(prices), 2),
            "count": len(prices),
            "prices": prices,
        }
    except ImportError:
        return {"error": "beautifulsoup4 yüklü değil"}
    except Exception as e:
        logger.warning(f"eBay scrape hatası: {e}")
        return {"error": str(e)}


# ── Analiz fonksiyonları ─────────────────────────────────────────────────────


def analyze_product(query: str) -> dict:
    """Ürün analizi yap — gerçek fiyat + AI yorumu."""

    # 1. Gerçek satış fiyatları
    price_data = fetch_ebay_sold_prices(query)

    price_context = ""
    if "error" not in price_data:
        price_context = (
            f"Gerçek eBay Sold fiyatları: "
            f"${price_data['min_price']} — ${price_data['max_price']} "
            f"(ortalama ${price_data['avg_price']}, {price_data['count']} satış)\n\n"
        )

    # 2. Pazar analizi (AI)
    market_prompt = (
        f"{price_context}"
        f'eBay\'de "{query}" için detaylı pazar analizi yap:\n'
        "1. Pazar Büyüklüğü: Tahmini aylık satış hacmi\n"
        "2. Fiyat Aralığı: Min/max/ortalama satış fiyatı (USD)\n"
        "3. Tedarik Maliyeti: AliExpress/Amazon'dan temin fiyatı\n"
        "4. Kar Marjı: Tahmini net kar marjı %\n"
        "5. Rekabet Seviyesi: Düşük/Orta/Yüksek + neden\n"
        "6. En İyi Satış Zamanı: Mevsimsel mi?\n"
        "7. eBay Kategori: Hangi kategoriye girmeli\n"
        "8. Risk: Potansiyel sorunlar"
    )
    market_analysis = _ask_model(market_prompt)

    # 3. Listing başlıkları
    title_prompt = (
        f'eBay\'de "{query}" için SEO optimize edilmiş 5 farklı listing başlığı yaz. '
        "Her başlık max 80 karakter olsun. Format: 1. [Başlık]"
    )
    titles = _ask_model(title_prompt)

    # 4. Tedarikçi önerileri
    supplier_prompt = (
        f'"{query}" için en iyi tedarikçi kaynakları:\n'
        "1. AliExpress'te arama terimleri (İngilizce)\n"
        "2. Amazon FBM tedarikçisi araması\n"
        "3. Wholesale/toptan kaynaklar\n"
        "4. Minimum sipariş miktarı önerileri\n"
        "Kısa ve pratik yaz."
    )
    suppliers = _ask_model(supplier_prompt)

    return {
        "query": query,
        "price_data": price_data,
        "market_analysis": market_analysis,
        "listing_titles": titles,
        "suppliers": suppliers,
    }


def format_report(result: dict) -> str:
    """Analizi Telegram formatında döndür."""
    pd = result.get("price_data", {})
    if "error" not in pd:
        price_line = (
            f"Gercek Satis: ${pd['min_price']} - ${pd['max_price']} "
            f"(ort. ${pd['avg_price']}, {pd['count']} islem)\n"
        )
    else:
        price_line = f"Fiyat verisi: {pd.get('error', 'N/A')}\n"

    return (
        f"*eBay Urun Analizi: {result['query']}*\n"
        f"{'=' * 32}\n\n"
        f"*CANLI FIYAT VERISI*\n{price_line}\n"
        f"*PAZAR ANALIZI*\n{result['market_analysis']}\n\n"
        f"{'=' * 32}\n"
        f"*LISTING BASLIKLARI*\n{result['listing_titles']}\n\n"
        f"{'=' * 32}\n"
        f"*TEDARIKCI KAYNAKLARI*\n{result['suppliers']}\n\n"
        f"Hizli test: AliExpress'ten 1 adet siparis et, eBay'e al, sat."
    )


def quick_opportunity_scan() -> str:
    """Hızlı fırsat taraması — 5 trend ürün."""
    prompt = (
        "Su an eBay'de trend olan, az rekabetli ve yuksek kar marjli 5 urun kategori oner. "
        "Her biri icin: urun adi, tahmini kar marji %, neden su an firsat. "
        "Bir paragraf maks, sadece liste. Turkce."
    )
    return _ask_model(prompt)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(f"\nAnaliz: {q}...\n")
        r = analyze_product(q)
        print(format_report(r))
    else:
        print("Hizli Firsat Taramasi:\n")
        print(quick_opportunity_scan())
