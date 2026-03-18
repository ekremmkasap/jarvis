@echo off
setlocal
cd /d "%~dp0"

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%STARTUP%\openclaw_autostart.cmd"

(
  echo @echo off
  echo cd /d "%~dp0"
  echo start "OpenClaw" /min cmd /c python "server\openclaw\bridge.py" --web-only
) > "%TARGET%"

echo Kurulum tamamlandi: %TARGET%
echo Sonraki oturum acilisinda OpenClaw otomatik baslayacak.
