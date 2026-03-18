"""
Directly patch bridge.py via SSH to add new commands cleanly.
"""
import paramiko
import time

host, username, password = "192.168.1.109", "userk", "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)

    # Read current bridge.py
    sftp = client.open_sftp()
    with sftp.file("/opt/jarvis/openclaw/bridge.py", "r") as f:
        content = f.read().decode()

    print(f"bridge.py size: {len(content)} chars")

    # Patch 1: Add /trendyol before /plan section
    if "/trendyol" not in content:
        trendyol_cmd = '''
    elif command == "/trendyol":
        query = args or "bluetooth kulaklık"
        import sys as _sys
        _sys.path.insert(0, "/opt/jarvis/skills")
        try:
            from trendyol_skill import full_trendyol_analysis
            response = full_trendyol_analysis(query)
        except Exception as _e:
            route = MODEL_ROUTES["search"]
            prompt = f"Trendyol TR pazarında \\"{query}\\" için ürün analizi yap:\\n1. Fiyat aralığı (TL)\\n2. Rekabet\\n3. Dropshipping fırsatı?\\n4. AliExpress karşılaştırması"
            history = [{{"role": "user", "content": prompt}}]
            response = call_ollama(route["model"], history, route["system"])
        memory.add_message(chat_id, "user", f"/trendyol {query}")
        memory.add_message(chat_id, "assistant", response, "trendyol")
        return f"🇹🇷 **Trendyol Analizi:**\\n\\n{response}"
'''
        # Insert before the last "return" in handle_command
        target = '    return f"❓ Bilinmeyen komut: {command}\\n/help yaz yardım için."'
        if target in content:
            content = content.replace(target, trendyol_cmd + "\n" + target)
            print("  ✅ /trendyol command added")
        else:
            print("  ⚠️  Target not found, trying alternate insertion...")
            # Find end of elif chain and insert
            old_end = '    return f"❓ Bilinmeyen'
            if old_end in content:
                content = content.replace(old_end, trendyol_cmd + "\n    " + old_end[4:])
                print("  ✅ /trendyol added (alternate)")
    else:
        print("  ℹ️  /trendyol already in bridge.py")

    # Patch 2: Add /trendyol to /help text
    if "trendyol" not in content.lower():
        old_help = "  `/ebay [ürün]` → eBay ürün araştırması"
        new_help = "  `/ebay [ürün]` → eBay ürün araştırması\n  `/trendyol [ürün]` → Trendyol TR pazar analizi"
        if old_help in content:
            content = content.replace(old_help, new_help)
            print("  ✅ /help updated with trendyol")

    # Write back
    with sftp.file("/opt/jarvis/openclaw/bridge.py", "w") as f:
        f.write(content)
    sftp.close()
    print("  ✅ bridge.py written back")

    # Restart jarvis
    time.sleep(1)
    _, so, _ = client.exec_command(
        "echo 'userk1' | sudo -S systemctl restart jarvis.service 2>&1", get_pty=True
    )
    so.channel.recv_exit_status()
    time.sleep(3)

    _, st, _ = client.exec_command("systemctl is-active jarvis.service")
    status = st.read().decode().strip()
    print(f"\n  jarvis.service: {status}")

    # Final tail log
    _, lo, _ = client.exec_command("tail -8 /home/userk/.jarvis/jarvis.log")
    print("\nLog:\n" + lo.read().decode())

    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
