"""Deploy memory_skill.py and integrate with bridge.py"""
import paramiko, time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)
sftp = client.open_sftp()

# Create memory directory and upload skill
client.exec_command('mkdir -p /opt/jarvis/memory')
sftp.put(
    r'C:\Users\sergen\Desktop\jarvis-mission-control\src\skills\memory_skill.py',
    '/opt/jarvis/skills/memory_skill.py'
)
print("✅ memory_skill.py uploaded")

# Read bridge.py
with sftp.file('/opt/jarvis/openclaw/bridge.py', 'r') as f:
    content = f.read().decode()

# Add memory import and initialization near top
if 'memory_skill' not in content:
    MEM_IMPORT = '''
# ─── MEMORY SYSTEM ───────────────────────────────────────────────────────────
import sys as _sys
_sys.path.insert(0, "/opt/jarvis/skills")
try:
    from memory_skill import save_message, get_history, format_history_for_ollama
    from memory_skill import save_fact, get_facts, get_user_context
    from memory_skill import add_task, get_tasks, update_task, daily_memory_report
    from memory_skill import init_db
    init_db()
    MEMORY_ENABLED = True
except Exception as _me:
    MEMORY_ENABLED = False
    def save_message(*a, **k): pass
    def get_history(*a, **k): return []
    def format_history_for_ollama(*a, **k): return []
    def get_user_context(*a, **k): return ""
    def add_task(*a, **k): return 0
    def get_tasks(*a, **k): return "Hafıza kapalı"
    def update_task(*a, **k): return ""
    def daily_memory_report(*a, **k): return "Hafıza kapalı"
# ─────────────────────────────────────────────────────────────────────────────
'''
    # Insert after existing imports
    import_pos = content.find('\nclass ')
    if import_pos > 0:
        content = content[:import_pos] + MEM_IMPORT + content[import_pos:]
    print("✅ Memory import added")

# Add /hafiza, /gorev, /gorev-ekle commands
MARKER = '    elif command == "/hava":'
MEMORY_CMDS = '''    elif command == "/hafiza":
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        return daily_memory_report(uid)

    elif command == "/gorev":
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        return get_tasks(uid)

    elif command == "/gorev-ekle":
        if not args:
            return "Kullanım: /gorev-ekle Görev başlığı"
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        task_id = add_task(uid, args, "normal")
        return f"✅ Görev eklendi: #{task_id} — {args}"

    elif command == "/gorev-bitti":
        if not args:
            return "Kullanım: /gorev-bitti [id]"
        uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
        try:
            return update_task(uid, int(args.strip()), "done")
        except:
            return "❌ Geçersiz görev ID"

    elif command == "/hava":'''

if MARKER in content and '/hafiza' not in content:
    content = content.replace(MARKER, MEMORY_CMDS)
    print("✅ Memory commands added")

# Inject memory into main AI query: save user input + assistant output
# Find the main query handler and wrap it
if 'save_message' not in content and 'MEMORY_ENABLED' in content:
    # Find where Ollama response is returned and add memory save
    OLD_RETURN = 'return response_text'
    if OLD_RETURN in content:
        NEW_RETURN = '''# Save to memory
        try:
            _uid = str(update.effective_user.id if hasattr(update, 'effective_user') else "default")
            save_message(_uid, "assistant", response_text, command=command)
        except:
            pass
        return response_text'''
        content = content.replace(OLD_RETURN, NEW_RETURN, 1)
        print("✅ Response save injected")

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

# Check model progress
_, log, _ = client.exec_command('tail -3 /tmp/ollama_pull.log 2>&1')
print(f"\nModel durumu: {log.read().decode().strip()}")

client.close()
print("\n✅ Memory system deployed!")
