@echo off
title JARVIS — Sesli Asistan
color 0A
echo.
echo  ============================================
echo    J A R V I S  —  Sesli AI Asistan
echo  ============================================
echo.

:: Python kontrol
"C:\Program Files\Python311\python.exe" --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi: C:\Program Files\Python311\python.exe
    pause
    exit /b 1
)

:: Ollama kontrol
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [UYARI] Ollama calismıyor! Lutfen Ollama'yi baslatin.
    echo         http://ollama.ai adresinden indirip calistirin.
    pause
    exit /b 1
)

echo  [OK] Python ve Ollama hazir
echo  [OK] Mikrofon: Logitech G733 ^(device 9^)
echo  [OK] Model: minimax-m2.7:cloud
echo.
echo  Baslatiliyor... ^(kapatmak icin Ctrl+C^)
echo.

cd /d "%~dp0"
"C:\Program Files\Python311\python.exe" hey_jarvis.py

echo.
echo [!] Jarvis kapandı.
pause
