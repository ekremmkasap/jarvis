"""
Deploy knowledge base and wire into bridge.py.
Bridge reads knowledge files and injects relevant context into AI prompts.
"""
import paramiko, time, os

host, username, password = "192.168.1.109", "userk", "userk1"

knowledge_files = [
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\knowledge\profil.md",
     "/opt/jarvis/knowledge/profil.md"),
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\knowledge\ebay_strateji.md",
     "/opt/jarvis/knowledge/ebay_strateji.md"),
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\knowledge\trendyol_strateji.md",
     "/opt/jarvis/knowledge/trendyol_strateji.md"),
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\knowledge\jarvis_komutlar.md",
     "/opt/jarvis/knowledge/jarvis_komutlar.md"),
]

# Knowledge loader + injector code to add to bridge.py
KNOWLEDGE_CODE = '''
# ─── KNOWLEDGE BASE (Eğitim Dosyaları) ────────────────────────────────────────
import glob as _glob

KNOWLEDGE_DIR = "/opt/jarvis/knowledge"
KNOWLEDGE = {}

def _load_knowledge():
    global KNOWLEDGE
    try:
        files = _glob.glob(f"{KNOWLEDGE_DIR}/*.md")
        for fp in files:
            name = fp.split("/")[-1].replace(".md", "")
            with open(fp, "r") as f:
                KNOWLEDGE[name] = f.read()
        log.info(f"Bilgi bankasi yuklendi: {list(KNOWLEDGE.keys())}")
    except Exception as e:
        log.warning(f"Bilgi bankasi yuklenemedi: {e}")

def get_relevant_knowledge(text: str) -> str:
    """Mesaja gore alakali bilgi snippet'i sec"""
    text_lower = text.lower()
    snippets = []
    
    # Her zaman profil ekle (kisa)
    if "profil" in KNOWLEDGE:
        profile_lines = [l for l in KNOWLEDGE["profil"].split("\\n") 
                        if l.startswith("- ") or l.startswith("**")][:8]
        snippets.append("Kullanici profili:\\n" + "\\n".join(profile_lines))
    
    # eBay sorusuysa
    if any(k in text_lower for k in ["ebay", "dropship", "listing", "urun", "satis"]):
        if "ebay_strateji" in KNOWLEDGE:
            # Ilk 500 karakter
            snippets.append("eBay Bilgisi:\\n" + KNOWLEDGE["ebay_strateji"][:600])
    
    # Trendyol sorusuysa
    if any(k in text_lower for k in ["trendyol", "tr pazar", "turkiye"]):
        if "trendyol_strateji" in KNOWLEDGE:
            snippets.append("Trendyol Bilgisi:\\n" + KNOWLEDGE["trendyol_strateji"][:600])
    
    return "\\n\\n".join(snippets) if snippets else ""

_load_knowledge()
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    # Create knowledge dir on server
    try:
        sftp.mkdir("/opt/jarvis/knowledge")
    except:
        pass  # dir might exist
    
    # Upload knowledge files
    for src, dst in knowledge_files:
        sftp.put(src, dst)
        print(f"  ✅ {dst}")
    
    sftp.close()
    transport.close()
    
    # Now SSH to update bridge.py
    client.connect(hostname=host, username=username, password=password, timeout=10)
    sftp2 = client.open_sftp()
    
    # Read bridge.py
    with sftp2.file("/opt/jarvis/openclaw/bridge.py", "r") as f:
        content = f.read().decode()
    
    # Inject knowledge code after the log definition
    if "KNOWLEDGE_DIR" not in content:
        insert_marker = "# ─── SOUL (Kimlik) — must be before MODEL_ROUTES ──"
        if insert_marker in content:
            content = content.replace(insert_marker, KNOWLEDGE_CODE + "\n" + insert_marker)
            print("  ✅ Knowledge loader injected into bridge.py")
        else:
            # Insert after log definition
            marker2 = 'log = logging.getLogger("jarvis")'
            if marker2 in content:
                content = content.replace(marker2, marker2 + "\n" + KNOWLEDGE_CODE)
                print("  ✅ Knowledge loader injected (alternate position)")
    else:
        print("  ℹ️  Knowledge loader already present")
    
    # Enhance call_ollama to inject knowledge context
    if "get_relevant_knowledge" not in content:
        # Add knowledge injection in process_message before call_ollama
        old = "    history.append({\"role\": \"user\", \"content\": text})\n    model = route[\"model\"]\n    response = call_ollama(model, history, route[\"system\"])"
        new = """    history.append({"role": "user", "content": text})
    model = route["model"]
    # Inject relevant knowledge
    knowledge_ctx = get_relevant_knowledge(text)
    system_prompt = route["system"]
    if knowledge_ctx:
        system_prompt = system_prompt + "\\n\\n=== BAĞLAM ===\\n" + knowledge_ctx
    response = call_ollama(model, history, system_prompt)"""
        if old in content:
            content = content.replace(old, new)
            print("  ✅ Knowledge context injection added to process_message")
        else:
            print("  ⚠️  Could not find process_message injection point")
    
    # Write back
    with sftp2.file("/opt/jarvis/openclaw/bridge.py", "w") as f:
        f.write(content)
    sftp2.close()
    
    # Syntax check
    _, sy, _ = client.exec_command("python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo SYNTAX_OK 2>&1", get_pty=True)
    sy_out = sy.read().decode().strip()
    print(f"\n  Syntax: {sy_out}")
    
    if "SYNTAX_OK" in sy_out:
        client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
        time.sleep(4)
        _, st, _ = client.exec_command("systemctl is-active jarvis.service")
        print(f"  Service: {st.read().decode().strip()}")
        _, lo, _ = client.exec_command("tail -10 /home/userk/.jarvis/jarvis.log")
        print("\nLog:\n" + lo.read().decode())
    else:
        print("  ❌ SYNTAX ERROR - checking...")
        _, lo, _ = client.exec_command("python3 /opt/jarvis/openclaw/bridge.py 2>&1 | head -20")
        print(lo.read().decode())
    
    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()

print("\n✅ Knowledge base deployed!")
