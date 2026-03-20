@echo off
echo Jarvis durduruluyor...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *bridge*" 2>nul
taskkill /F /IM pythonw.exe 2>nul
wmic process where "commandline like '%%bridge.py%%'" delete 2>nul
timeout /t 3 /nobreak >nul

echo Jarvis baslatiliyor...
cd /d "C:\Users\sergen\Desktop\jarvis-mission-control\server"
start pythonw bridge.py

timeout /t 4 /nobreak >nul
echo.
echo Tamam! Telegram'dan /kabul yaz, buton cikacak.
pause
