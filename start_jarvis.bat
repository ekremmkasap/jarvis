@echo off
title Jarvis Mission Control
color 0A

echo ============================================
echo   JARVIS MISSION CONTROL - Standalone Desktop Edition
echo ============================================
echo.

:: Python yolunu bul (Pinokio python tercih et)
set PYTHON=C:\Users\sergen\AppData\Roaming\uv\python\cpython-3.14-windows-x86_64-none\python.exe
if not exist "%PYTHON%" set PYTHON=python

echo [*] Python: %PYTHON%
echo [*] Bridge baslatiliyor...
echo.

:: pyautogui yoksa kur
%PYTHON% -c "import pyautogui" 2>nul || (
    echo [*] pyautogui kuruluyor...
    %PYTHON% -m pip install pyautogui -q
)

:: Jarvis'i baslat
%PYTHON% "C:\Users\sergen\Desktop\jarvis-mission-control\server\bridge.py"

echo.
echo [!] Jarvis durdu. Kapatmak icin bir tusa basin...
pause
