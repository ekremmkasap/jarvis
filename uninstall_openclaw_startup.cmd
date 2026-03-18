@echo off
setlocal

set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%STARTUP%\openclaw_autostart.cmd"

if exist "%TARGET%" (
  del "%TARGET%"
  echo Kaldirildi: %TARGET%
) else (
  echo Startup kaydi bulunamadi.
)
