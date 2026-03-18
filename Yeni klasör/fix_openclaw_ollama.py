import paramiko
import json

host = "192.168.1.109"
username = "userk"
password = "userk1"

# The updated openclaw.json with Ollama as the AI provider
# Based on OpenClaw docs, we use "ollama" provider and point to local API
new_config = {
  "meta": {
    "lastTouchedVersion": "2026.2.24",
    "lastTouchedAt": "2026-03-01T18:45:00.000Z"
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
        "ollama/llama3.2:latest": {
          "alias": "Llama3"
        },
        "ollama/deepseek-r1:latest": {
          "alias": "DeepSeek"
        },
        "ollama/qwen2.5-coder:7b": {
          "alias": "QwenCoder"
        }
      },
      "workspace": "/home/userk/.openclaw/workspace",
      "compaction": {
        "mode": "safeguard"
      },
      "maxConcurrent": 4,
      "subagents": {
        "maxConcurrent": 8
      }
    }
  },
  "messages": {
    "ackReactionScope": "group-mentions"
  },
  "commands": {
    "native": "auto",
    "nativeSkills": "auto",
    "restart": True,
    "ownerDisplay": "raw"
  },
  "session": {
    "dmScope": "per-channel-peer"
  },
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
    "tailscale": {
      "mode": "off",
      "resetOnExit": False
    }
  }
}

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    client.connect(hostname=host, username=username, password=password, timeout=10)
    
    print("=== Checking which Ollama models are installed ===")
    stdin, stdout, _ = client.exec_command("ollama list", get_pty=True)
    ollama_out = stdout.read().decode('utf-8')
    print(ollama_out)
    
    # Find the best available model
    best_model = "ollama/llama3.2:latest"
    if "llama3.2" in ollama_out:
        best_model = "ollama/llama3.2:latest"
    elif "llama3" in ollama_out:
        best_model = "ollama/llama3:latest"
    elif "qwen2.5-coder" in ollama_out:
        best_model = "ollama/qwen2.5-coder:7b"
    elif "deepseek" in ollama_out:
        best_model = "ollama/deepseek-r1:latest"
    
    print(f"Best model selected: {best_model}")
    new_config["agents"]["defaults"]["model"]["primary"] = best_model
    
    print("\n=== Backing up current config ===")
    stdin2, stdout2, _ = client.exec_command("cp /home/userk/.openclaw/openclaw.json /home/userk/.openclaw/openclaw.json.bak.before_ollama", get_pty=True)
    stdout2.read()
    print("Backup created: openclaw.json.bak.before_ollama")
    
    print("\n=== Writing new Ollama config ===")
    config_json = json.dumps(new_config, indent=2)
    sftp = client.open_sftp()
    with sftp.file('/home/userk/.openclaw/openclaw.json', 'w') as f:
        f.write(config_json)
    sftp.close()
    print("Config written successfully!")
    
    print("\n=== Restarting OpenClaw via openclaw restart ===")
    stdin3, stdout3, _ = client.exec_command("pkill -f openclaw 2>/dev/null; echo 'killed'", get_pty=True)
    print(stdout3.read().decode())
    
    # Start openclaw in background
    stdin4, stdout4, _ = client.exec_command(
        "nohup openclaw start > /home/userk/openclaw-start.log 2>&1 &",
        get_pty=True
    )
    stdout4.read()
    print("OpenClaw restarted!")
    
    import time
    time.sleep(3)
    
    print("\n=== Checking OpenClaw status ===")
    stdin5, stdout5, _ = client.exec_command("cat /home/userk/openclaw-start.log | head -20", get_pty=True)
    print(stdout5.read().decode())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
