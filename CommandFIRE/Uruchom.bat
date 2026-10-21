@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0tools\manager_boot.py" (
  echo Brak tools\manager_boot.py. Wgraj poprawke 2.4.3.
  pause
  exit /b 1
)
if exist "%~dp0runtime\pythonw.exe" (
  start "" "%~dp0runtime\pythonw.exe" -I -B "%~dp0tools\manager_boot.py"
  exit /b 0
)
rem VBS hides the console if the portable runtime does not include pythonw.exe.
wscript.exe "%~dp0SSP_Polon_Manager.vbs"
if errorlevel 1 (
  echo Windows zablokowal skrypt VBS. Uruchom Diagnoza_Menedzera.bat.
  pause
)
