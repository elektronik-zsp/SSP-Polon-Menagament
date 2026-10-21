@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0runtime\python.exe" (
  "%~dp0runtime\python.exe" -B "%~dp0tools\utworz_admina.py"
) else (
  py -3 "%~dp0tools\utworz_admina.py"
)
echo.
pause
