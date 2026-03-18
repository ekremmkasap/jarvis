"""
Deploy all next skills to the server and update bridge.py.
"""
import paramiko
import time

host, username, password = "192.168.1.109", "userk", "userk1"

files = [
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\whisper_skill.py",
     "/opt/jarvis/skills/whisper_skill.py"),
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\trendyol_skill.py",
     "/opt/jarvis/skills/trendyol_skill.py"),
    (r"C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\whatsapp_skill.py",
     "/opt/jarvis/skills/whatsapp_skill.py"),
]

# The bridge.py patch to add /trendyol, /whisper commands and Trendyol routing
BRIDGE_PATCH = '''
def _patch_bridge():
    path = "/opt/jarvis/openclaw/bridge.py"
    with open(path, "r") as f:
        content = f.read()
    
    changes = 0
    
    # 1. Add /trendyol command to handle_command
    if "/trendyol" not in content:
        old = "    elif command == \"/plan\":"
        new = """    elif command == "/trendyol":
        query = args or "bluetooth kulaklık"
        import sys
        sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from trendyol_skill import full_trendyol_analysis
            response = full_trendyol_analysis(query)
        except Exception as e:
            response = f"Trendyol skill hatası: {e}"
        memory.add_message(chat_id, "user", f"/trendyol {query}")
        memory.add_message(chat_id, "assistant", response, "trendyol_skill")
        return response

    elif command == "/plan\\":
"""
        if old in content:
            content = content.replace(old, new)
            changes += 1

    # 2. Add "trendyol" to the /help text
    if "trendyol" not in content:
        old = '  `/ebay [ürün]` → eBay ürün araştırması'
        new = '  `/ebay [ürün]` → eBay ürün araştırması\\n  `/trendyol [ürün]` → Trendyol TR pazar analizi'
        if old in content:
            content = content.replace(old, new)
            changes += 1
    
    # 3. Add "trendyol" to routing keywords (search route)
    if '"trendyol"' not in content:
        old = '"keywords": ["ara", "bul", "ebay"'
        new = '"keywords": ["ara", "bul", "ebay", "trendyol", "tr pazar"'
        if old in content:
            content = content.replace(old, new)
            changes += 1

    with open(path, "w") as f:
        f.write(content)
    print(f"bridge.py patched ({changes} changes)")

_patch_bridge()
'''

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)

    for src, dst in files:
        sftp.put(src, dst)
        print(f"  ✅ Uploaded: {dst}")

    # Now create WhatsApp setup files on server
    sftp.close()
    transport.close()

    client.connect(hostname=host, username=username, password=password, timeout=10)

    # Create WhatsApp directory
    client.exec_command("mkdir -p /opt/jarvis/whatsapp")
    
    # Write the WA bridge JS file
    wa_js_content = open(r"C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\whatsapp_skill.py").read()
    # Extract JS content
    import re
    js_match = re.search(r'WHATSAPP_BRIDGE_JS = """(.*?)"""', wa_js_content, re.DOTALL)
    if js_match:
        wa_js = js_match.group(1)
        sftp2 = client.open_sftp()
        with sftp2.file("/opt/jarvis/whatsapp/wa_bridge.js", "w") as f:
            f.write(wa_js)
        
        # Write install script
        install_match = re.search(r'INSTALL_SCRIPT = """(.*?)"""', wa_js_content, re.DOTALL)
        if install_match:
            with sftp2.file("/opt/jarvis/whatsapp/install.sh", "w") as f:
                f.write(install_match.group(1))
        
        # Write WA skill py
        skill_match = re.search(r'WHATSAPP_SKILL_PY = """(.*?)"""', wa_js_content, re.DOTALL)
        if skill_match:
            with sftp2.file("/opt/jarvis/skills/wa_skill.py", "w") as f:
                f.write(skill_match.group(1))
        
        sftp2.close()
        print("  ✅ WhatsApp bridge files written")

    # Write and run the bridge patch
    sftp3 = client.open_sftp()
    with sftp3.file("/tmp/patch_bridge.py", "w") as f:
        f.write(BRIDGE_PATCH)
    sftp3.close()

    _, po, pe = client.exec_command("python3 /tmp/patch_bridge.py 2>&1", get_pty=True)
    po.channel.recv_exit_status()
    print("  Patch:", po.read().decode().strip())

    # Install Whisper on server (background)
    print("\nInstalling Whisper (background, may take 2-3 mins)...")
    client.exec_command(
        "pip3 install --break-system-packages openai-whisper 2>&1 | tail -3 > /home/userk/.jarvis/whisper_install.log &"
    )

    # Install Node.js if not present
    _, nd, _ = client.exec_command("node --version 2>/dev/null")
    node_ver = nd.read().decode().strip()
    if not node_ver:
        print("Node.js yok, kuruluyor (arka planda)...")
        client.exec_command(
            "curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - "
            "&& sudo apt-get install -y nodejs > /home/userk/.jarvis/node_install.log 2>&1 &"
        )
    else:
        print(f"  Node.js: {node_ver} ✅")

    # Restart jarvis to pick up bridge.py changes
    time.sleep(2)
    client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
    time.sleep(3)
    
    _, st, _ = client.exec_command("systemctl is-active jarvis.service")
    print(f"\n  jarvis.service: {st.read().decode().strip()}")

    # Final log check
    _, lo, _ = client.exec_command("tail -10 /home/userk/.jarvis/jarvis.log")
    log = lo.read().decode()
    print("\nJarvis log:")
    print(log)

    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()

print("\n✅ Deploy complete!")
