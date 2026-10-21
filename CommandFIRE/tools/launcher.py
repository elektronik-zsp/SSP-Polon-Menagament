"""No-install, single-instance Windows launcher for CommandFIRE SSP Serwis portable.

The GUI wrapper (.vbs) hides its own console. The long-running HTTP server is
spawned without a console and controlled only through a per-user random token.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = hashlib.sha256(os.path.normcase(os.path.abspath(ROOT)).encode('utf-8')).hexdigest()[:20]
if os.environ.get('SSP_LAUNCHER_STATE_DIR'):
    STATE_BASE = Path(os.environ['SSP_LAUNCHER_STATE_DIR'])
elif os.environ.get('LOCALAPPDATA'):
    STATE_BASE = Path(os.environ['LOCALAPPDATA']) / 'SSP-Polon'
else:
    STATE_BASE = Path.home() / '.local' / 'state' / 'SSP-Polon'
STATE_DIR = STATE_BASE / IDENTITY
STATE_FILE = STATE_DIR / 'instance.json'
LOG_FILE = STATE_DIR / 'server.log'
LOCK_FILE = STATE_DIR / 'launcher.lock'


def alert(message, error=False):
    if os.name == 'nt':
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(message), 'CommandFIRE SSP Serwis', 0x10 if error else 0x40)
    else:
        print(message, file=sys.stderr if error else sys.stdout)



def confirm_stop(count):
    if os.name != 'nt':
        return True
    import ctypes
    message = (f'W tej aplikacji aktywne są {count} formularze edycji.\n'
               'Zapisz pracę i zamknij formularze przed zatrzymaniem serwera.\n'
               'Niezapisane dane w przeglądarce zostaną utracone.\n\n'
               'Czy mimo to zatrzymać CommandFIRE SSP Serwis?')
    return ctypes.windll.user32.MessageBoxW(None, message, 'CommandFIRE SSP Serwis — uwaga', 0x24) == 6

def read_port():
    config = ROOT / 'config.json'
    data = json.loads(config.read_text(encoding='utf-8-sig')) if config.exists() else {}
    port = data.get('port', 8765)
    if type(port) is not int or not (1 <= port <= 65535):
        raise ValueError('Nieprawidłowy numer portu w config.json (wymagane 1–65535).')
    return port


def save_state(data):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=STATE_DIR, prefix='instance-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(data, stream)
        os.replace(name, STATE_FILE)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_state():
    try:
        value = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        if value.get('root') != str(ROOT) or not isinstance(value.get('token'), str):
            return None
        return value
    except (OSError, ValueError, TypeError, AttributeError):
        return None


@contextmanager
def launcher_lock():
    """Serializes two double-clicks before either can spawn a server."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, 'a+b') as file:
        file.seek(0, os.SEEK_END)
        if file.tell() == 0:
            file.write(b'1')
            file.flush()
        for attempt in range(80):
            try:
                file.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if attempt == 79:
                    raise RuntimeError('Inne uruchomienie aplikacji trwa zbyt długo.')
                time.sleep(.1)
        try:
            yield
        finally:
            file.seek(0)
            if os.name == 'nt':
                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(file.fileno(), fcntl.LOCK_UN)


def request_control(state, action='status'):
    if not state or type(state.get('port')) is not int:
        return None
    if not (1 <= state['port'] <= 65535):
        return None
    url = f"http://127.0.0.1:{state['port']}/__control/{action}"
    req = urllib.request.Request(url, method='POST' if action == 'stop' else 'GET',
                                 headers={'X-SSP-Control': state['token']})
    try:
        with urllib.request.urlopen(req, timeout=1.2) as response:
            answer = json.load(response)
        if action == 'status':
            if (answer.get('root') != str(ROOT) or answer.get('port') != state['port']
                    or answer.get('pid') != state.get('pid')):
                return None
        return answer
    except (OSError, ValueError, urllib.error.HTTPError):
        return None


def available(port):
    with socket.socket() as sock:
        sock.settimeout(.35)
        return sock.connect_ex(('127.0.0.1', port)) != 0


def check_database(port, control_token=None, timeout=5):
    try:
        req=urllib.request.Request(f'http://127.0.0.1:{port}/__control/database-health',
                                 headers={'X-SSP-Control': control_token or ''})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            json.load(response)
        return None
    except urllib.error.HTTPError as exc:
        try:
            error = json.loads(exc.read().decode('utf-8')).get('error', str(exc))
        except (OSError, ValueError):
            error = str(exc)
        return error
    except (OSError, ValueError) as exc:
        return str(exc)


def browser(port):
    url = f'http://127.0.0.1:{port}'
    if os.name == 'nt':
        os.startfile(url)
    else:
        webbrowser.open(url)


