import urllib.request
import urllib.parse
import json

TOKEN = "8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k"
URL = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"

commands = {
    "commands": [
        {"command": "status", "description": "Sistem durumunu göster"},
        {"command": "models", "description": "Aktif AI modellerini listele"},
        {"command": "reset", "description": "Konuşma geçmişini sil"},
        {"command": "ebay", "description": "eBay ürün/pazar analizi yap"},
        {"command": "hava", "description": "Hava durumu (örn: /hava Izmir)"},
        {"command": "haber", "description": "Son dakika haberleri (örn: /haber eknomi)"},
        {"command": "altin", "description": "Güncel altın fiyatları"},
        {"command": "kur", "description": "Döviz çevirici (örn: /kur 100 USD)"},
        {"command": "hesap", "description": "Hesap makinesi (örn: /hesap 2+2)"},
        {"command": "printify", "description": "Printify POD analizi"},
        {"command": "trendyol", "description": "Trendyol ürün analizi"},
        {"command": "code", "description": "AI'a kod yazdır"},
        {"command": "plan", "description": "AI'a proje planı oluştur"},
        {"command": "n8n_web", "description": "n8n üzerinden internet araştırması"},
        {"command": "hafiza", "description": "Hafıza raporunu göster"},
        {"command": "gorev", "description": "Görev listesini göster"}
    ]
}

data = json.dumps(commands).encode('utf-8')
req = urllib.request.Request(URL, data=data, headers={'Content-Type': 'application/json'}, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print("Telegram Menu Setup Response:", response.read().decode('utf-8'))
except Exception as e:
    print("Error setting menu:", e)
