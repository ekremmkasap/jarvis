@echo off
echo ============================================
echo   Jarvis Mission Control v2.2 (Pinokio)
echo ============================================
cd /d "%~dp0"

REM Python path kontrolü
where python >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadi!
    pause
    exit /b 1
)

REM .env kontrolü
if not exist ".env" (
    echo UYARI: .env dosyasi bulunamadi!
    echo .env.example'dan kopyalanıyor...
    if exist ".env.example" copy ".env.example" ".env"
)

echo Jarvis baslatiliyor...
echo Web: http://127.0.0.1:8080
echo Durdurmak icin Ctrl+C
echo.
python bridge.py
pause
