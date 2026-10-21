@echo off
setlocal
chcp 65001 >nul
pushd "%~dp0"
if not exist "%~dp0runtime\python.exe" (
    echo Brak runtime\python.exe - zachowaj runtime z lokalnej wersji portable.
    pause
    exit /b 1
)
"%~dp0runtime\python.exe" -I -B "%~dp0tools\konfiguruj_baze.py"
if errorlevel 1 ( echo Nie skonfigurowano wspolnej bazy. )
pause
popd
