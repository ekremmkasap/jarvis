"""
Fix bridge.py: JARVIS_SOUL is referenced in MODEL_ROUTES before being defined.
Move JARVIS_SOUL definition before MODEL_ROUTES.
"""
import paramiko
import time

host, username, password = "192.168.1.109", "userk", "userk1"

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    sftp = client.open_sftp()
    
    with sftp.file("/opt/jarvis/openclaw/bridge.py", "r") as f:
        content = f.read().decode()
    
    print(f"bridge.py size: {len(content)} chars")
    
    # The JARVIS_SOUL block that was patched in via apply_soul.py after the logger
    # We need it to exist BEFORE the MODEL_ROUTES dict
    # Find the JARVIS_SOUL block and move it
    
    # First: check if JARVIS_SOUL is defined
    if "JARVIS_SOUL" in content:
        print("JARVIS_SOUL found. Checking order...")
        
        soul_idx = content.find("JARVIS_SOUL")
        routes_idx = content.find("MODEL_ROUTES")
        
        print(f"  JARVIS_SOUL at pos: {soul_idx}")
        print(f"  MODEL_ROUTES at pos: {routes_idx}")
        
        if soul_idx > routes_idx:
            print("  ❌ SOUL is after ROUTES — fixing order...")
            
            # Extract the SOUL block
            soul_start = content.find("# ─── SOUL (Kimlik) ───")
            soul_end = content.find("\n# ─", soul_start + 10)
            if soul_end == -1:
                soul_end = content.find("\nMODEL_ROUTES", soul_start)
            
            soul_block = content[soul_start:soul_end]
            
            # Remove from current location
            content = content[:soul_start] + content[soul_end:]
            
            # Insert before MODEL_ROUTES
            routes_pos = content.find("# ─────────────────────────── MODEL ROUTER")
            if routes_pos == -1:
                routes_pos = content.find("MODEL_ROUTES = {")
            
            content = content[:routes_pos] + soul_block + "\n\n" + content[routes_pos:]
            print("  ✅ SOUL moved before MODEL_ROUTES")
        else:
            print("  ✅ Order is correct already")
            
            # The issue is "system": JARVIS_SOUL is in MODEL_ROUTES which is a module-level dict
            # JARVIS_SOUL itself must be defined before MODEL_ROUTES
            # Let's check the exact issue
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "JARVIS_SOUL" in line:
                    print(f"  Line {i+1}: {line[:80]}")
    else:
        print("JARVIS_SOUL not found — adding simple fallback...")
        # Add before MODEL_ROUTES
        routes_pos = content.find("MODEL_ROUTES = {")
        soul_simple = '''# ─── SOUL (Kimlik) ───────────────────────────────────────────────
try:
    with open("/opt/jarvis/soul.md", "r") as _f:
        JARVIS_SOUL = _f.read()
except Exception:
    JARVIS_SOUL = "Sen Jarvis'sin, Ekrem'in AI asistanı. Zeki, pratik, Tony Stark tarzı."

'''
        content = content[:routes_pos] + soul_simple + content[routes_pos:]
        print("  ✅ JARVIS_SOUL added before MODEL_ROUTES")
    
    with sftp.file("/opt/jarvis/openclaw/bridge.py", "w") as f:
        f.write(content)
    sftp.close()
    print("\n  bridge.py saved.")
    
    # Test syntax
    _, sy, _ = client.exec_command("python3 -m py_compile /opt/jarvis/openclaw/bridge.py && echo SYNTAX_OK", get_pty=True)
    sy_out = sy.read().decode().strip()
    print(f"  Syntax check: {sy_out}")
    
    if "SYNTAX_OK" in sy_out:
        # Restart service
        client.exec_command("echo 'userk1' | sudo -S systemctl restart jarvis.service")
        time.sleep(4)
        _, st, _ = client.exec_command("systemctl is-active jarvis.service")
        status = st.read().decode().strip()
        print(f"  jarvis.service: {status}")
        
        _, lo, _ = client.exec_command("tail -6 /home/userk/.jarvis/jarvis.log")
        print("\nLog:\n" + lo.read().decode())
    else:
        print("  ❌ Syntax error, not restarting")
    
    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
