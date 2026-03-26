@echo off
title Jarvis Mission Control v2.0

echo.
echo  ============================================
echo   JARVIS MISSION CONTROL v2.0 - STARTING
echo  ============================================
echo.

cd /d "%~dp0"

:: Create required directories
if not exist "memory" mkdir memory
if not exist "outputs\reports" mkdir outputs\reports
if not exist "outputs\summaries" mkdir outputs\summaries
if not exist "logs" mkdir logs

:: Start Orchestrator
echo [1/3] Starting Orchestrator on :8090...
start "Jarvis Orchestrator" cmd /k "python -m services.orchestrator.main 2>>logs\orchestrator.log"
timeout /t 3 /nobreak >nul

:: Start GitHub Worker (if token set)
echo [2/3] Starting GitHub Worker...
start "Jarvis GitHub Worker" cmd /k "python services/github-worker/worker.py 2>>logs\github_worker.log"
timeout /t 2 /nobreak >nul

:: Start Voice Service
echo [3/3] Starting Voice Service...
start "Jarvis Voice" cmd /k "python services/voice/voice_service.py 2>>logs\voice.log"

echo.
echo  ============================================
echo   All services started!
echo   Orchestrator: http://localhost:8091
echo   Dashboard:    cd apps\web-ui ^& npm run dev
echo   Health:       http://localhost:8090/health
echo  ============================================
echo.

pause
