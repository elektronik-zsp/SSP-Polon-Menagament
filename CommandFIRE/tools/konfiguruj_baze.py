"""Wskazuje wspolny plik bazy w lokalnym config.json. Bez instalacji pakietow."""
from pathlib import Path
import json
import os
import sys
import tempfile

APP = Path(__file__).resolve().parent.parent
CONFIG = APP / 'config.json'
DEFAULT_NAME = 'db_polon_ssp.json'
# Reuse precisely the same cross-computer SMB lock as the running application.
sys.path.insert(0, str(APP))
from server import database_mutex


def write_atomic(path, data):
    fd, temporary = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    print('CommandFIRE SSP Serwis 2.5.2 - wskazanie wspolnej bazy danych')
    print('Program oraz config.json pozostaja na tym komputerze.')
    print('Podaj sciezke UNC, np. \\\\KOMPUTER-ZSP\\Serwis\\db_polon_ssp.json')
    print('Mozesz takze podac litere dysku, np. Z:\\Serwis\\db_polon_ssp.json')
    value = input('Pelna sciezka do wspolnego pliku JSON: ').strip().strip('"')
    target = Path(value)
    if not value or not target.is_absolute() or target.suffix.lower() != '.json' or target.name.lower() == 'config.json':
        raise ValueError('Podaj bezwzgledna sciezke do pliku *.json.')
    if not target.parent.is_dir():
        raise OSError('Folder nie istnieje lub nie masz do niego dostepu: ' + str(target.parent))
    config = json.loads(CONFIG.read_text(encoding='utf-8-sig')) if CONFIG.exists() else {}
    old_location = Path(config.get('database', DEFAULT_NAME))
    if not old_location.is_absolute():
        old_location = APP / old_location
    initial_contents = None
    if not target.exists():
        print('Nie znaleziono pliku bazy w udziale. To bedzie pierwsza kopia.')
        if old_location.is_file():
            contents = old_location.read_bytes()
            db = json.loads(contents.decode('utf-16' if contents.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'))
            if not isinstance(db, dict) or not all(isinstance(db.get(x), list) for x in ('panels','faults','history')):
                raise ValueError('Lokalny plik nie jest baza CommandFIRE SSP Serwis.')
        else:
            db={'panels': [], 'faults': [], 'history': [], 'schemaVersion': 3, 'audit': []}
        db.setdefault('serviceConfig', config.get('service', {}))
        print('Utworze baze w udziale z lokalnych danych tego komputera.')
        if input('Potwierdz przez wpisanie TAK: ').strip() != 'TAK':
            print('Anulowano.');return
        initial_contents = json.dumps(db, ensure_ascii=False, indent=2).encode('utf-8')
    # The shared mutex prevents a second configurator from racing against
    # first creation. The file appears atomically, never half-copied.
    with database_mutex(target):
        if not target.exists():
            if initial_contents is None:
                raise OSError('Baza zniknela z udzialu. Uruchom konfigurator ponownie.')
            write_atomic(target, initial_contents)
        existing=target.read_bytes()
        db=json.loads(existing.decode('utf-16' if existing.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'))
        if not isinstance(db,dict) or not all(isinstance(db.get(x), list) for x in ('panels','faults','history')):
            raise ValueError('Udostepniony plik nie jest poprawna baza SSP.')
        if 'serviceConfig' not in db:
            print('Plik nie posiada jeszcze wspolnej konfiguracji serwisu.')
            print('Zapisz ustawienia firmy z panelu Konfiguracja po uruchomieniu.')
    # We need create/mutate/delete permission for atomic saves and SMB lock file.
    probe=target.parent/('ssp-test-'+str(os.getpid())+'.tmp')
    try:
        probe.write_bytes(b'test')
        probe.unlink()
    except OSError as error:
        raise OSError('Wymagane uprawnienie modyfikacji plikow w folderze sieciowym: '+str(error))
    original=CONFIG.read_bytes() if CONFIG.exists() else None
    if original:
        write_atomic(APP/'config.json.before-shared.bak', original)
    config['database']=str(target)
    config.setdefault('port',8765)
    config.setdefault('open_browser',True)
    write_atomic(CONFIG,json.dumps(config, ensure_ascii=False, indent=2).encode('utf-8'))
    print('Gotowe. Program lokalny uzywa wspolnej bazy: '+str(target))
    print('Skonfiguruj IDENTYCZNA sciezke na pozostalych komputerach.')
    print('Nie uruchamiaj starszych wersji CommandFIRE SSP Serwis ze wspolnej bazy.')


if __name__ == '__main__':
    try:main()
    except (ValueError,OSError,UnicodeError) as exc:
        print('BLAD: '+str(exc))
        sys.exit(1)
