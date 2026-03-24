"""
Jarvis ReAct Agent Loop v1.0
Düşün → Araç Çağır → Sonucu Gör → Tekrar Düşün → Bitti

Gerçek otonom ajan: konuşmaz, iş yapar.
"""
import json
import logging
import os
import re
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

log = logging.getLogger("jarvis.agent")

OLLAMA_URL  = "http://127.0.0.1:11434/api/chat"
AGENT_MODEL = "qwen3:8b"           # hızlı + araç kullanımında iyi
MAX_STEPS   = 8                     # sonsuz döngü koruması
STEP_TIMEOUT = 90                   # saniye (LLM başına)

# Güvenli izin verilen dizinler
SAFE_DIRS = [
    "C:/Users/sergen/Desktop",
    "C:/Users/sergen/Documents",
    "C:/Users/sergen/Downloads",
]

FORBIDDEN_PATTERNS = [
    "rm -rf /", "format c:", "del /f /s /q c:\\",
    "drop database", "shutdown /s", ":(){:|:&};:",
]

# ─────────────────────────── TOOLS ────────────────────────────────

def tool_shell(cmd: str) -> str:
    """Güvenli shell komutu çalıştır."""
    cmd_lower = cmd.lower()
    for pat in FORBIDDEN_PATTERNS:
        if pat in cmd_lower:
            return f"HATA: Yasak komut engellendi: '{pat}'"
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=20, encoding="utf-8", errors="replace"
        )
        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        if result.returncode != 0 and err:
            return f"[exit {result.returncode}] {err[:600]}"
        return out[:1000] or "(çıktı yok)"
    except subprocess.TimeoutExpired:
        return "HATA: Komut zaman aşımına uğradı (20s)"
    except Exception as e:
        return f"HATA: {e}"


def tool_write_file(path: str, content: str) -> str:
    """Dosyaya yaz."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"OK: {path} dosyasına {len(content)} karakter yazıldı."
    except Exception as e:
        return f"HATA: {e}"


def tool_read_file(path: str) -> str:
    """Dosya oku."""
    try:
        p = Path(path)
        if not p.exists():
            return f"HATA: Dosya bulunamadı: {path}"
        content = p.read_text(encoding="utf-8", errors="replace")
        if len(content) > 2000:
            return content[:2000] + f"\n... (toplam {len(content)} karakter, ilk 2000 gösterildi)"
        return content or "(boş dosya)"
    except Exception as e:
        return f"HATA: {e}"


def tool_list_dir(path: str) -> str:
    """Dizin içeriğini listele."""
    try:
        p = Path(path)
        if not p.exists():
            return f"HATA: Dizin bulunamadı: {path}"
        items = []
        for item in sorted(p.iterdir()):
            tag = "[D]" if item.is_dir() else "[F]"
            items.append(f"{tag} {item.name}")
        return "\n".join(items[:50]) or "(boş dizin)"
    except Exception as e:
        return f"HATA: {e}"


def tool_web_search(query: str) -> str:
    """DuckDuckGo instant answer API ile arama."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.request.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Jarvis/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        abstract = data.get("AbstractText", "").strip()
        if abstract:
            return abstract[:800]
        related = [r.get("Text", "") for r in data.get("RelatedTopics", [])[:3] if r.get("Text")]
        if related:
            return "\n".join(related)
        return "Sonuç bulunamadı. Farklı arama terimi dene."
    except Exception as e:
        return f"HATA: Web arama başarısız: {e}"


def tool_pc_control(action: str, args: str = "") -> str:
    """Mouse/klavye kontrolü (pyautogui)."""
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        a = action.lower()
        if a == "screenshot":
            path = f"C:/Users/sergen/Desktop/screenshot_{int(time.time())}.png"
            pyautogui.screenshot(path)
            return f"OK: Ekran görüntüsü alındı: {path}"
        elif a == "click":
            parts = args.split()
            x, y = int(parts[0]), int(parts[1])
            pyautogui.click(x, y)
            return f"OK: Tıklandı ({x}, {y})"
        elif a == "write":
            pyautogui.write(args, interval=0.05)
            return f"OK: Yazıldı: {args[:50]}"
        elif a == "hotkey":
            keys = args.split("+")
            pyautogui.hotkey(*keys)
            return f"OK: Kısayol: {args}"
        elif a == "move":
            parts = args.split()
            x, y = int(parts[0]), int(parts[1])
            pyautogui.moveTo(x, y)
            return f"OK: Mouse ({x}, {y}) konumuna taşındı"
        else:
            return f"HATA: Bilinmeyen eylem: {action}"
    except Exception as e:
        return f"HATA: {e}"


