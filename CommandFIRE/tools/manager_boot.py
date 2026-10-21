"""Visible startup diagnostics for the portable CommandFIRE SSP Serwis tray manager.

Run this file via pythonw.exe (or console-less python.exe) and -I -B.
If importing/starting manager fails, show a Windows error dialog and save a
traceback under LOCALAPPDATA. No dependencies or installation are required.
"""
from __future__ import annotations

import ctypes
from datetime import datetime
import hashlib
import os
from pathlib import Path
import sys
import traceback

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
IDENTITY = hashlib.sha256(os.path.normcase(os.path.abspath(ROOT)).encode('utf-8')).hexdigest()[:20]
if os.environ.get('SSP_LAUNCHER_STATE_DIR'):
    BASE = Path(os.environ['SSP_LAUNCHER_STATE_DIR'])
elif os.environ.get('LOCALAPPDATA'):
    BASE = Path(os.environ['LOCALAPPDATA']) / 'SSP-Polon'
else:
    BASE = Path.home() / '.local' / 'state' / 'SSP-Polon'
LOG = BASE / IDENTITY / 'manager.log'


def report_startup_error(exc: BaseException) -> None:
    detail = traceback.format_exc()
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open('a', encoding='utf-8') as f:
            f.write('\n===== Manager startup ' + datetime.now().isoformat(timespec='seconds') + ' =====\n')
            f.write(detail)
            f.write('\n')
    except OSError:
        pass

    message = ('Nie mozna uruchomic menedzera CommandFIRE SSP Serwis.\n\n'
               + type(exc).__name__ + ': ' + str(exc)[:500]
               + '\n\nDziennik bledow:\n' + str(LOG)
               + '\n\nJesli problem pozostaje, uruchom Diagnoza_Menedzera.bat.')
    if os.name == 'nt':
        try:
            ctypes.windll.user32.MessageBoxW(None, message, 'CommandFIRE SSP Serwis - blad uruchamiania', 0x10)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)
    print(detail, file=sys.stderr)


def main():
    try:
        sys.path.insert(0, str(TOOLS))  # -I removes script's folder from sys.path
        os.environ['SSP_MANAGER_BOOTSTRAP'] = '1'
        import manager
        manager.main()
    except (Exception, KeyboardInterrupt) as exc:
        report_startup_error(exc)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
