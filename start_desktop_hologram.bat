@echo off
title Jarvis Desktop Hologram
color 0B
echo.
echo  ========================================
echo    J A R V I S   H O L O G R A M
echo  ========================================
echo.

cd /d "%~dp0apps\desktop-hologram"

if not exist node_modules (
    echo [*] node_modules bulunamadi, npm install baslatiliyor...
    npm install
)

echo [OK] Hologram baslatiliyor...
npm start
