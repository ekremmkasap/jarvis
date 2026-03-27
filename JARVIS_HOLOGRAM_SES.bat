@echo off
title Jarvis - Tam Sistem
color 0A
echo.
echo  ============================================
echo    J A R V I S   TAM SISTEM BASLATIYOR
echo    Bridge + Hologram + Voice
echo  ============================================
echo.

cd /d "%~dp0"

echo [1/3] Bridge baslatiliyor (arka planda)...
start /B "Jarvis Bridge" "C:\Program Files\Python311\python.exe" server\bridge.py

timeout /t 3 /nobreak > NUL

echo [2/3] Desktop Hologram baslatiliyor...
start "Jarvis Hologram" "%~dp0start_desktop_hologram.bat"

timeout /t 2 /nobreak > NUL

echo [3/3] Voice Service baslatiliyor...
"C:\Program Files\Python311\python.exe" services\voice\voice_service.py

echo.
echo [!] Voice service kapandi.
pause
