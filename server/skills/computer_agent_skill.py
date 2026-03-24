"""
Jarvis Computer Agent Skill
Ekranı görür → anlar → karar verir → pyautogui ile hareket eder.

Komutlar (bridge.py üzerinden):
  /yap [doğal dil]   → Ekranı analiz et + görevi otomatik yap
  /bak               → Ekran görüntüsü al + ne var açıkla
  /otonom [hedef]    → Hedefe ulaşana kadar döngüde çalış
"""

import os
import sys
import json
import base64
import tempfile
import subprocess
import urllib.request
import urllib.parse

# Python 3.11 yolu (faster-whisper + pyautogui buraya kurulu)
PYTHON311 = r"C:\Program Files\Python311\python.exe"
if not os.path.exists(PYTHON311):
    PYTHON311 = sys.executable

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
VISION_MODEL = "moondream:latest"
AGENT_MODEL = os.getenv("AGENT_MODEL", "qwen2.5-coder:7b")
SCREENSHOT_PATH = os.path.join(tempfile.gettempdir(), "jarvis_screen.png")


# ─── Ekran Görüntüsü ────────────────────────────────────────────────────────

def take_screenshot() -> str:
    """Ekran görüntüsü al, dosya yolunu döndür."""
    import pyautogui
    img = pyautogui.screenshot()
    img.save(SCREENSHOT_PATH)
    return SCREENSHOT_PATH


def screenshot_to_base64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ─── Ekran Analizi (moondream) ───────────────────────────────────────────────

def analyze_screen(question: str = "Ekranda ne var? Hangi program açık, ne yazıyor?") -> str:
    """Moondream ile ekranı analiz et."""
    try:
        path = take_screenshot()
        img_b64 = screenshot_to_base64(path)

        payload = json.dumps({
            "model": VISION_MODEL,
            "prompt": question,
            "images": [img_b64],
            "stream": False
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            return data.get("response", "Ekran analizi başarısız.")
    except Exception as e:
        return f"Ekran analiz hatası: {e}"


# ─── LLM Karar (pyautogui kodu üret) ────────────────────────────────────────

def plan_action(task: str, screen_desc: str) -> str:
    """
    LLM'e ekran durumunu + görevi ver, pyautogui kodu üretmesini iste.
    Sadece çalıştırılabilir Python kodu döner.
    """
    prompt = f"""Sen bir bilgisayar kontrol ajanısın. pyautogui kullanarak görevleri otomatik yapıyorsun.

EKRAN DURUMU:
{screen_desc}

GÖREV:
{task}

KURALLAR:
- Sadece Python kodu yaz, açıklama yazma
- import pyautogui satırını dahil et
- import time kullan gerekirse
- Güvenli ol: silme/format gibi tehlikeli işlem yapma
- Kısa ve net kod yaz

Python kodu:"""

    try:
        payload = json.dumps({
            "model": AGENT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 400}
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            code = data.get("response", "")
            # Kod bloğu varsa ayıkla
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0]
            elif "```" in code:
                code = code.split("```")[1].split("```")[0]
            return code.strip()
    except Exception as e:
        return f"# LLM plan hatası: {e}"


# ─── Kodu Güvenli Çalıştır ───────────────────────────────────────────────────

def execute_code(code: str) -> str:
    """Üretilen pyautogui kodunu çalıştır."""
    if not code or code.startswith("#"):
        return f"Çalıştırılacak kod yok: {code}"

    # Tehlikeli komutları engelle
    blocked = ["rmdir", "remove", "unlink", "format", "deltree",
               "rd /s", "del /f", "shutil.rmtree", "os.system"]
    code_lower = code.lower()
    for danger in blocked:
        if danger in code_lower:
            return f"❌ Güvenlik engeli: '{danger}' tespit edildi."

    try:
        # Geçici dosyaya yaz ve Python 3.11 ile çalıştır
        tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8")
        tmp.write(code)
        tmp.close()

        result = subprocess.run(
            [PYTHON311, tmp.name],
            capture_output=True, text=True, timeout=30
        )
        os.unlink(tmp.name)

        if result.returncode == 0:
            out = result.stdout.strip() or "Kod çalıştı."
            return f"✅ {out[:300]}"
        else:
            return f"❌ Hata: {result.stderr.strip()[:300]}"
    except subprocess.TimeoutExpired:
        return "⏱️ Zaman aşımı (30sn)."
    except Exception as e:
        return f"❌ Çalıştırma hatası: {e}"


# ─── Ana Dispatcher ──────────────────────────────────────────────────────────

def run_computer_agent(cmd: str, args: str) -> str:
    cmd = cmd.lower().strip("/")

    # /bak → sadece ekranı açıkla
    if cmd in ("bak", "ekrangoster", "screen"):
        desc = analyze_screen()
        return f"👁️ *Ekran Analizi:*\n{desc}"

    # /yap [görev] → ekranı gör + karar ver + çalıştır
    elif cmd in ("yap", "do", "execute", "calistir"):
        if not args:
            return "Kullanım: /yap [ne yapmamı istiyorsun?]"

        # 1. Ekranı analiz et
        screen_desc = analyze_screen(f"Bu ekranda '{args}' görevini yapmak için ne görüyorum?")

        # 2. Plan üret
        code = plan_action(args, screen_desc)

        # 3. Çalıştır
        result = execute_code(code)

        return (
            f"👁️ *Ekran:* {screen_desc[:150]}...\n\n"
            f"🧠 *Plan:*\n```python\n{code[:300]}\n```\n\n"
            f"⚡ *Sonuç:* {result}"
        )

    # /otonom [hedef] → döngüde çalış (max 5 adım)
    elif cmd in ("otonom", "auto", "loop"):
        if not args:
            return "Kullanım: /otonom [hedef]"
        return run_autonomous(args, max_steps=5)

    # /kodcalistir [kod] → direkt kod çalıştır
    elif cmd in ("kodcalistir", "runcode"):
        if not args:
            return "Kullanım: /kodcalistir [python kodu]"
        return execute_code(args)

    else:
        return (
            "*Computer Agent Komutları:*\n"
            "/bak → Ekranı gör + açıkla\n"
            "/yap [görev] → Görevi otomatik yap\n"
            "/otonom [hedef] → Hedefe ulaşana kadar döngü\n"
            "/kodcalistir [kod] → Python kodu çalıştır"
        )


def run_autonomous(goal: str, max_steps: int = 5) -> str:
    """Hedefe ulaşana kadar döngüde çalış."""
    log = []
    for step in range(1, max_steps + 1):
        screen_desc = analyze_screen(f"'{goal}' hedefine ulaştım mı? Ne görüyorum?")

        # Hedefe ulaşıldı mı kontrol et
        check_prompt = f"Ekran: {screen_desc}\nHedef: {goal}\nCevap sadece EVET veya HAYIR:"
        check_resp = _quick_llm(check_prompt)
        if "EVET" in check_resp.upper():
            log.append(f"✅ Adım {step}: Hedefe ulaşıldı!")
            break

        # Sonraki adımı planla ve çalıştır
        code = plan_action(f"Adım {step}: {goal}", screen_desc)
        result = execute_code(code)
        log.append(f"🔄 Adım {step}: {result[:100]}")

        if "❌" in result and step > 2:
            log.append("⛔ Hatalar devam ediyor, duruyorum.")
            break

    return "\n".join(log)


def _quick_llm(prompt: str) -> str:
    try:
        payload = json.dumps({
            "model": AGENT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 10}
        }).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read()).get("response", "")
    except Exception:
        return ""