def last_log_lines(count=12):
    try:
        lines = LOG_FILE.read_text(encoding='utf-8', errors='replace').splitlines()
        return '\n'.join(lines[-count:])[-1400:]
    except OSError:
        return 'Brak pliku dziennika.'


def start():
    port = read_port()
    python = ROOT / 'runtime' / 'python.exe'
    if not python.is_file():
        raise RuntimeError('Nie znaleziono runtime\\python.exe w folderze programu.')
    state = read_state()
    if state and request_control(state):
        if state['port'] != port:
            raise RuntimeError('Zmieniono port w config.json. Najpierw zatrzymaj uruchomioną aplikację.')
        browser(state['port'])
        return
    if not available(port):
        raise RuntimeError(f'Port {port} jest już zajęty. Może działać starsza wersja CommandFIRE SSP Serwis '\
                           'lub inny program. Nie zatrzymuję obcego procesu. '\
                           'Zamknij poprzednią wersję albo ustaw inny port w config.json.')

    if LOG_FILE.exists() and LOG_FILE.stat().st_size > 2 * 1024 * 1024:
        previous = LOG_FILE.with_name('server.previous.log')
        os.replace(LOG_FILE, previous)
    token = secrets.token_hex(32)
    environ = os.environ.copy()
    environ['SSP_CONTROL_TOKEN'] = token
    new_state = {'port': port, 'root': str(ROOT), 'token': token,
                 'startedAt': datetime.now().isoformat(timespec='seconds'), 'pid': 0}
    save_state(new_state)
    creationflags = (subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    try:
        with open(LOG_FILE, 'ab') as log:
            log.write((f'\n===== Start {new_state["startedAt"]} =====\n').encode('utf-8'))
            log.flush()
            process = subprocess.Popen(
                [str(python), '-I', '-B', '-u', str(ROOT / 'server.py'), '--no-browser', '--port', str(port)],
                cwd=str(ROOT), env=environ, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=creationflags, close_fds=True)
        new_state['pid'] = process.pid
        save_state(new_state)
        for attempt in range(75):
            if process.poll() is not None:
                raise RuntimeError('Serwer zakończył pracę podczas uruchamiania.\n\n' + last_log_lines())
            if request_control(new_state):
                problem = check_database(port, new_state['token'])
                if problem:
                    request_control(new_state, 'stop')
                    raise RuntimeError('Nie można odczytać wspólnej bazy:\n' + problem +
                                       '\n\nSprawdź połączenie i uprawnienia do udziału sieciowego.')
                browser(port)
                return
            time.sleep(.12)
        raise RuntimeError('Serwer nie odpowiedział po uruchomieniu. Sprawdź dziennik:\n' + str(LOG_FILE))
    except Exception:
        if request_control(new_state):
            request_control(new_state, 'stop')
        raise


def stop(announce=True):
    state = read_state()
    if not state or not request_control(state):
        if announce:
            alert('Nie wykryto uruchomionego CommandFIRE SSP Serwis z tej instalacji.\n'
                  'Jeśli port jest zajęty, sprawdź, czy nie działa starsza wersja programu.')
        return
    active = request_control(state)
    if active and active.get('localEditors', 0) > 0 and not confirm_stop(active['localEditors']):
        return
    if request_control(state, 'stop') is None:
        raise RuntimeError('Nie udało się wysłać polecenia zatrzymania.\nDziennik: ' + str(LOG_FILE))
    for _ in range(40):
        if not request_control(state):
            if announce:
                alert('Serwer CommandFIRE SSP Serwis został zatrzymany. Możesz zamknąć przeglądarkę.')
            return
        time.sleep(.1)
    raise RuntimeError('Serwer nie potwierdził zatrzymania. Sprawdź status i dziennik.')


def status():
    state = read_state()
    active = request_control(state) if state else None
    if active:
        problem = check_database(state['port'], state['token'])
        message = ('CommandFIRE SSP Serwis działa w tle.\n'
                   f'Wersja: {active.get("version")}\nPort: {state["port"]}\n'
                   + ('Wspólna baza: odczyt prawidłowy.' if not problem
                      else 'UWAGA: Błąd wspólnej bazy:\n' + problem))
    else:
        message = ('CommandFIRE SSP Serwis nie działa w tle z tego folderu.\n'
                   f'Dziennik: {LOG_FILE}')
    alert(message, error=bool(active and problem))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    args = parser.parse_args()
    try:
        with launcher_lock():
            {'start': start, 'stop': stop, 'status': status}[args.action]()
    except (OSError, ValueError, RuntimeError) as error:
        alert(str(error) + '\n\nDziennik: ' + str(LOG_FILE), error=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
