import paramiko
import time

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Sunucuya baglaniliyor...")
client.connect('192.168.1.109', username='userk', password='userk1', timeout=10)

def exec_cmd(cmd):
    print(f"Calistiriliyor: {cmd}")
    stdin, stdout, stderr = client.exec_command(cmd)
    exit_status = stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    if exit_status != 0:
        print(f"Hata ({exit_status}): {err}")
    return out

# Klasor temizle ve olustur
exec_cmd("echo userk1 | sudo -S rm -rf /home/userk/agent_prompts")
exec_cmd("mkdir -p /home/userk/agent_prompts")

# Repolari cek
print("Claude Agents repolari indiriliyor (1/3)...")
exec_cmd("git clone https://github.com/iannuttall/claude-agents.git /home/userk/agent_prompts/iannuttall")

print("Claude Agents Kutuphanesi indiriliyor (2/3)...")
exec_cmd("git clone https://github.com/aiagentskit/claude-agents-library.git /home/userk/agent_prompts/library")

print("WS Hobson Agents indiriliyor (3/3)...")
exec_cmd("git clone https://github.com/wshobson/agents.git /home/userk/agent_prompts/wshobson")

print("Agent Prompts /opt/jarvis/icine tasiniyor...")
exec_cmd("echo userk1 | sudo -S rm -rf /opt/jarvis/agent_prompts")
exec_cmd("echo userk1 | sudo -S mv /home/userk/agent_prompts /opt/jarvis/")
exec_cmd("echo userk1 | sudo -S chown -R userk:userk /opt/jarvis/agent_prompts")

client.close()
print("GitHub ajanlari sunucuya başarıyla entegre edildi!")
