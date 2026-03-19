@echo off
echo ============================================
echo   Jarvis bridge.py Guncelleme + Restart
echo ============================================

echo [1/2] bridge.py kopyalaniyor...
copy /Y "C:\Users\sergen\Desktop\jarvis-mission-control\server\bridge.py" "C:\Users\sergen\Desktop\jarvis-mission-control\server\bridge.py.bak" >nul
echo Yedek alindi.

echo [2/2] Pinokio'dan manuel restart gerekiyor.
echo.
echo Dosyalar guncellendi. Simdi Pinokio'dan
echo Jarvis servisini restart edin.
echo.
echo Yeni komutlar:
echo   /kabul  - AnyDesk baglanti istegini kabul et
echo   /cmd    - Terminal komutu calistir
echo ============================================
pause
