import paramiko
import time

host = "192.168.1.109"
port = 22
username = "userk"
password = "userk1"

# We use echo password | sudo -S for non-interactive sudo execution
setup_script = """#!/bin/bash
echo "=== Establishing Jarvis Mission Control Architecture (Phase 1) ==="

# Base Directory
BASE_DIR="/opt/jarvis"
echo "userk1" | sudo -S mkdir -p $BASE_DIR
echo "userk1" | sudo -S chown -R $USER:$USER $BASE_DIR

# 1. Orchestrator & Core Actions
mkdir -p $BASE_DIR/core
mkdir -p $BASE_DIR/config
mkdir -p $BASE_DIR/logs

# 2. Sub-Agents
mkdir -p $BASE_DIR/agents
mkdir -p $BASE_DIR/agents/planner
mkdir -p $BASE_DIR/agents/implementer
mkdir -p $BASE_DIR/agents/reviewer

# 3. Memory Structure (j.txt Section 3)
mkdir -p $BASE_DIR/memory/working_memory
mkdir -p $BASE_DIR/memory/project_memory
mkdir -p $BASE_DIR/memory/knowledge_store

# 4. Skills (j.txt Section 5)
mkdir -p $BASE_DIR/skills/cognitive
mkdir -p $BASE_DIR/skills/execution
mkdir -p $BASE_DIR/skills/io
mkdir -p $BASE_DIR/skills/governance

# Create initial place holder files
touch $BASE_DIR/core/agent.py
touch $BASE_DIR/core/orchestrator.py
touch $BASE_DIR/memory/project_memory/MISSION.md
touch $BASE_DIR/memory/project_memory/MEMORY.md

# OpenClaw base structure for Gateway (if needed later)
mkdir -p $BASE_DIR/openclaw
touch $BASE_DIR/openclaw/bridge.py

echo "=== Folder structure successfully created in $BASE_DIR ==="
ls -la $BASE_DIR
"""

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {host}...")
    client.connect(hostname=host, port=port, username=username, password=password, timeout=10)
    
    # create script via SFTP
    sftp = client.open_sftp()
    with sftp.file('/home/userk/setup_jarvis_sudo.sh', 'w') as f:
        f.write(setup_script)
    sftp.close()
    
    # execute
    cmd = "chmod +x /home/userk/setup_jarvis_sudo.sh && /home/userk/setup_jarvis_sudo.sh"
    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    
    out = stdout.read().decode('utf-8')
    err = stderr.read().decode('utf-8')
    
    print(out)
    if err:
        print(f"Errors: {err}")

except Exception as e:
    print(f"Failed: {e}")
finally:
    client.close()
