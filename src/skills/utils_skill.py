"""
Jarvis Utility Tools — Gerçek zamanlı araçlar
Hava, haberler, altın/döviz, hesap makinesi
Hiçbiri API key gerektirmez.
"""
import json, math, re
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote

HEADERS = {"User-Agent": "Mozilla/5.0 Chrome/121 Safari/537.36", "Accept": "application/json"}

def _get(url: str, timeout: int = 10) -> dict | list | None:
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"error": str(e)}

# ─── HAVA DURUMU ─────────────────────────────────────────────────────────────
def get_weather(city: str = "Istanbul") -> str:
    """Open-Meteo + geocoding — tamamen ücretsiz"""
    geo = _get(f"https://geocoding-api.open-meteo.com/v1/search?name={quote(city)}&count=1&language=tr")
    if not geo or "results" not in geo:
        return f"❌ '{city}' şehri bulunamadı."
    r = geo["results"][0]
    lat, lon, name = r["latitude"], r["longitude"], r.get("name", city)
    
    weather = _get(
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,wind_speed_10m,weather_code,relative_humidity_2m"
        f"&timezone=auto"
    )
    if not weather or "current" not in weather:
        return "❌ Hava verisi alınamadı."
    
    c = weather["current"]
    temp = c.get("temperature_2m", "?")
    wind = c.get("wind_speed_10m", "?")
    humidity = c.get("relative_humidity_2m", "?")
    code = c.get("weather_code", 0)
    
    # WMO weather code → emoji
    emoji = "☀️"
    if code in range(1, 4): emoji = "🌤️"
    elif code in range(45, 68): emoji = "🌫️"
    elif code in range(51, 68): emoji = "🌧️"
    elif code in range(71, 78): emoji = "❄️"
    elif code in range(80, 100): emoji = "⛈️"
    
    return (
        f"{emoji} **{name} Hava Durumu**\n"
        f"🌡️ Sıcaklık: {temp}°C\n"
        f"💨 Rüzgar: {wind} km/s\n"
        f"💧 Nem: {humidity}%"
    )

# ─── HABERLER ─────────────────────────────────────────────────────────────────
def get_news(topic: str = "türkiye", count: int = 5) -> str:
    """DuckDuckGo News (API key gerektirmez)"""
    try:
        url = f"https://api.duckduckgo.com/?q={quote(topic)}&format=json&t=jarvis"
        data = _get(url)
        
        # DuckDuckGo abstract
        lines = [f"📰 **{topic.title()} Haberleri**\n"]
        
        if data and data.get("Abstract"):
            lines.append(f"📌 {data['Abstract'][:300]}")
            if data.get("AbstractURL"):
                lines.append(f"🔗 {data['AbstractURL']}")
        
        if data and data.get("RelatedTopics"):
            for item in data["RelatedTopics"][:count]:
                if isinstance(item, dict) and item.get("Text"):
                    lines.append(f"• {item['Text'][:120]}")
        
        if len(lines) == 1:
            # Fallback: RSS haberleri
            return get_rss_news(topic)
        
        return "\n".join(lines)
    except Exception as e:
        return get_rss_news(topic)

def get_rss_news(topic: str = "ekonomi") -> str:
    """Hürriyet/NTV RSS feed"""
    feeds = {
        "ekonomi": "https://www.ntv.com.tr/ekonomi.rss",
        "türkiye": "https://www.ntv.com.tr/turkiye.rss",
        "teknoloji": "https://www.ntv.com.tr/teknoloji.rss",
        "default": "https://www.ntv.com.tr/son-dakika.rss"
    }
    feed_url = feeds.get(topic.lower(), feeds["default"])
    try:
        req = Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=10) as r:
            content = r.read().decode("utf-8", errors="ignore")
        
        # Parse RSS basitçe
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", content)
        links = re.findall(r"<link>(http.*?)</link>", content)
        
        lines = [f"📰 **Son Haberler — {topic.title()}**\n"]
        for i, title in enumerate(titles[1:6]):  # İlk title site adı
            lines.append(f"{i+1}. {title}")
        
        return "\n".join(lines) if len(lines) > 1 else "❌ Haber alınamadı."
    except Exception as e:
        return f"❌ Haber hatası: {e}"

