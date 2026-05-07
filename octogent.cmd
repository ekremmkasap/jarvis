@echo off
setlocal
title Jarvis - Octogent Runtime
echo ============================================
echo   Jarvis Octogent Runtime
echo ============================================
cd /d "%~dp0"

set "OCTOGENT_CLI=%APPDATA%\npm\octogent.cmd"
if not exist "%OCTOGENT_CLI%" (
  echo ERROR: Global Octogent CLI not found at:
  echo %OCTOGENT_CLI%
  echo.
  echo Expected bootstrap:
  echo   cd external-repos\octogent
  echo   cmd /c pnpm install
  echo   cmd /c pnpm build
  echo   npm install -g .
  echo.
  echo After install, re-run this launcher.
  pause
  exit /b 1
)

if "%~1"=="" (
  echo Starting Octogent dashboard for current project...
  set "OCTOGENT_NO_OPEN=1"
  "%OCTOGENT_CLI%"
) else (
  "%OCTOGENT_CLI%" %*
)
pause
