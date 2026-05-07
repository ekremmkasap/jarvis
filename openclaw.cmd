@echo off
setlocal
title Jarvis - OpenClaw Gateway
echo ============================================
echo   Jarvis OpenClaw Gateway
echo ============================================
cd /d "%~dp0"

set "OPENCLAW_CLI=%APPDATA%\npm\openclaw.cmd"
if not exist "%OPENCLAW_CLI%" (
  echo ERROR: Global OpenClaw CLI not found at:
  echo %OPENCLAW_CLI%
  echo.
  echo Install or repair OpenClaw first, then run this launcher again.
  pause
  exit /b 1
)

echo Baslatiyor: openclaw gateway --force
echo Dashboard: http://127.0.0.1:18789/
echo.
"%OPENCLAW_CLI%" gateway --force
pause
