@echo off
title Jarvis Sesli Asistan
echo ============================================
echo   Jarvis Sesli Asistan v1.0
echo ============================================
cd /d "%~dp0"

REM Python
set PYTHON=C:\Program Files\Python311\python.exe
if not exist "%PYTHON%" set PYTHON=python

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
