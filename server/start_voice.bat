@echo off
title Jarvis Sesli Asistan
echo ============================================
echo   Jarvis Sesli Asistan v1.0 (Pinokio)
echo ============================================
cd /d "%~dp0"

REM Python kontrolü (Pinokio)
set PYTHON=c:\pinokio\bin\miniconda\python.exe
if not exist "%PYTHON%" (
    REM Sistem Python'u dene
    where python >nul 2>&1
    if errorlevel 1 (
        echo HATA: Python bulunamadi!
        pause
        exit /b 1
    )
    set PYTHON=python
)

REM Paket kontrolü
echo Bagimliliklar kontrol ediliyor...
%PYTHON% -c "import sounddevice, faster_whisper, pyttsx3" 2>nul
if errorlevel 1 (
    echo Gerekli paketler kuruluyor...
    %PYTHON% -m pip install sounddevice numpy faster-whisper pyttsx3 --quiet
)

echo.
echo Ollama'nin acik oldugunu kontrol et: http://127.0.0.1:11434
echo.
echo Jarvis sesli asistan baslatiliyor...
echo.
%PYTHON% voice_jarvis.py
pause
