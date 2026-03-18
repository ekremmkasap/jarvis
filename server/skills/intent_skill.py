"""
Jarvis Intent Classification System
Komut olmadan da ne istediğini anlar.
'Hava nasıl istanbul?' → /hava Istanbul
'Bugün ne var?' → /gorev
'100 dolar kaç lira?' → /kur 100 USD TRY
"""
import re

# ─── INTENT PATTERNS ─────────────────────────────────────────────────────────
INTENTS = [
    # Hava durumu
    {
        "intent": "hava",
        "patterns": [
            r"hava\s*(nasıl|durumu|kaç derece|ne kadar soğuk|ne kadar sıcak)",
            r"(bugün|yarın|şu an)\s*hava",
            r"yağmur\s*(yağacak|var mı)",
            r"dışarısı\s*(nasıl|soğuk|sıcak)",
        ],
        "city_extract": True,
    },
    # Döviz / Altın
    {
        "intent": "altin",
        "patterns": [
            r"(dolar|euro|döviz|kur|sterlin|pound)\s*(kaç|ne kadar|fiyat)",
            r"(altın|gram altın|cumhuriyet altını)\s*(kaç|fiyat|ne kadar)",
            r"1\s*(dolar|euro|usd|eur)\s*(kaç|=)\s*(lira|tl|try)",
            r"döviz\s*(kuru|fiyat)",
        ],
        "convert_extract": True,
    },
    # Hesap makinesi
    {
        "intent": "hesap",
        "patterns": [
            r"\d+\s*[\+\-\*\/\^]\s*\d+",
            r"(hesapla|kaç eder|ne kadar eder)\s*[\d\s\+\-\*\/]+",
            r"sqrt\s*\(",
            r"\d+\s*kareköküD",
        ],
    },
    # Haberler
    {
        "intent": "haber",
        "patterns": [
            r"(son dakika|gündem|haberler|ne oldu|ne var)\s*(haberleri?|gündem)?",
            r"(ekonomi|spor|teknoloji|türkiye|dünya)\s*haberleri?",
            r"bugün\s*(ne\s*oldu|neler\s*var)",
        ],
        "topic_extract": True,
    },
    # Görevler
    {
        "intent": "gorev",
        "patterns": [
            r"(görevlerim|yapılacaklar|to[- ]do|ne\s*yapmalıyım)",
            r"(bugün|bu\s*hafta)\s*ne\s*(yapacak|yapmam\s*gerek)",
            r"(görev\s*listesi|iş\s*listesi)",
        ],
    },
    # Hafıza raporu
    {
        "intent": "hafiza",
        "patterns": [
            r"(beni\s*hatırlıyor\s*musun|hatıran\s*var\s*mı|ne\s*biliyorsun\s*benim\s*hakkımda)",
            r"(hafıza\s*raporu|ne\s*öğrendin)",
            r"benim\s*(hakkımda|adım|ismim)",
        ],
    },
    # eBay araştırma
    {
        "intent": "ebay",
        "patterns": [
            r"(ebay'd[ae]|ebay\s*için|ebay\s*satış)\s*(sata[b]?ilir\s*miyim|araştır|analiz|ne\s*kadar)",
            r"(ürün\s*araştır|hangi\s*ürün|ne\s*satalım)",
        ],
        "product_extract": True,
    },
    # Trendyol
    {
        "intent": "trendyol",
        "patterns": [
            r"(trendyol'?d[ae]|trendyol\s*için)\s*(araştır|analiz|satış|trend)",
            r"trendyol\s*(fiyat|pazar|kategori|trend)",
        ],
        "product_extract": True,
    },
]

# ─── EXTRACT HELPERS ─────────────────────────────────────────────────────────
CITIES = ["istanbul", "ankara", "izmir", "bursa", "antalya", "adana", "konya",
          "gaziantep", "mersin", "diyarbakır", "kayseri", "eskişehir", "trabzon"]

TOPICS = ["ekonomi", "spor", "teknoloji", "türkiye", "dünya", "siyaset",
          "finans", "borsa", "kripto"]

def _extract_city(text: str) -> str:
    low = text.lower()
    for city in CITIES:
        if city in low:
            return city.capitalize()
    return "Istanbul"

def _extract_topic(text: str) -> str:
    low = text.lower()
    for topic in TOPICS:
        if topic in low:
            return topic
    return "turkiye"

