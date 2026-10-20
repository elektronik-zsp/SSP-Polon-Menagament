@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
if not exist "%~dp0runtime\python.exe" (
    echo Brak folderu runtime. Rozpakuj cala paczke ZIP przed uruchomieniem.
    pause
    exit /b 1
)
"%~dp0runtime\python.exe" -I -B "%~dp0server.py"
if errorlevel 1 (
    echo Aplikacja nie zostala uruchomiona. Szczegoly bledu sa powyzej.
    pause
)
