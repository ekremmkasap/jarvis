# JARVIS 24-HOUR AUTONOMOUS LOOP

## Quick Start (Windows)

```powershell
# Terminal 1: Start OpenClaw dev gateway
openclaw --dev gateway --force

# Terminal 2: Start 24-hour autonomous loop (PRODUCTION)
cd C:\Users\sergen\Desktop\jarvis-mission-control
$env:TEST_MODE = "0"
$env:JARVIS_ALLOWED_CHAT_IDS = "5847386182"
python scripts/start_24h_autonomous_loop.py

# OR: Start in TEST_MODE (30s intervals, 3 iterations)
$env:TEST_MODE = "1"
python scripts/start_24h_autonomous_loop.py
```

## What It Does (Every Hour)

1. **PHASE 1: Research** - Brainstorm optimization ideas
2. **PHASE 2: Self-improve** - Evaluate strategy
3. **PHASE 3: Metrics** - Measure improvement %
4. **PHASE 4: Testing** - Validate changes
5. **PHASE 5: Git commit** - Save good changes
6. **TELEGRAM REPORT** - Hourly notification

## Example Telegram Report

```
[JARVIS] AUTONOMOUS LOOP - Hour 5:00
Autonomous improvement cycle in progress...

- Progress: 20% (5/24h)
- Improvement: +3.4%
- Trend: UP
- Tests: 48/50 OK
- Commit: yes
- Report: Hourly automated observation
```

## Files

- `scripts/start_24h_autonomous_loop.py` - Main loop engine
- `server/openclaw_bridge.py` - Telegram integration
- `server/logs/autonomous/` - Reports and state

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| TEST_MODE | 0 | Set to 1 for 30s intervals (testing) |
| AUTONOMOUS_DURATION_HOURS | 24 | Loop duration |
| AUTONOMOUS_REPORT_INTERVAL_MINUTES | 60 | Telegram report frequency |
| JARVIS_ALLOWED_CHAT_IDS | 5847386182 | Telegram recipient |

## Status Commands

```bash
# Check current state
cat server/agent_workspace/autonomous/current_job.json

# View reports log
tail -f server/logs/autonomous/jobs.jsonl

# View all telegram notifications sent
grep "messageId" server/logs/autonomous/telegram.log
```

## Stop/Resume

```bash
# Stop (Ctrl+C in loop terminal)
# Manual stop: kill the Python process

# Resume: just run the script again
# It will load previous state from current_job.json
```

## Full Production Setup (Windows Task Scheduler)

Create `Start-Jarvis-24h.ps1`:

```powershell
# Admin PowerShell
schtasks /create /tn "Jarvis-Autonomous-24h" /sc onstart /rl HIGHEST `
  /tr "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"C:\Users\sergen\Desktop\jarvis-mission-control\Start-Jarvis-24h.ps1`""
```

Contents of `Start-Jarvis-24h.ps1`:

```powershell
$RepoRoot = "C:\Users\sergen\Desktop\jarvis-mission-control"
Set-Location $RepoRoot

# Load .env
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^\s*#" -or $_ -notmatch "=") { return }
    $k,$v = $_.Split("=",2)
    $k = $k.Trim(); $v = $v.Trim()
    if ($k.Length -gt 0) { [Environment]::SetEnvironmentVariable($k,$v,"Process") }
}

# Start OpenClaw gateway (detached)
Start-Process -FilePath "openclaw" -ArgumentList "--dev","gateway","--force" -WindowStyle Hidden

# Wait for gateway
Start-Sleep -Seconds 4

# Start autonomous loop (detached) with output to file
$logPath = "$RepoRoot\server\logs\autonomous\loop-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"
Start-Process -FilePath "python" -ArgumentList "scripts/start_24h_autonomous_loop.py" `
  -RedirectStandardOutput $logPath `
  -RedirectStandardError $logPath `
  -WindowStyle Hidden

Write-Host "Jarvis 24h loop started. Log: $logPath"
```

## Monitoring Dashboard

Open in browser:
- OpenClaw dashboard: http://127.0.0.1:19001/
- Watch logs: `tail -f server/logs/autonomous/jobs.jsonl | jq '.hour, .progress_pct, .phases.metrics.improvement_pct'`

## Troubleshooting

**OpenCode not found:**
- Install OpenCode: `npm install -g opencode`

**Telegram not sending:**
- Check env: `echo $env:JARVIS_ALLOWED_CHAT_IDS`
- Test manually: `openclaw message send --channel telegram --target "5847386182" --message "test"`

**Loop stuck:**
- Check: `ps aux | grep python`
- Kill: `taskkill /F /IM python.exe`
- Restart: `python scripts/start_24h_autonomous_loop.py`

---

**Current Status:** Ready for 24-hour autonomous operation  
**Last Updated:** 2026-04-04 06:20 UTC
