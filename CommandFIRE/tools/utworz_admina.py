"""One-time administrator setup, on a trusted local workstation only."""
from pathlib import Path
import sys
import getpass
import json
from copy import deepcopy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from server import DEFAULT_CONFIG, EMPTY_DB, atomic_write, database_mutex, database_codec, validate_database, VERSION
from auth_users import new_user


def main():
    print('CommandFIRE SSP Serwis ' + VERSION + ' — UTWORZENIE PIERWSZEGO ADMINISTRATORA')
    print('Konto zostanie zapisane we wspólnej bazie; nie istnieje hasło domyślne.\n')
    path = ROOT / 'config.json'
    if not path.exists():
        raise ValueError('Brak config.json. Najpierw skonfiguruj ścieżkę do wspólnej bazy.')
    config = json.loads(path.read_text(encoding='utf-8-sig'))
    name = config.get('database', DEFAULT_CONFIG['database'])
    database = Path(name)
    if not database.is_absolute():
        database = ROOT / database
    if not database.parent.is_dir():
        raise ValueError('Folder wspólnej bazy nie istnieje: ' + str(database.parent))
    db_decode, db_encode = database_codec(ROOT, database)
    with database_mutex(database):
        data = db_decode(database.read_bytes()) if database.exists() else validate_database(deepcopy(EMPTY_DB))
        if data['users']:
            print('W bazie istnieją już konta. Użytkownikami zarządza administrator w programie.')
            return
        username = input('Login administratora (min. 3 znaki): ').strip()
        display = input('Imię i nazwisko: ').strip()
        passwd = getpass.getpass('Hasło (12–128 znaków): ')
        confirmation = getpass.getpass('Powtórz hasło: ')
        if passwd != confirmation:
            raise ValueError('Hasła nie są takie same.')
        admin = new_user(username, display, passwd, 'ADMIN', must_change=False)
        data['users'].append(admin)
        # Make a recovery copy of the existing DB before adding credentials.
        if database.exists():
            recovery = database.with_name(database.name + '.przed-kontami.bak')
            if not recovery.exists():
                atomic_write(recovery, database.read_bytes())
        atomic_write(database, db_encode(data))
        print('\nUtworzono administratora:', admin['username'])
        print('Można teraz uruchomić CommandFIRE SSP Serwis na wszystkich stanowiskach.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, EOFError, KeyboardInterrupt) as exc:
        print('\nNie utworzono administratora:', exc)
        raise SystemExit(1)
