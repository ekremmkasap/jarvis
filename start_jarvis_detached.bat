@echo off
title Jarvis Mission Control Detached
cd /d "%~dp0"

set PYTHON=python
where %PYTHON% >nul 2>&1
if errorlevel 1 (
  echo HATA: Python bulunamadi.
  pause
  exit /b 1
)

echo Jarvis arka planda baslatiliyor...
start "Jarvis Mission Control" /min %PYTHON% ".\server\bridge.py"
timeout /t 5 >nul
echo Web: http://127.0.0.1:8081
echo Audit: .\server\logs\team_audit.jsonl
echo Durdurmak icin Gorev Yonetici veya Stop-Process kullan.