# ─────────────────────────── TOOL REGISTRY ───────────────────────

TOOLS = {
    "shell": {
        "fn": tool_shell,
        "desc": "Shell/terminal komutu çalıştır. Parametre: komut string'i.",
        "example": 'shell | dir C:/Users/sergen/Desktop'
    },
    "write_file": {
        "fn": tool_write_file,
        "desc": "Dosyaya içerik yaz. Parametre: yol::içerik (:: ile ayır).",
        "example": 'write_file | C:/Users/sergen/Desktop/not.txt::Merhaba dünya'
    },
    "read_file": {
        "fn": tool_read_file,
        "desc": "Dosya içeriğini oku. Parametre: dosya yolu.",
        "example": 'read_file | C:/Users/sergen/Desktop/not.txt'
    },
    "list_dir": {
        "fn": tool_list_dir,
        "desc": "Dizin içeriğini listele. Parametre: dizin yolu.",
        "example": 'list_dir | C:/Users/sergen/Desktop'
    },
    "web_search": {
        "fn": tool_web_search,
        "desc": "Web'de ara. Parametre: arama sorgusu.",
        "example": 'web_search | Python asyncio nedir'
    },
    "pc_control": {
        "fn": tool_pc_control,
        "desc": "Fare/klavye kontrolü. Parametre: eylem::args (screenshot, click, write, hotkey, move).",
        "example": 'pc_control | screenshot'
    },
}

TOOLS_DESC = "\n".join(
    f"- {name}: {t['desc']}\n  Örnek: {t['example']}"
    for name, t in TOOLS.items()
)

# ─────────────────────────── LLM CALL ────────────────────────────

def _call_llm(messages: list) -> str:
    payload = json.dumps({
        "model": AGENT_MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.2, "num_predict": 600}
    }).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=STEP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"LLM hatası: {e}")


# ─────────────────────────── PARSER ──────────────────────────────

def _parse_action(text: str):
    """
    LLM çıktısını ayrıştır — ARAÇ öncelikli.
    Döner: ("action", tool_name, param) veya ("done", None, answer)
    """
    # Sadece İLK bloğu al (model birden fazla adım yazarsa ilkini al)
    first_block = text.split("\n\n")[0] if "\n\n" in text else text

    # ARAÇ / ACTION — her zaman önce kontrol et
    for pat in [r"(?i)^ARAÇ:\s*(\w+)\s*\|\s*(.+)", r"(?i)^ACTION:\s*(\w+)\s*\|\s*(.+)"]:
        m = re.search(pat, first_block, re.MULTILINE)
        if m:
            return ("action", m.group(1).strip().lower(), m.group(2).strip())

    # Tüm metinde ARAÇ ara (model tek blok yazmışsa)
    for pat in [r"(?i)^ARAÇ:\s*(\w+)\s*\|\s*(.+)", r"(?i)^ACTION:\s*(\w+)\s*\|\s*(.+)"]:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            return ("action", m.group(1).strip().lower(), m.group(2).strip())

    # Araç adı fallback
    for tool_name in TOOLS:
        if tool_name in text.lower():
            after = re.search(rf"{tool_name}\s*[\|:]\s*(.+)", text, re.IGNORECASE)
            if after:
                return ("action", tool_name, after.group(1).strip())

    # CEVAP / DONE — son kontrol
    for pat in [r"(?i)^CEVAP:\s*(.+)", r"(?i)^DONE:\s*(.+)", r"(?i)^SONUÇ:\s*(.+)"]:
        m = re.search(pat, text, re.MULTILINE | re.DOTALL)
        if m:
            return ("done", None, m.group(1).strip())

    return ("done", None, text)


