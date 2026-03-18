"""
Check server Ollama models and pull missing ones in background
"""
import paramiko, time

# Models from user's screenshot - ordered by priority
WANTED_MODELS = [
    "nomic-embed-text:latest",  # 274MB - RAG/embeddings için şart
    "deepseek-r1:8b",           # 5.2GB - En iyi reasoning modeli
    "qwen2.5-coder:7b",         # 4.7GB - Coding
    "llava:7b",                 # 4.7GB - Vision (görsel analiz)
    "mistral:latest",           # 4.4GB - Genel amaç
    "llama3.2:3b",             # 2.0GB - Hızlı yanıt
    "moondream:latest",         # 1.7GB - Küçük vision model
    "deepseek-coder:latest",    # 776MB - Kompakt coding model
]

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)

# Check current models
print("[1] Server'daki mevcut modeller:")
_, out, _ = client.exec_command('ollama list 2>&1')
current = out.read().decode()
print(current)

# Check disk space
_, disk_out, _ = client.exec_command('df -h /opt 2>&1 || df -h / 2>&1')
print("[2] Disk durumu:")
print(disk_out.read().decode())

# Determine which models to pull
current_lower = current.lower()
to_pull = []
for model in WANTED_MODELS:
    name = model.split(':')[0]
    if name not in current_lower:
        to_pull.append(model)

print(f"\n[3] Çekilecek modeller ({len(to_pull)}):")
for m in to_pull:
    print(f"  - {m}")

# Pull missing models in background using nohup
if to_pull:
    # Create pull script on server
    pull_script = "#!/bin/bash\n"
    pull_script += "LOG=/tmp/ollama_pull.log\n"
    pull_script += "echo 'Starting model downloads...' > $LOG\n"
    for model in to_pull:
        pull_script += f"echo 'Pulling {model}...' >> $LOG\n"
        pull_script += f"ollama pull {model} >> $LOG 2>&1\n"
        pull_script += f"echo '{model} done!' >> $LOG\n"
    pull_script += "echo 'All models downloaded!' >> $LOG\n"
    
    sftp = client.open_sftp()
    with sftp.file('/tmp/pull_models.sh', 'w') as f:
        f.write(pull_script)
    sftp.close()
    
    client.exec_command('chmod +x /tmp/pull_models.sh')
    client.exec_command('nohup bash /tmp/pull_models.sh &')
    print("\n✅ Model indirme arka planda başladı!")
    print("Durumu görmek için: tail -f /tmp/ollama_pull.log")
    time.sleep(2)
    
    # Show initial log
    _, log_out, _ = client.exec_command('cat /tmp/ollama_pull.log 2>&1')
    print("\nLog:")
    print(log_out.read().decode())
else:
    print("\n✅ Tüm modeller zaten mevcut!")

client.close()
