@echo off
setlocal
cd /d "%~dp0"

set "OPENCLAW_CLI=%APPDATA%\npm\openclaw.cmd"
if not exist "%OPENCLAW_CLI%" (
  echo ERROR: Global OpenClaw CLI not found at:
  echo %OPENCLAW_CLI%
  pause
  exit /b 1
)

echo Opening OpenClaw dashboard...
"%OPENCLAW_CLI%" dashboard