# ─────────────────────────── REACT LOOP ──────────────────────────

_TOOL_LIST = "\n".join(f"- {n}: {t['desc']}" for n, t in TOOLS.items())

SYSTEM_PROMPT = f"""/no_think
Sen Jarvis, otonom ajan. Araçlarla iş yaparsın.

ARAÇLAR:
{_TOOL_LIST}

FORMAT (her adımda):
DÜŞÜNCE: ne yapacağını yaz
ARAÇ: araç_adı | parametre

Bitti ise:
DÜŞÜNCE: açıkla
CEVAP: kullanıcıya son mesaj

Kural: tek araç, Türkçe, maks {MAX_STEPS} adım."""


def run(goal: str, chat_id: str = "0") -> str:
    """
    Ana giriş noktası. Hedefi al, ReAct döngüsünü çalıştır, cevap dön.
    """
    log.info(f"[Agent] Hedef: {goal[:80]}")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Hedef: {goal}"}
    ]

    steps_log = []

    for step in range(1, MAX_STEPS + 1):
        log.info(f"[Agent] Adım {step}/{MAX_STEPS}")

        try:
            llm_output = _call_llm(messages)
            log.info(f"[Agent] LLM raw:\n{llm_output[:300]}")
        except RuntimeError as e:
            return f"❌ Agent LLM hatası: {e}"

        log.debug(f"[Agent] LLM çıktı:\n{llm_output}")

        kind, tool_name, param = _parse_action(llm_output)

        if kind == "done":
            log.info(f"[Agent] Tamamlandı {step} adımda.")
            summary = ""
            if steps_log:
                summary = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps_log))
                return f"✅ *Görev tamamlandı* ({step} adım)\n\n{param}\n\n_Adımlar:_\n{summary}"
            return f"✅ {param}"

        # Araç çağrısı
        tool = TOOLS.get(tool_name)
        if not tool:
            observation = f"HATA: '{tool_name}' adında araç yok. Mevcut araçlar: {', '.join(TOOLS)}"
            log.warning(f"[Agent] Bilinmeyen araç: {tool_name}")
        else:
            log.info(f"[Agent] Araç: {tool_name} | {param[:60]}")
            # write_file için :: ayıracını işle
            if tool_name == "write_file" and "::" in param:
                parts = param.split("::", 1)
                observation = tool["fn"](parts[0].strip(), parts[1].strip())
            elif tool_name == "pc_control" and "::" in param:
                parts = param.split("::", 1)
                observation = tool["fn"](parts[0].strip(), parts[1].strip())
            else:
                observation = tool["fn"](param)
            steps_log.append(f"{tool_name}({param[:40]}) → {observation[:60]}")

        log.info(f"[Agent] Gözlem: {observation[:100]}")

        # Sadece bu adımın ARAÇ satırını tut (geçmiş şişmesin)
        # İlk ARAÇ satırını bul
        action_line = ""
        for line in llm_output.splitlines():
            if re.match(r"(?i)^araç:", line) or re.match(r"(?i)^action:", line):
                action_line = line.strip()
                break

        messages.append({
            "role": "assistant",
            "content": action_line or llm_output[:200]
        })
        messages.append({
            "role": "user",
            "content": (
                f"Sonuç: {observation[:500]}\n\n"
                f"Hedef: {goal}\n"
                f"Henüz tamamlanmadıysa sıradaki ARAÇ: satırını yaz. "
                f"Tamamlandıysa CEVAP: yaz."
            )
        })

    # Max adım aşıldı
    return f"⚠️ Görev {MAX_STEPS} adımda tamamlanamadı.\n\nSon adımlar:\n" + \
           "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps_log))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_goal = "Masaüstünde test.txt dosyası oluştur ve içine 'Jarvis ReAct çalışıyor' yaz, sonra dosyayı oku ve içeriği doğrula."
    print(f"\nHedef: {test_goal}\n")
    result = run(test_goal)
    print(f"\nSonuç:\n{result}")
