@echo off
setlocal
cd /d "%~dp0"

set "OPENCLAW_CLI=%APPDATA%\npm\openclaw.cmd"
set "OPENCLAW_HOST=127.0.0.1"
set "OPENCLAW_PORT=18789"

if not exist "%OPENCLAW_CLI%" (
  echo ERROR: Global OpenClaw CLI not found at:
  echo %OPENCLAW_CLI%
  exit /b 1
)

rem Avoid duplicate gateway boots during Windows startup or launcher overlap.
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$client = $null; try { $client = New-Object Net.Sockets.TcpClient; $iar = $client.BeginConnect('%OPENCLAW_HOST%', %OPENCLAW_PORT%, $null, $null); if ($iar.AsyncWaitHandle.WaitOne(700, $false) -and $client.Connected) { $client.EndConnect($iar) | Out-Null; exit 0 } else { exit 1 } } catch { exit 1 } finally { if ($client) { $client.Close() } }"

if not errorlevel 1 (
  echo OpenClaw gateway already reachable at http://%OPENCLAW_HOST%:%OPENCLAW_PORT%/
  exit /b 0
)

"%OPENCLAW_CLI%" gateway --force
exit /b %ERRORLEVEL%
