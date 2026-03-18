@echo off
setlocal
cd /d "%~dp0"
python "server\openclaw\bridge.py" --web-only
