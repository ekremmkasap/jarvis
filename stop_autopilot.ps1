$root = "C:\Users\sergen\Desktop\jarvis-mission-control"
$stopFile = Join-Path $root "server\agent_workspace\approval_state\autopilot.stop"
$pidFile = Join-Path $root "server\agent_workspace\approval_state\autopilot.pid"
New-Item -Path $stopFile -ItemType File -Force | Out-Null
if (Test-Path $pidFile) {
  $pidValue = Get-Content $pidFile -ErrorAction SilentlyContinue
  if ($pidValue) {
    try {
      Stop-Process -Id ([int]$pidValue) -Force -ErrorAction Stop
    } catch {}
  }
}
Write-Output "JARVIS autopilot stop signal created."