def _extract_product(text: str) -> str:
    # Remove common words, return remainder
    remove = ["ebay", "trendyol", "araştır", "analiz", "için", "satış", "ne", "kadar", "satalım", "satalım"]
    words = text.lower().split()
    remaining = [w for w in words if w not in remove]
    return " ".join(remaining[:3]) if remaining else "genel"

def _extract_convert(text: str) -> tuple:
    """'100 dolar' → (100, USD, TRY)"""
    amount_match = re.search(r"(\d+[\.,]?\d*)", text)
    amount = float(amount_match.group(1).replace(",", ".")) if amount_match else 1.0
    
    cur_map = {
        "dolar": "USD", "usd": "USD", "$": "USD",
        "euro": "EUR", "eur": "EUR", "€": "EUR",
        "sterlin": "GBP", "pound": "GBP", "gbp": "GBP",
        "altın": "XAU",
    }
    from_cur = "USD"
    for word, cur in cur_map.items():
        if word in text.lower():
            from_cur = cur
            break
    return (amount, from_cur, "TRY")

# ─── MAIN CLASSIFIER ─────────────────────────────────────────────────────────
def classify_intent(text: str) -> dict | None:
    """
    Metnden niyet çıkar.
    Returns: {"intent": "hava", "command": "/hava", "args": "Istanbul"} or None
    """
    text_low = text.lower().strip()
    
    # Skip if it looks like a command already
    if text_low.startswith("/"):
        return None
    
    # Skip very short messages
    if len(text_low) < 4:
        return None
    
    for intent_def in INTENTS:
        for pattern in intent_def["patterns"]:
            if re.search(pattern, text_low, re.IGNORECASE):
                intent = intent_def["intent"]
                args = ""
                
                if intent == "hava" and intent_def.get("city_extract"):
                    args = _extract_city(text_low)
                elif intent == "altin" and intent_def.get("convert_extract"):
                    amount, from_cur, to_cur = _extract_convert(text_low)
                    # If asking for altın specifically
                    if "altın" in text_low:
                        return {"intent": "altin", "command": "/altin", "args": ""}
                    args = f"{amount} {from_cur} {to_cur}"
                    return {"intent": "kur", "command": "/kur", "args": args}
                elif intent == "haber" and intent_def.get("topic_extract"):
                    args = _extract_topic(text_low)
                elif intent in ("ebay", "trendyol") and intent_def.get("product_extract"):
                    args = _extract_product(text_low)
                
                return {
                    "intent": intent,
                    "command": f"/{intent}",
                    "args": args,
                }
    
    return None  # No intent matched → normal AI response


def handle_with_intent(text: str, user_id: str = None) -> str | None:
    """
    Eğer bir niyet varsa ilgili handler'a yönlendir.
    Returns: response string if intent found, None if should go to AI
    """
    result = classify_intent(text)
    if not result:
        return None
    
    cmd = result["command"]
    args = result["args"]
    
    # Import and call the relevant skill
    import sys
    sys.path.insert(0, "/opt/jarvis/skills")
    
    try:
        if cmd == "/hava":
            from utils_skill import get_weather
            return get_weather(args or "Istanbul")
        elif cmd in ("/altin", "/kur"):
            if cmd == "/altin":
                from utils_skill import get_gold_price
                return get_gold_price()
            else:
                from utils_skill import get_currency
                parts = args.split()
                if len(parts) == 3:
                    return get_currency(float(parts[0]), parts[1], parts[2])
                return get_currency(1, "USD", "TRY")
        elif cmd == "/haber":
            from utils_skill import get_rss_news
            return get_rss_news(args or "turkiye")
        elif cmd == "/gorev":
            from memory_skill import get_tasks
            return get_tasks(str(user_id) if user_id else "default")
        elif cmd == "/hafiza":
            from memory_skill import daily_memory_report
            return daily_memory_report(str(user_id) if user_id else "default")
    except Exception as e:
        return None  # Fall back to AI on error
    
    return None


# ─── TEST ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        "istanbul'da hava nasıl?",
        "1 dolar kaç lira?",
        "bugün ki haberler neler?",
        "görevlerimi göster",
        "100 euro kaç tl eder?",
        "yarın yağmur yağacak mı?",
        "altın ne kadar?",
        "teknoloji haberleri",
        "merhaba jarvis",  # → None
    ]
    for t in tests:
        r = classify_intent(t)
        print(f"  '{t}' → {r}")
