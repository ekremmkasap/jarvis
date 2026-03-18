import json
import urllib.request
import urllib.error

N8N_HOST = "http://192.168.1.109:5678"

def trigger_n8n_webhook(webhook_endpoint: str, payload: dict) -> str:
    """
    Belirli bir n8n webhook adresini tetikler (POST gönderir) ve sonucu döndürür.
    Örn webhook_endpoint: webhook/jarvis-search
    """
    url = f"{N8N_HOST}/{webhook_endpoint.lstrip('/')}"
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json", "User-Agent": "Jarvis-Core/1.0"}, 
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            if response.status == 200:
                raw_data = response.read().decode("utf-8", errors="ignore")
                try:
                    js = json.loads(raw_data)
                    return json.dumps(js, ensure_ascii=False, indent=2)
                except:
                    return raw_data
            else:
                return f"❌ n8n hata döndü: HTTP {response.status}"
    except urllib.error.URLError as e:
         return f"❌ n8n erişilemiyor. Lütfen Pinokio n8n sunucusunun {N8N_HOST} adresinde açık olduğundan emin ol! Detay: {e}"
    except Exception as e:
        return f"❌ Beklenmeyen hata: {str(e)}"

def web_search(query: str) -> str:
    """
    n8n'e bağlı 'jarvis-web-search' webhook'unu kullanarak canlı internet araması yapar.
    """
    return trigger_n8n_webhook("webhook/jarvis-web-search", {"query": query})

def scrape_url(url: str) -> str:
    """
    n8n'e bağlı 'jarvis-scrape' webhook'unu kullanarak web sitesindeki metni çeker.
    """
    return trigger_n8n_webhook("webhook/jarvis-scrape", {"url": url})

def trendyol_search(query: str) -> str:
    """
    n8n'e bağlı 'jarvis-trendyol' webhook'unu kullanarak Trendyol ürün fiyatlarını çeker.
    """
    return trigger_n8n_webhook("webhook/jarvis-trendyol", {"query": query})

def tiktok_trends(topic: str) -> str:
    """
    n8n'e bağlı 'jarvis-tiktok' webhook'unu kullanarak TikTok trend verilerini çeker.
    """
    return trigger_n8n_webhook("webhook/jarvis-tiktok", {"topic": topic})
