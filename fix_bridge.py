"""
Fix bridge.py: news command + model routing
deepseek-r1:8b for reasoning, qwen2.5-coder for code, etc.
"""
import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)
sftp = client.open_sftp()

# Read bridge.py
with sftp.file('/opt/jarvis/openclaw/bridge.py', 'r') as f:
    content = f.read().decode()

# ── FIX 1: Default model → deepseek-r1:8b (once downloaded)
# Use model fallback: try best model, fallback to llama3.2
OLD_MODEL = '"model": "llama3.2:latest"'
if OLD_MODEL in content:
    NEW_MODEL = '''def _get_best_model(task_type="general"):
    """Görev türüne göre en iyi modeli seç"""
    import urllib.request as ur, json
    try:
        with ur.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            models = [m["name"] for m in json.loads(r.read())["models"]]
    except:
        return "llama3.2:latest"
    
    preferences = {
        "code":    ["qwen2.5-coder:7b", "deepseek-coder:latest", "qwen2.5-coder:3b", "llama3.2:latest"],
        "reason":  ["deepseek-r1:8b", "llama3.1:latest", "mistral:latest", "llama3.2:latest"],
        "vision":  ["llava:7b", "moondream:latest", "llama3.2:latest"],
        "embed":   ["nomic-embed-text:latest", "llama3.2:latest"],
        "general": ["mistral:latest", "llama3.1:latest", "llama3.2:latest"],
    }
    for candidate in preferences.get(task_type, preferences["general"]):
        if any(candidate in m for m in models):
            return candidate
    return "llama3.2:latest"

'''
    # Insert before first use of model
    content = content.replace(
        '"model": "llama3.2:latest"',
        '"model": _get_best_model("general")',
        1  # Only first occurrence (main query)
    )
    # Insert function near top (after imports)
    import_end = content.find('\nclass ')
    if import_end > 0:
        content = content[:import_end] + '\n' + NEW_MODEL + content[import_end:]
    print("✅ Model routing added")

# ── FIX 2: /code command → use coder model
OLD_CODE = '"model": _get_best_model("general")'  
if content.count('"model": _get_best_model("general")') > 0:
    # Replace model in code command specifically
    pass

# Fix code command to use coder model
if 'command == "/code"' in content:
    OLD_CODE_CMD = '''    elif command == "/code":'''
    if OLD_CODE_CMD in content:
        # Find the ollama call in code command and replace model
        code_section_start = content.find(OLD_CODE_CMD)
        code_section_end = content.find('\n    elif', code_section_start + 1)
        code_section = content[code_section_start:code_section_end]
        
        if '"model": _get_best_model("general")' in code_section:
            new_code_section = code_section.replace(
                '"model": _get_best_model("general")',
                '"model": _get_best_model("code")'
            )
            content = content[:code_section_start] + new_code_section + content[code_section_end:]
            print("✅ /code → coder model")

# ── FIX 3: /haber → better news fetching on server
OLD_HABER = '''    elif command == "/haber":
        topic = args or "turkiye"
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from utils_skill import get_rss_news
            return get_rss_news(topic)
        except Exception as e:
            return f"Haber hatası: {e}"'''

NEW_HABER = '''    elif command == "/haber":
        topic = args or "turkiye"
        import urllib.request as ur, re
        feeds = {
            "ekonomi": "https://www.ntv.com.tr/ekonomi.rss",
            "turkiye": "https://www.ntv.com.tr/turkiye.rss",
            "teknoloji": "https://www.ntv.com.tr/teknoloji.rss",
            "spor": "https://www.ntv.com.tr/spor.rss",
        }
        feed_url = feeds.get(topic.lower(), "https://www.ntv.com.tr/son-dakika.rss")
        try:
            req = ur.Request(feed_url, headers={"User-Agent": "Mozilla/5.0"})
            with ur.urlopen(req, timeout=12) as r:
                raw = r.read().decode("utf-8", errors="ignore")
            titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", raw)
            if not titles:
                titles = re.findall(r"<title>(.*?)</title>", raw)
            lines = [f"📰 **Son Haberler — {topic.upper()}**\\n"]
            for i, t in enumerate(titles[1:6]):
                lines.append(f"{i+1}. {t.strip()}")
            return "\\n".join(lines) if len(lines) > 1 else "❌ Haber bulunamadı."
        except Exception as e:
            return f"❌ Haber hatası: {e}"'''

if OLD_HABER in content:
    content = content.replace(OLD_HABER, NEW_HABER)
    print("✅ /haber fixed")
else:
    print("⚠️ /haber not found to fix")

# Write back
with sftp.file('/opt/jarvis/openclaw/bridge.py', 'w') as f:
    f.write(content)
sftp.close()

# Syntax + restart
_, so, _ = client.exec_command('python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo SYNTAX_OK')
result = so.read().decode().strip()
print(f"Syntax: {result}")
if 'OK' in result:
    client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
    time.sleep(3)
    _, ss, _ = client.exec_command('systemctl is-active jarvis.service')
    print(f"Service: {ss.read().decode().strip()}")

# Check download progress
print("\n[Model indirme durumu]:")
_, log, _ = client.exec_command('tail -5 /tmp/ollama_pull.log 2>&1')
print(log.read().decode())

client.close()
print("\nDone!")
