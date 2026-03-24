import sys, os

bridge_path = r"C:\Users\sergen\Desktop\jarvis-mission-control\server\bridge.py"

with open(bridge_path, 'r', encoding='utf-8') as f:
    code = f.read()

# Eger zaten eklenmisse bir daha ekleme
if "/osint" not in code:
    # Komutlari ekleyecek yeri bul, cmd altina ekle
    target = "    elif command == \"/cmd\":"
    
    new_commands = """
    elif command == "/osint":
        hedef = args.strip()
        if not hedef:
            return "Kullanim: /osint [hedef (IP, isim, vd.)]"
        try:
            from shadowbroker_skill import run_osint
            return run_osint(hedef)
        except Exception as e:
            return f"OSINT hatasi: {e}"

    elif command == "/arastirma" or command == "/research":
        hedef = args.strip()
        if not hedef:
            return "Kullanim: /arastirma [konu]"
        try:
            from autoresearch_skill import run_deep_research
            return run_deep_research(hedef)
        except Exception as e:
            return f"Arastirma motoru hatasi: {e}"

    elif command == "/sandbox":
        kod = args.strip()
        if not kod:
            return "Kullanim: /sandbox [python kodu]"
        try:
            from opensandbox_skill import run_in_sandbox
            return run_in_sandbox(kod)
        except Exception as e:
            return f"Sandbox calistirma hatasi: {e}"
"""
    
    code = code.replace(target, new_commands + "\n" + target)

    with open(bridge_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print("Bridge'e komutlar eklendi!")
else:
    print("Komutlar zaten var.")
