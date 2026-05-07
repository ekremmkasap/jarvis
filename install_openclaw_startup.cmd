@echo off
setlocal
cd /d "%~dp0"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%STARTUP%\openclaw_autostart.cmd"
set "LAUNCHER=%~dp0openclaw_gateway_start.cmd"

if not exist "%LAUNCHER%" (
  echo ERROR: Launcher not found:
  echo %LAUNCHER%
  exit /b 1
)

(
  echo @echo off
  echo cd /d "%~dp0"
  echo start "OpenClaw" /min cmd /c call "%LAUNCHER%"
) > "%TARGET%"

echo Kurulum tamamlandi: %TARGET%
echo Sonraki oturum acilisinda OpenClaw otomatik baslayacak.
