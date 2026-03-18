import paramiko
import json

host = "192.168.1.109"
username = "userk"
password = "userk1"

# Best Ollama model available on the system (visible in the screenshot)
# llama3.2:latest  - seen in screenshot as nomic-embed-text, deepseek, mistral, devstral
# Let's use llama3.2 as primary with deepseek as fallback
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
        },
        "ollama/mistral:latest": {
          "alias": "Mistral"
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

config_json = json.dumps(new_config, indent=2)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting...")
    client.connect(hostname=host, username=username, password=password, timeout=8)

    # Step 1: Backup
    print("Step 1: Backing up config...")
    stdin, stdout, _ = client.exec_command("cp /home/userk/.openclaw/openclaw.json /home/userk/.openclaw/openclaw.json.bak.before_ollama")
    stdout.channel.recv_exit_status()
    print("  Backup done.")
    
    # Step 2: Upload new config via SFTP
    print("Step 2: Writing new Ollama config...")
    sftp = client.open_sftp()
    with sftp.file('/home/userk/.openclaw/openclaw.json', 'w') as f:
        f.write(config_json)
    sftp.close()
    print("  Config written!")
    
    # Step 3: Stop the existing openclaw gateway
    print("Step 3: Stopping OpenClaw service...")
    stdin2, stdout2, _ = client.exec_command("echo 'userk1' | sudo -S systemctl stop openclaw.service 2>/dev/null; pkill -f 'openclaw' 2>/dev/null || echo 'no process to kill'")
    stdout2.channel.recv_exit_status()
    print("  Stopped.")
    
    # Step 4: Check if official openclaw is available
    print("Step 4: Checking openclaw binary location...")
    stdin3, stdout3, _ = client.exec_command("which openclaw")
    openclaw_path = stdout3.read().decode().strip()
    print(f"  openclaw binary: {openclaw_path}")
    
    # Step 5: Restart
    print("Step 5: Starting openclaw gateway with new Ollama config...")
    start_cmd = f"nohup {openclaw_path} start > /home/userk/openclaw-ollama.log 2>&1 &" if openclaw_path else "echo 'openclaw not in PATH'"
    stdin4, stdout4, _ = client.exec_command(start_cmd)
    stdout4.channel.recv_exit_status()
    print("  Started!")
    
    import time
    time.sleep(3)
    
    # Step 6: Check log
    print("Step 6: Checking startup log...")
    stdin5, stdout5, _ = client.exec_command("cat /home/userk/openclaw-ollama.log 2>/dev/null | head -30")
    log = stdout5.read().decode()
    print(log if log else "(log empty - waiting for startup)")
    
    # Step 7: Verify new config was saved
    print("\nStep 7: Verifying new config on server...")
    stdin6, stdout6, _ = client.exec_command("cat /home/userk/.openclaw/openclaw.json | python3 -m json.tool | grep -E 'primary|provider|baseUrl'")
    print(stdout6.read().decode())

except Exception as e:
    print(f"Error: {e}")
finally:
    client.close()
    print("Done.")
