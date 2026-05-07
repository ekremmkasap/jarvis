@echo off
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0jarvis-subagent-cli.ps1" ps51 -Task %*
