@echo off
cd /d "%~dp0"
if exist "runtime\python.exe" (
 "runtime\python.exe" -B "tools\cfdb_setup.py"
) else (
 py -3 "tools\cfdb_setup.py"
)
pause
