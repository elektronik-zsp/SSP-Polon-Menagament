@echo off
cd /d "%~dp0"
"runtime\python.exe" -B "tools\diagnostyka_cfdb.py"
echo.
pause
