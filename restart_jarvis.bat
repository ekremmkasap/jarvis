@echo off
echo Eski Jarvis servisleri kapatiliyor...
wmic process where "commandline like '%%bridge.py%%' and name='python.exe'" call terminate >nul 2>&1

echo Yeni Jarvis servisi baslatiliyor...
cd /d "C:\Users\sergen\Desktop\jarvis-mission-control\server"
start "Jarvis-Bridge" python bridge.py

echo.
echo Islem tamam! Pinokio disinda Jarvis yeniden baslatildi.
echo Simdi Telegram uzerinden "anydesk istegini onayla" diyerek test edebilirsiniz.
pause
