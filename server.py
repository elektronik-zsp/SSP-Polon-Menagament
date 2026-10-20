"""SSP Polon 2.0 — local, offline service application; Python standard library."""
import argparse
from copy import deepcopy
from datetime import datetime, date
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parent
VERSION = '2.0.0'
DEFAULT_SERVICE = {
    'company': '', 'address': '', 'taxId': '', 'phone': '', 'email': '',
    'site': '', 'siteAddress': '', 'technicians': [], 'protocolPrefix': 'SSP',
    'inspectionMonths': 3, 'reminderDays': 30,
    'checklist': ['Oględziny centrali i sygnalizacji', 'Kontrola zasilania podstawowego i rezerwowego',
                  'Sprawdzenie wskazań uszkodzeń', 'Próby wybranych elementów dozorowych',
                  'Weryfikacja transmisji i sterowań w uzgodnionym zakresie',
                  'Przywrócenie systemu do uzgodnionego stanu pracy'],
}
DEFAULT_CONFIG = {'port': 8765, 'database': 'db_polon_ssp.json', 'open_browser': True,
                  'service': DEFAULT_SERVICE}
EMPTY_DB = {'panels': [], 'faults': [], 'history': [], 'schemaVersion': 2, 'audit': []}


def atomic_write(path, content):
    fd, name = tempfile.mkstemp(prefix=path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def encode(data):
    return json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')


def revision(raw):
    return hashlib.sha256(raw).hexdigest() if raw is not None else None


def require(condition, message):
    if not condition:
        raise ValueError(message)


def valid_date(value, label, optional=True):
    if value in ('', None) and optional:
        return
    require(isinstance(value, str), 'Nieprawidłowa data: ' + label)
    try:
        datetime.fromisoformat(value.replace(' ', 'T'))
    except (ValueError, TypeError):
        raise ValueError('Nieprawidłowa data: ' + label)


def validate_database(data):
    require(isinstance(data, dict), 'Baza musi być obiektem JSON.')
    require(data.get('schemaVersion', 1) in (1, 2), 'Nieobsługiwana wersja bazy. Zaktualizuj aplikację.')
    defaults = {
        'panels': {'model': '', 'location': '', 'spot': '', 'serialNo': '', 'intervalMonths': 3,
                   'lastInspection': '', 'condition': 'Niezweryfikowana', 'archived': False},
        'faults': {'date': '', 'panelId': '', 'reporter': '', 'desc': '', 'status': 'Nowe',
                   'priority': 'Normalny', 'assignee': '', 'dueDate': ''},
        'history': {'date': '', 'panelId': '', 'type': 'Serwis', 'contractor': '', 'protocolNo': '',
                    'result': '', 'desc': '', 'recom': '', 'protocolStatus': 'legacy'},
    }
    for key in defaults:
        require(isinstance(data.get(key), list), 'Baza musi zawierać listę ' + key)
        ids = set()
        for row in data[key]:
            require(isinstance(row, dict) and isinstance(row.get('id'), str) and 0 < len(row['id']) <= 120,
                    'Nieprawidłowy identyfikator: ' + key)
            require(row['id'] not in ids, 'Powtórzony identyfikator: ' + row['id'])
            ids.add(row['id'])
            for field, fallback in defaults[key].items():
                if field not in row:
                    row[field] = deepcopy(fallback)
                if isinstance(fallback, str):
                    require(isinstance(row[field], str) and len(row[field]) <= 30000, 'Nieprawidłowe pole: ' + field)
            valid_date(row.get('date'), 'data wpisu')
            if key == 'panels':
                require(type(row['intervalMonths']) is int and 1 <= row['intervalMonths'] <= 120, 'Interwał: 1–120 miesięcy.')
                require(type(row['archived']) is bool, 'Nieprawidłowy stan archiwizacji.')
                valid_date(row['lastInspection'], 'ostatni przegląd')
            elif key == 'faults':
                require(row['status'] in ('Nowe', 'W trakcie', 'Oczekujące', 'Zamknięte'), 'Nieprawidłowy status zgłoszenia.')
                require(row['priority'] in ('Niski', 'Normalny', 'Wysoki', 'Krytyczny'), 'Nieprawidłowy priorytet.')
                valid_date(row['dueDate'], 'termin zgłoszenia')
            else:
                require(row['protocolStatus'] in ('legacy', 'draft', 'final'), 'Nieprawidłowy status protokołu.')
                if row['protocolStatus'] != 'legacy':
                    require(row.get('result') in ('Pozytywny', 'Negatywny', 'Warunkowy', ''), 'Nieprawidłowy wynik.')
                    checks = row.get('checklist', [])
                    require(isinstance(checks, list) and len(checks) <= 100, 'Nieprawidłowa lista kontrolna.')
                    for item in checks:
                        require(isinstance(item, dict) and isinstance(item.get('label'), str)
                                and isinstance(item.get('note', ''), str)
                                and item.get('result') in ('', 'OK', 'Usterka', 'Nie dotyczy'), 'Nieprawidłowa pozycja kontroli.')
                    for field in ('parts', 'recipient', 'technician', 'scope'):
                        require(isinstance(row.get(field, ''), str), 'Nieprawidłowe pole: ' + field)
                    hours = row.get('hours', 0)
                    require(type(hours) in (int, float) and 0 <= hours <= 10000, 'Nieprawidłowy czas pracy.')
    data['schemaVersion'] = 2
    require(isinstance(data.get('audit', []), list), 'Nieprawidłowy dziennik zmian.')
    data.setdefault('audit', [])
    require(all(isinstance(a, dict) and isinstance(a.get('date'), str)
                and isinstance(a.get('action'), str) and isinstance(a.get('details'), list)
                and all(isinstance(x, str) for x in a['details']) for a in data['audit']),
            'Nieprawidłowe wpisy dziennika zmian.')
    return data


def decode_database(raw):
    encoding = 'utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'
    return validate_database(json.loads(raw.decode(encoding)))


def validate_service(value):
    require(isinstance(value, dict), 'Nieprawidłowa konfiguracja serwisu.')
    result = dict(DEFAULT_SERVICE, **value)
    for field in ('company', 'address', 'taxId', 'phone', 'email', 'site', 'siteAddress', 'protocolPrefix'):
        require(isinstance(result[field], str) and len(result[field]) <= 500, 'Nieprawidłowe pole: ' + field)
    require(re.fullmatch(r'[A-Za-z0-9_-]{1,16}', result['protocolPrefix']), 'Prefiks: 1–16 liter, cyfr, _ lub -.')
    for field in ('technicians', 'checklist'):
        require(isinstance(result[field], list) and len(result[field]) <= 100
                and all(isinstance(x, str) and 0 < len(x.strip()) <= 500 for x in result[field]), 'Nieprawidłowa lista: ' + field)
    require(type(result['inspectionMonths']) is int and 1 <= result['inspectionMonths'] <= 120, 'Interwał: 1–120 miesięcy.')
    require(type(result['reminderDays']) is int and 1 <= result['reminderDays'] <= 365, 'Przypomnienie: 1–365 dni.')
    return result


def apply_workflow(data, old, service, replace=False):
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    old = old or deepcopy(EMPTY_DB)
    previous = {h['id']: h for h in old['history']}
    panels = {p['id']: p for p in data['panels']}
    faults = {f['id']: f for f in data['faults']}
    if not replace:
        incoming = {h['id']: h for h in data['history']}
        for key, record in previous.items():
            if record['protocolStatus'] == 'final':
                require(incoming.get(key) == record, 'Zatwierdzony protokół jest niezmienny. Utwórz nowy protokół uzupełniający.')
        for collection in ('panels', 'faults'):
            require({r['id'] for r in old[collection]} <= {r['id'] for r in data[collection]},
                    'Nie usuwaj ewidencji. Użyj archiwizacji lub zamknięcia zgłoszenia.')
    used = {h['protocolNo'] for h in data['history'] if h.get('protocolNo')}
    for row in data['history']:
        before = previous.get(row['id'])
        newly_final = row['protocolStatus'] == 'final' and (not before or before['protocolStatus'] != 'final')
        if not newly_final or replace:
            continue
        panel = panels.get(row['panelId'])
        require(panel is not None and not panel['archived'], 'Wybierz aktywną centralę.')
        require(row['date'] and row['desc'].strip() and row.get('technician', '').strip(), 'Uzupełnij datę, opis i wykonawcę.')
        require(row['result'] in ('Pozytywny', 'Negatywny', 'Warunkowy'), 'Wybierz wynik prac.')
        checks = row.get('checklist', [])
        if row['type'] == 'Przegląd':
            require(checks and all(c['result'] for c in checks), 'Przegląd wymaga uzupełnionej listy kontrolnej.')
            require(any(c['result'] != 'Nie dotyczy' for c in checks), 'Nie można zatwierdzić przeglądu bez wykonanych kontroli.')
        if row['result'] == 'Pozytywny':
            require(not any(c['result'] == 'Usterka' for c in checks), 'Lista zawiera usterkę — wynik nie może być pozytywny.')
        else:
            require(row['recom'].strip(), 'Wynik negatywny lub warunkowy wymaga zaleceń.')
        valid_date(row['date'], 'data protokołu', optional=False)
        require(date.fromisoformat(row['date'][:10]) <= date.today(), 'Nie można zatwierdzić prac z przyszłą datą.')
        year = row['date'][:4]
        number = 1
        prefix = service['protocolPrefix'] + '/' + year + '/'
        while prefix + f'{number:04d}' in used:
            number += 1
        row['protocolNo'] = prefix + f'{number:04d}'
        used.add(row['protocolNo'])
        row['finalizedAt'] = now
        row['panelSnapshot'] = deepcopy(panel)
        row['serviceSnapshot'] = deepcopy(service)
        row['contractor'] = row['technician']
        if row['type'] == 'Przegląd' and row['result'] == 'Pozytywny':
            panel['lastInspection'] = max(panel['lastInspection'], row['date'])
        if row['result'] != 'Pozytywny':
            panel['condition'] = 'Wymaga serwisu'
        if row.get('closeFault'):
            require(row['result'] == 'Pozytywny', 'Zgłoszenie można zamknąć tylko po pozytywnym wyniku.')
            fault = faults.get(row.get('faultId'))
            require(fault is not None and fault['panelId'] == row['panelId'], 'Nieprawidłowe powiązanie zgłoszenia.')
            fault['status'] = 'Zamknięte'
            fault['closedAt'] = now
    if not replace:
        old_panels = {p['id']: p for p in old['panels']}
        for panel in data['panels']:
            if panel['archived'] and not old_panels.get(panel['id'], {}).get('archived'):
                require(not any(f['panelId'] == panel['id'] and f['status'] != 'Zamknięte' for f in data['faults'])
                        and not any(h['panelId'] == panel['id'] and h['protocolStatus'] == 'draft' for h in data['history']),
                        'Nie można archiwizować centrali z otwartymi zgłoszeniami lub szkicami.')
        for field in ('faults', 'history'):
            old_by_id = {r['id']: r for r in old[field]}
            for row in data[field]:
                if row != old_by_id.get(row['id']):
                    require(row['panelId'] in panels, 'Wpis musi być powiązany z istniejącą centralą.')
        old_faults = {f['id']: f for f in old['faults']}
        for fault in data['faults']:
            if fault['status'] == 'Zamknięte' and old_faults.get(fault['id'], {}).get('status') != 'Zamknięte':
                require(any(h.get('faultId') == fault['id'] and h['protocolStatus'] == 'final'
                            and h['result'] == 'Pozytywny' for h in data['history']),
                        'Zamknięcie zgłoszenia wymaga pozytywnego zatwierdzonego protokołu.')
    changes = []
    for field, label in (('panels', 'Centrala'), ('faults', 'Zgłoszenie'), ('history', 'Protokół')):
        old_by_id = {r['id']: r for r in old[field]}
        for row in data[field]:
            if row != old_by_id.get(row['id']):
                changes.append(label + ': ' + row['id'] + (' — dodano' if row['id'] not in old_by_id else ' — zmieniono'))
    for record in old['history']:
        if not any(h['id'] == record['id'] for h in data['history']):
            changes.append('Protokół: ' + record['id'] + ' — usunięto')
    data['audit'] = deepcopy(old.get('audit', []))[-999:]
    data['audit'].append({'date': now, 'action': 'Import / przywrócenie bazy' if replace else 'Zapis', 'details': changes[:200]})
    return data


def make_server(root, port):
    config_path = root / 'config.json'
    if not config_path.exists():
        atomic_write(config_path, encode(DEFAULT_CONFIG))
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    require(isinstance(config, dict), 'Konfiguracja musi być obiektem JSON.')
    config['service'] = validate_service(config.get('service', {}))
    filename = config.get('database', DEFAULT_CONFIG['database'])
    require(isinstance(filename, str) and re.fullmatch(r'[\w][\w.-]{0,100}\.json', filename)
            and filename.lower() != 'config.json', 'Nieprawidłowa nazwa pliku bazy.')
    database = root / filename
    require(not database.is_symlink(), 'Baza nie może być dowiązaniem symbolicznym.')
    backup_dir = root / 'backups'
    selected_port = config.get('port', 8765) if port is None else port
    require(type(selected_port) is int and 0 <= selected_port <= 65535, 'Nieprawidłowy port.')

    def backup(raw):
        if raw is None:
            return None
        backup_dir.mkdir(exist_ok=True)
        name = database.stem + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json'
        atomic_write(backup_dir / name, raw)
        atomic_write(database.with_suffix('.json.bak'), raw)
        # Keep the newest 30 for this database only.
        for p in sorted(backup_dir.glob(database.stem + '-*.json'), reverse=True)[30:]:
            p.unlink()
        return name

    class Handler(BaseHTTPRequestHandler):
        def respond(self, status, data, content_type='application/json; charset=utf-8'):
            body = encode(data) if not isinstance(data, bytes) else data
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def trusted(self, write=False):
            expected = '127.0.0.1:' + str(self.server.server_port)
            return (self.headers.get('Host') == expected
                    and self.headers.get('Origin') in (None, 'http://' + expected)
                    and self.headers.get('Sec-Fetch-Site') != 'cross-site'
                    and (not write or self.headers.get('X-SSP-Client') == 'local'))

        def current(self):
            if not database.exists():
                return None, None, None
            raw = database.read_bytes()
            return decode_database(raw), revision(raw), raw

        def do_GET(self):
            if not self.trusted():
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            try:
                files = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'),
                         '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css')}
                if self.path in files:
                    name, mime = files[self.path]
                    return self.respond(200, (root / name).read_bytes(), mime + '; charset=utf-8')
                if self.path == '/api/database':
                    data, rev, _ = self.current()
                    return self.respond(200, {'database': data, 'revision': rev})
                if self.path == '/api/config':
                    raw = config_path.read_bytes()
                    latest = json.loads(raw.decode('utf-8-sig'))
                    return self.respond(200, {'service': validate_service(latest.get('service', {})),
                                             'revision': revision(raw), 'version': VERSION, 'database': filename})
                if self.path == '/api/backups':
                    items = sorted(backup_dir.glob(database.stem + '-*.json'), reverse=True) if backup_dir.exists() else []
                    return self.respond(200, [{'name': p.name, 'size': p.stat().st_size} for p in items])
                if self.path.startswith('/api/backups/'):
                    name = self.path[len('/api/backups/'):]
                    require('/' not in name and '\\' not in name and name.startswith(database.stem + '-') and name.endswith('.json'), 'Nieprawidłowa kopia.')
                    path = backup_dir / name
                    require(not path.is_symlink(), 'Nieprawidłowa kopia.')
                    return self.respond(200, path.read_bytes())
                self.respond(404, {'error': 'Nie znaleziono.'})
            except (ValueError, OSError) as error:
                self.respond(500, {'error': 'Nie można odczytać danych: ' + str(error)})

        def do_POST(self):
            if not self.trusted(write=True):
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            if self.path != '/api/backup':
                return self.respond(404, {'error': 'Nie znaleziono.'})
            try:
                _, _, raw = self.current()
                return self.respond(200, {'name': backup(raw)})
            except (ValueError, OSError) as error:
                return self.respond(400, {'error': str(error)})

        def do_PUT(self):
            if not self.trusted(write=True):
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            if self.path not in ('/api/database', '/api/config'):
                return self.respond(404, {'error': 'Nie znaleziono.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 20 * 1024 * 1024:
                    return self.respond(413, {'error': 'Limit pliku wynosi 20 MB.'})
                payload = json.loads(self.rfile.read(length))
                require(isinstance(payload, dict) and 'revision' in payload, 'Brak wersji danych.')
                if self.path == '/api/config':
                    raw = config_path.read_bytes()
                    if payload['revision'] != revision(raw):
                        return self.respond(409, {'error': 'Konfiguracja zmieniła się. Odśwież stronę.'})
                    latest = json.loads(raw.decode('utf-8-sig'))
                    latest['service'] = validate_service(payload.get('service'))
                    atomic_write(config_path.with_suffix('.json.bak'), raw)
                    content = encode(latest)
                    atomic_write(config_path, content)
                    config['service'] = latest['service']
                    return self.respond(200, {'service': latest['service'], 'revision': revision(content)})
                data = validate_database(payload.get('database'))
                old_data, rev, raw = self.current()
                if payload['revision'] != rev:
                    return self.respond(409, {'error': 'Baza zmieniła się w innym oknie lub na dysku. Odśwież stronę; Twoje zmiany nie zostały zapisane.'})
                service = validate_service(json.loads(config_path.read_text(encoding='utf-8-sig')).get('service', {}))
                data = apply_workflow(data, old_data, service, replace=payload.get('mode') == 'replace')
                content = encode(data)
                backup(raw)
                atomic_write(database, content)
                return self.respond(200, {'revision': revision(content), 'database': data})
            except (ValueError, OSError, TypeError) as error:
                self.respond(400, {'error': 'Nie zapisano danych: ' + str(error)})

    server = HTTPServer(('127.0.0.1', selected_port), Handler)
    server.timeout = 10
    return server, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    try:
        server, config = make_server(ROOT, args.port)
        url = 'http://127.0.0.1:' + str(server.server_port)
        print('SSP Polon ' + VERSION + ': ' + url + '\nZostaw to okno otwarte. Ctrl+C kończy pracę.', flush=True)
        if config.get('open_browser', True) and not args.no_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    except (OSError, ValueError) as error:
        print('Nie można uruchomić aplikacji: ' + str(error))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
