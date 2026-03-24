"""
Jarvis Vision Skill
Telegram'dan gelen fotoğrafı analiz eder (Ollama vision model kullanarak).

Pipeline:
  Telegram photo → download → base64 → Ollama vision → açıklama

Desteklenen Ollama Vision Modeller:
  - llava:latest (7B)
  - llava:13b
  - llava:34b
  - bakllava:latest
  - moondream:latest (1.8B, hızlı)
"""

import os
import base64
import tempfile
import urllib.request
import json


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "moondream:latest")  # En hızlı model


def get_available_vision_models() -> list:
    """Ollama'da yüklü vision modellerini listele."""
    try:
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
            all_models = [m["name"] for m in data.get("models", [])]
            # Vision modelleri filtrele
            vision_keywords = ["llava", "bakllava", "moondream", "vision"]
            return [m for m in all_models if any(kw in m.lower() for kw in vision_keywords)]
    except Exception:
        return []


def analyze_image_with_ollama(image_path: str, prompt: str = None) -> str:
    """
    Ollama vision model ile görseli analiz et.

    Args:
        image_path: Yerel görsel dosyası yolu
        prompt: Kullanıcı sorusu (varsayılan: "Bu görselde ne var? Detaylı açıkla.")

    Returns:
        Ollama'dan gelen açıklama metni
    """
    if prompt is None:
        prompt = "Bu görselde ne var? Detaylı açıkla. Türkçe cevap ver."

    # Görseli base64'e çevir
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Model seçimi (fallback sistemi)
    available = get_available_vision_models()
    model = VISION_MODEL

    if not available:
        return "❌ Hiçbir vision model yüklü değil. `ollama pull moondream` çalıştır."

    # İstenilen model yoksa ilk bulunanı kullan
    if not any(model.split(":")[0] in m for m in available):
        model = available[0]

    # Ollama API çağrısı
    payload = {
        "model": model,
        "prompt": prompt,
        "images": [image_b64],
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 512
        }
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            response_text = result.get("response", "").strip()

            if not response_text:
                return "❌ Ollama boş yanıt döndü."

            return f"🖼️ **[{model}]**\n\n{response_text}"

    except urllib.error.URLError as e:
        return f"❌ Ollama bağlantı hatası: {e}"
    except Exception as e:
        return f"❌ Vision analiz hatası: {e}"


def handle_photo_message(bot_token: str, file_id: str, caption: str = None) -> str:
    """
    Telegram'dan gelen fotoğrafı işle.

    Args:
        bot_token: Telegram bot token
        file_id: Telegram file_id
        caption: Kullanıcının mesajı (varsa)

    Returns:
        Görsel analiz sonucu (Türkçe açıklama)
    """
    try:
        # 1. Telegram'dan file_path al
        url = f"https://api.telegram.org/bot{bot_token}/getFile?file_id={file_id}"
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read())
            file_path = data["result"]["file_path"]

        # 2. Fotoğrafı indir
        download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
        temp_path = tempfile.mktemp(suffix=".jpg")
        urllib.request.urlretrieve(download_url, temp_path)

        # 3. Ollama vision model ile analiz et
        prompt = caption if caption else "Bu görselde ne var? Detaylı açıkla. Türkçe cevap ver."
        result = analyze_image_with_ollama(temp_path, prompt)

        # Temizle
        try:
            os.unlink(temp_path)
        except Exception:
            pass

        return result

    except Exception as e:
        return f"❌ Fotoğraf işleme hatası: {e}"
