@echo off
echo ============================================
echo   Jarvis Restart (Pinokio'suz)
echo ============================================

echo [1/3] Calisan bridge.py durduruluyor...
wmic process where "commandline like '%%bridge.py%%'" delete >nul 2>&1
taskkill /F /FI "COMMANDLINE eq python bridge.py" >nul 2>&1
timeout /t 2 /nobreak >nul
echo OK

echo [2/3] Yeni bridge.py baslatiliyor...
cd /d "C:\Users\sergen\Desktop\jarvis-mission-control\server"
start /B pythonw bridge.py

timeout /t 4 /nobreak >nul
echo OK

echo [3/3] Kontrol ediliyor...
wmic process where "commandline like '%%bridge.py%%'" get processid,commandline 2>nul | findstr bridge

echo.
echo ============================================
echo   Hazir! Telegram'dan /kabul test edin.
echo ============================================
pause
