@echo off
setlocal
cd /d "%~dp0"
title CommandFIRE SSP Serwis - diagnostyka menedzera
if not exist "%~dp0runtime\python.exe" (
  echo BLAD: brak runtime\python.exe
  echo Uruchom ten plik z lokalnego folderu SSP-Polon, w ktorym jest runtime.
  pause
  exit /b 1
)
if not exist "%~dp0tools\manager_boot.py" (
  echo BLAD: brak tools\manager_boot.py
  pause
  exit /b 1
)
echo Uruchamianie menedzera w trybie diagnostycznym...
echo Jesli pojawi sie okno menedzera, start jest poprawny.
echo Konsola pozostanie otwarta do czasu zamkniecia menedzera z menu tray.
echo.
"%~dp0runtime\python.exe" -I -B "%~dp0tools\manager_boot.py"
echo.
echo Menedzer zakonczyl dzialanie. Kod wyjscia: %errorlevel%
echo Log bledu: %%LOCALAPPDATA%%\SSP-Polon\[id instalacji]\manager.log
pause
