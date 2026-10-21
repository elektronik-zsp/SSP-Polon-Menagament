@echo off
cd /d "%~dp0"
"runtime\python.exe" -B -c "from cryptography.hazmat.primitives.ciphers.aead import AESGCM; import cffi; print('AES-GCM OK; cffi OK')"
if errorlevel 1 (echo BLAD: NIE URUCHAMIAJ MIGRACJI. ) else (echo Moduly zaladowane. )
pause
