"""
Uploads the fixed openclaw.json config directly via SFTP only.
No blocking SSH commands that cause timeouts.
"""
import paramiko
import json

host = "192.168.1.109"
username = "userk"
password = "userk1"

# Based on the models visible in the user's Ollama screenshot:
# llama3.2:latest, mistral:latest, deepseek-r1:latest, qwen2.5-coder:7b, devstral:latest
# Going with llama3.2 as primary (appears first, most capable chat model)
new_config = {
  "meta": {
    "lastTouchedVersion": "2026.2.24",
    "lastTouchedAt": "2026-03-01T18:50:00.000Z"
  },
  "wizard": {
    "lastRunAt": "2026-02-25T22:07:43.057Z",
    "lastRunVersion": "2026.2.24",
    "lastRunCommand": "onboard",
    "lastRunMode": "local"
  },
  "auth": {
    "profiles": {
      "ollama:local": {
        "provider": "ollama",
        "mode": "local",
        "baseUrl": "http://127.0.0.1:11434"
      }
    }
  },
  "agents": {
    "defaults": {
      "model": {
        "primary": "ollama/llama3.2:latest"
      },
      "models": {
        "ollama/llama3.2:latest": {"alias": "Llama3"},
        "ollama/deepseek-r1:latest": {"alias": "DeepSeek"},
        "ollama/qwen2.5-coder:7b": {"alias": "QwenCoder"},
        "ollama/mistral:latest": {"alias": "Mistral"},
        "ollama/devstral:latest": {"alias": "Devstral"}
      },
      "workspace": "/home/userk/.openclaw/workspace",
      "compaction": {"mode": "safeguard"},
      "maxConcurrent": 4,
      "subagents": {"maxConcurrent": 8}
    }
  },
  "messages": {"ackReactionScope": "group-mentions"},
  "commands": {
    "native": "auto",
    "nativeSkills": "auto",
    "restart": True,
    "ownerDisplay": "raw"
  },
  "session": {"dmScope": "per-channel-peer"},
  "channels": {
    "telegram": {
      "enabled": True,
      "dmPolicy": "pairing",
      "groupPolicy": "allowlist",
      "streaming": "off"
    }
  },
  "gateway": {
    "port": 18789,
    "mode": "local",
    "bind": "loopback",
    "auth": {
      "mode": "token",
      "token": "b630cff25495995973a4f8cd911ada685f1e4e569f905c73"
    },
    "tailscale": {"mode": "off", "resetOnExit": False}
  }
}

config_json = json.dumps(new_config, indent=2)

transport = None
try:
    print("Opening SFTP-only transport...")
    transport = paramiko.Transport((host, 22))
    transport.connect(username=username, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    # Backup existing config
    try:
        sftp.rename('/home/userk/.openclaw/openclaw.json',
                    '/home/userk/.openclaw/openclaw.json.bak.before_ollama')
        print("Backup: openclaw.json.bak.before_ollama created")
    except Exception as e:
        print(f"Backup note: {e}")
    
    # Write the new config
    with sftp.file('/home/userk/.openclaw/openclaw.json', 'w') as f:
        f.write(config_json)
    
    print("SUCCESS: New Ollama config uploaded to /home/userk/.openclaw/openclaw.json")
    
    # Verify 
    with sftp.file('/home/userk/.openclaw/openclaw.json', 'r') as f:
        check = f.read(200).decode()
    print(f"Verification (first 200 chars):\n{check}")
    
    sftp.close()
    
    print("\nNext step: Now restart openclaw via SSH (brief command)...")
    
    # Quick SSH exec - just kill and restart
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, timeout=8)
    
    # Just restart, don't wait for output
    client.exec_command("pkill -f 'openclaw-gateway' 2>/dev/null; sleep 1; nohup openclaw start > /tmp/oc_restart.log 2>&1 &")
    print("OpenClaw restart command sent!")
    client.close()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    if transport:
        transport.close()

print("\nDone. OpenClaw should now use local Ollama models (llama3.2) instead of OpenAI API.")
print("Test by sending a message to your Telegram bot!")
