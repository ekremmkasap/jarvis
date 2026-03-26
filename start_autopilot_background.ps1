$root = "C:\Users\sergen\Desktop\jarvis-mission-control"
$python = "python.exe"
$script = "server\agent_os\autopilot_runner.py"
$pidFile = Join-Path $root "server\agent_workspace\approval_state\autopilot.pid"

if (Test-Path $pidFile) {
  $existing = Get-Content $pidFile -ErrorAction SilentlyContinue
  if ($existing) {
    try {
      Get-Process -Id ([int]$existing) -ErrorAction Stop | Out-Null
      Write-Output "JARVIS autopilot zaten calisiyor."
      exit 0
    } catch {}
  }
}

Start-Process -FilePath $python -ArgumentList $script -WorkingDirectory $root -WindowStyle Hidden
Write-Output "JARVIS autopilot started in background."
