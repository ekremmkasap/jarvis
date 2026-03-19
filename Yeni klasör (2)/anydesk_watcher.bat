@echo off
:: anydesk_watcher.bat
:: Arka planda çalışır. Claude veya Telegram /kabul dediğinde
:: masaüstüne .anydesk_trigger dosyası bırakılır, bu bat onu algılar ve AnyDesk'i kabul eder.
:: Bilgisayar açılınca bir kez çalıştırın — arka planda bekler.

echo ============================================
echo   Jarvis AnyDesk Watcher - Aktif
echo   Claude veya Telegram'dan /kabul veya
echo   "onayla / kabul et" yazin.
echo   Durdurmak icin bu pencereyi kapatin.
echo ============================================
echo.

:loop
if exist "%USERPROFILE%\Desktop\.anydesk_trigger" (
    echo [%time%] Trigger alindi! AnyDesk kabul ediliyor...
    del "%USERPROFILE%\Desktop\.anydesk_trigger" >nul 2>&1
    powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "%USERPROFILE%\Desktop\anydesk_kabul.ps1"
    echo [%time%] Islem tamamlandi.
    echo.
)
timeout /t 1 /nobreak >nul
goto loop