# ─── ALTIN & DÖVİZ ──────────────────────────────────────────────────────────
def get_gold_price() -> str:
    """Gold-API.io — ücretsiz plan, API key gerekmez bazı endpointler"""
    try:
        # Open Exchange Rates ile dolar kuru
        usd = _get("https://api.exchangerate-api.com/v4/latest/USD")
        if usd and "rates" in usd:
            try_rate = usd["rates"].get("TRY", 0)
            eur_rate = usd["rates"].get("EUR", 0)
            gbp_rate = usd["rates"].get("GBP", 0)
            
            # Altın fiyatı (troy ons = ~31.1 gram)
            # Metal Prices API (ücretsiz)
            gold_data = _get("https://api.metals.live/v1/spot/gold")
            
            lines = ["💰 **Döviz Kurları**\n"]
            lines.append(f"💵 Dolar: {try_rate:.2f} ₺")
            lines.append(f"💶 Euro: {(try_rate/eur_rate if eur_rate else 0):.2f} ₺")
            lines.append(f"💷 Sterlin: {(try_rate/gbp_rate if gbp_rate else 0):.2f} ₺")
            
            if gold_data and isinstance(gold_data, list) and gold_data:
                gold_usd = gold_data[0].get("price", 0)
                # Gram altın = troy ons / 31.1
                gram_usd = gold_usd / 31.1
                gram_try = gram_usd * try_rate
                lines.append(f"\n🥇 **Altın Fiyatı**")
                lines.append(f"Ons: ${gold_usd:.2f}")
                lines.append(f"Gram: {gram_try:.2f} ₺")
            
            return "\n".join(lines)
    except Exception as e:
        pass
    
    # Basit fallback
    try:
        data = _get("https://api.exchangerate-api.com/v4/latest/USD")
        if data and "rates" in data:
            r = data["rates"]
            return (
                f"💰 **Döviz Kurları**\n"
                f"💵 USD/TRY: {r.get('TRY', '?'):.2f} ₺\n"
                f"💶 EUR/TRY: {(r.get('TRY', 0)/r.get('EUR', 1)):.2f} ₺"
            )
    except:
        return "❌ Kur verisi alınamadı."

def get_currency(amount: float, from_cur: str = "USD", to_cur: str = "TRY") -> str:
    """Döviz çevirici"""
    try:
        data = _get(f"https://api.exchangerate-api.com/v4/latest/{from_cur.upper()}")
        if data and "rates" in data:
            rate = data["rates"].get(to_cur.upper())
            if rate:
                result = amount * rate
                return f"💱 {amount} {from_cur.upper()} = **{result:.2f} {to_cur.upper()}**"
        return "❌ Döviz çevrilemedi."
    except Exception as e:
        return f"❌ Hata: {e}"

# ─── HESAP MAKİNESİ ──────────────────────────────────────────────────────────
def calculate(expression: str) -> str:
    """Güvenli matematik hesaplayıcı"""
    try:
        # İzin verilen fonksiyonlar
        safe = {
            "sqrt": math.sqrt, "pow": math.pow, "abs": abs,
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10,
            "pi": math.pi, "e": math.e,
            "round": round, "int": int, "float": float,
        }
        # Türkçe operatörler
        expr = expression.replace("^", "**").replace(",", ".")
        result = eval(expr, {"__builtins__": {}}, safe)
        return f"🧮 {expression} = **{result}**"
    except Exception as e:
        return f"❌ Hesaplama hatası: {e}"

# ─── TEST ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(get_weather("Istanbul"))
    print()
    print(get_gold_price())
    print()
    print(calculate("sqrt(144) + 2^10"))
    print()
    print(get_currency(100, "USD", "TRY"))
