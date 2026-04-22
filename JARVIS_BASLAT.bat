@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title JARVIS Mission Control

set "REPO=%~dp0"
if "%REPO:~-1%"=="\" set "REPO=%REPO:~0,-1%"

set "PYTHON=C:\Program Files\Python311\python.exe"
if not exist "%PYTHON%" (
    for /f "delims=" %%i in ('where python 2^>nul') do (
        if "!PYTHON_FOUND!"=="" set "PYTHON=%%i" & set "PYTHON_FOUND=1"
    )
)
if not exist "%PYTHON%" set "PYTHON=python"

set "OBSIDIAN_VAULT_PATH=%REPO%\wiki"
set "JARVIS_OBSIDIAN_AUTO_OPEN=1"
set "JARVIS_WAIT_FOR_GATEWAY=0"
if not defined JARVIS_ENABLE_HOLOGRAM set "JARVIS_ENABLE_HOLOGRAM=1"
if not defined JARVIS_SWARM_HOLOGRAM set "JARVIS_SWARM_HOLOGRAM=0"
if not defined JARVIS_WEB_ONLY set "JARVIS_WEB_ONLY=0"
if not defined JARVIS_OPEN_MIC set "JARVIS_OPEN_MIC=1"
if not defined JARVIS_VOICE_RUNTIME set "JARVIS_VOICE_RUNTIME=mark_xxxv"
set "JARVIS_LAUNCHER_ENTRY=%~f0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUNBUFFERED=1"

cls
echo.
echo  ================================================
echo   JARVIS - REPO CANONICAL LAUNCHER
echo  ================================================
echo   Repo     : %REPO%
echo   Vault    : %OBSIDIAN_VAULT_PATH%
echo   Voice    : %JARVIS_VOICE_RUNTIME%
echo   Mic      : Acik mikrofon aktif
echo   Hologram : %JARVIS_ENABLE_HOLOGRAM%
echo  ================================================
echo.

cd /d "%REPO%"
if errorlevel 1 (
    echo HATA: Repo klasoru bulunamadi: %REPO%
    pause
    exit /b 1
)
if not exist "%REPO%\master_launcher.py" (
    echo HATA: master_launcher.py bulunamadi.
    pause
    exit /b 1
)

echo Eski Jarvis surecleri temizleniyor...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$targets = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and $_.Name -match '^(python|node|electron)\.exe$' -and ($_.CommandLine -like '*jarvis-mission-control*' -or $_.CommandLine -like '*Mark-XXXV\\main.py*' -or $_.CommandLine -like '*master_launcher.py*') }; foreach ($proc in $targets) { try { Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop } catch {} }" >nul 2>&1
timeout /t 2 >nul

"%PYTHON%" master_launcher.py
set "EXITCODE=%ERRORLEVEL%"
echo.
if not "%EXITCODE%"=="0" echo Launcher exit code: %EXITCODE%
pause
exit /b %EXITCODE%
