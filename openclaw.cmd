@echo off
title Jarvis — OpenClaw Gateway
echo ============================================
echo   Jarvis OpenClaw Gateway (Pinokio)
echo ============================================
cd /d "%~dp0"

set PYTHON=c:\pinokio\bin\miniconda\python.exe
if not exist "%PYTHON%" set PYTHON=python

echo Baslatiyor: server\openclaw\bridge.py
echo Web: http://127.0.0.1:8080
echo.
%PYTHON% "server\openclaw\bridge.py"
pause
