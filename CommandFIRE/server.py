"""CommandFIRE SSP Serwis — shared database, configurable sequences, dashboard."""
import argparse
import base64
import binascii
from contextlib import contextmanager
import getpass
import socket
import time
from copy import deepcopy
from datetime import datetime, date
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import threading
import webbrowser
import uuid
import sys
# Portable Python is launched with -I (isolated); make the application module discoverable.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth_users import (PERMISSIONS, ROLE_DEFAULTS, LoginSessions, active_admins,
                        check_username, new_user, password_record, permissions_for,
                        public_user, record_account_change, validate_users, verify_password)
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = Path(__file__).resolve().parent
VERSION = '2.12.10-TEST'
DEFAULT_SERVICE = {
    'company': '', 'address': '', 'taxId': '', 'phone': '', 'email': '',
    'site': '', 'siteAddress': '', 'technicians': [], 'protocolPrefix': 'SSP',
    'inspectionMonths': 3, 'reminderDays': 30,
    'numbering': {
        'fault': {'prefix': 'ZG', 'start': 1, 'digits': 4, 'annual': True},
        'inspection': {'prefix': 'PRZ', 'start': 1, 'digits': 4, 'annual': True},
        'protocol': {'prefix': 'SSP', 'start': 1, 'digits': 4, 'annual': True},
    },
    'checklist': ['Oględziny centrali i sygnalizacji', 'Kontrola zasilania podstawowego i rezerwowego',
                  'Sprawdzenie wskazań uszkodzeń', 'Próby wybranych elementów dozorowych',
                  'Weryfikacja transmisji i sterowań w uzgodnionym zakresie',
                  'Przywrócenie systemu do uzgodnionego stanu pracy'],
}
DEFAULT_CONFIG = {'port': 8765, 'database': 'db_polon_ssp.json', 'open_browser': True,
                  'service': DEFAULT_SERVICE}
EMPTY_DB = {'panels': [], 'faults': [], 'history': [], 'schemaVersion': 8, 'audit': [], 'users': [], 'costs': []}
FAULT_STATUSES = ('Nowe', 'W realizacji', 'Zakończone', 'Anulowane')
LEGACY_STATUSES = {'W trakcie': 'W realizacji', 'Oczekujące': 'W realizacji', 'Zamknięte': 'Zakończone'}
TERMINAL_STATUSES = ('Zakończone', 'Anulowane')



def number_rule(service, kind):
    """Use legacy protocolPrefix for databases not yet configured for numbering."""
    rules = service.get('numbering') or {}
    default = deepcopy(DEFAULT_SERVICE['numbering'][kind])
    if kind == 'protocol':
        default['prefix'] = service.get('protocolPrefix', 'SSP')
    if isinstance(rules.get(kind), dict):
        default.update(rules[kind])
    return default


def next_document_number(rows, field, service, kind, event_date):
    """Called exclusively inside the cross-computer database mutex."""
    rule = number_rule(service, kind)
    lead = rule['prefix'] + ('/' + event_date[:4] if rule['annual'] else '') + '/'
    highest = rule['start'] - 1
    existing = {row.get(field, '') for row in rows if row.get(field)}
    for value in existing:
        if value.startswith(lead) and value[len(lead):].isdigit():
            highest = max(highest, int(value[len(lead):]))
    proposed = lead + str(highest + 1).zfill(rule['digits'])
    while proposed in existing:
        highest += 1
        proposed = lead + str(highest + 1).zfill(rule['digits'])
    return proposed


def active_fault(fault):
    return fault['status'] not in TERMINAL_STATUSES


def make_activity(now, kind, author, text, old_status='', new_status=''):
    activity = {'id': 'LOG-' + uuid.uuid4().hex, 'at': now, 'type': kind,
                'author': author, 'text': text}
    if old_status != new_status:
        activity['fromStatus'] = old_status
        activity['toStatus'] = new_status
    return activity




# The OS-level lock serializes every read-modify-write transaction across SMB
# clients. The active editors themselves are recorded INSIDE the JSON database.
@contextmanager
def database_mutex(path):
    marker = path.with_name(path.name + '.mutex')
    with open(marker, 'a+b') as mutex:
        for attempt in range(200):
            try:
                mutex.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(mutex.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(mutex.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if attempt == 199:
                    raise OSError('Nie można zablokować wspólnej bazy. Sprawdź połączenie z dyskiem.')
                time.sleep(.05)
        try:
            yield
        finally:
            mutex.seek(0)
            if os.name == 'nt':
                msvcrt.locking(mutex.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(mutex.fileno(), fcntl.LOCK_UN)


def content_revision(data):
    """Do not invalidate editor snapshots merely by acquiring/renewing a lease."""
    if data is None:
        return None
    relevant = dict(data)
    relevant.pop('activeSessions', None)
    relevant.pop('users', None)
    return revision(json.dumps(relevant, ensure_ascii=False, sort_keys=True).encode('utf-8'))


def service_revision(value):
    return revision(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8'))


def checked_resource(value):
    require(isinstance(value, str) and re.fullmatch(r'(panels|faults|history)/[^\x00-\x1f]{1,120}|settings|import', value),
            'Nieprawidłowy identyfikator blokady.')
    return value


def token_digest(token):
    require(isinstance(token, str) and re.fullmatch(r'[a-fA-F0-9-]{32,64}', token),
            'Nieprawidłowy identyfikator sesji.')
    return hashlib.sha256(token.encode('ascii')).hexdigest()


def sessions(data, now=None):
    """Remove expired leases in memory. Call under database_mutex."""
    if now is None:
        now = time.time()
    values = data.setdefault('activeSessions', {})
    require(isinstance(values, dict), 'Nieprawidłowe sesje w pliku bazy.')
    for key, value in list(values.items()):
        checked_resource(key)
        require(isinstance(value, dict) and type(value.get('lastActivity')) in (float, int)
                and isinstance(value.get('tokenHash'), str) and isinstance(value.get('owner'), str),
                'Nieprawidłowa sesja w bazie: ' + key)
        if now - value['lastActivity'] >= 1800:
            del values[key]
    return values


def own_lease(state, resource, token):
    entry = state.get(resource)
    return bool(entry and entry['tokenHash'] == token_digest(token))


def check_edit_lock(state, resource, token):
    checked_resource(resource)
    if not own_lease(state, resource, token):
        entry = state.get(resource)
        if entry:
            raise LockedError('Ten rekord edytuje obecnie: ' + entry['owner'] + '. Spróbuj później.')
        raise LockedError('Brak aktywnej blokady edycji lub upłynęło 30 minut bezczynności. Otwórz formularz ponownie.')


class LockedError(ValueError):
    pass


def merge_changed_rows(current, base, incoming, lock_state, token):
    """Merge independent modifications instead of overwriting another client."""
    merged = deepcopy(current)
    for field in ('panels', 'faults', 'history', 'costs'):
        old_rows = {r['id']: r for r in base[field]}
        new_rows = {r['id']: r for r in incoming[field]}
        latest_rows = {r['id']: r for r in current[field]}
        # Keep client collection order deterministic; sets would randomize newly
        # inserted rows and make sequence assignment unpredictable.
        for row_id in dict.fromkeys([r['id'] for r in base[field]] +
                                    [r['id'] for r in incoming[field]]):
            before, proposed, latest = old_rows.get(row_id), new_rows.get(row_id), latest_rows.get(row_id)
            if before == proposed:
                continue
            if field == 'costs':
                require(before is None, 'Rejestr kosztów jest niezmienny. Dodaj korektę zamiast edycji lub usunięcia.')
            if before is not None:
                check_edit_lock(lock_state, field + '/' + row_id, token)
            if before != latest:
                raise ConflictError('W tym rekordzie pojawiły się nowsze zmiany. Otwórz go ponownie.')
            if proposed is None:
                merged[field] = [r for r in merged[field] if r['id'] != row_id]
            elif before is None:
                if row_id in latest_rows:
                    raise ConflictError('Identyfikator jest już zajęty. Odśwież dane.')
                merged[field].append(deepcopy(proposed))
            else:
                merged[field] = [deepcopy(proposed) if r['id'] == row_id else r for r in merged[field]]
    return merged


class ConflictError(ValueError):
    pass

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


COST_CATEGORIES = ('Części', 'Robocizna', 'Dojazd', 'Inne')


def validate_costs(data):
    rows = data.setdefault('costs', [])
    require(isinstance(rows, list) and len(rows) <= 100000, 'Nieprawidłowy rejestr kosztów.')
    ids = set()
    protocols = {h['id']: h for h in data['history']}
    for row in rows:
        require(isinstance(row, dict), 'Nieprawidłowy wpis kosztu.')
        key = row.get('id')
        require(isinstance(key, str) and 0 < len(key) <= 120 and key not in ids, 'Nieprawidłowy identyfikator kosztu.')
        ids.add(key)
        for field, maximum in (('protocolId',120),('date',10),('category',30),('description',2000),
                                ('reference',120),('reversesId',120),('createdAt',50),('createdBy',250)):
            row.setdefault(field, '')
            require(isinstance(row[field], str) and len(row[field]) <= maximum, 'Nieprawidłowe pole kosztu: ' + field)
        require(row['protocolId'] in protocols and protocols[row['protocolId']]['protocolStatus'] in ('final','legacy'),
                'Koszt wymaga zatwierdzonego protokołu lub wpisu historycznego.')
        require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', row['date']), 'Podaj datę kosztu RRRR-MM-DD.')
        try:
            date.fromisoformat(row['date'])
        except ValueError:
            raise ValueError('Nieprawidłowa data kosztu.')
        require(row['category'] in COST_CATEGORIES and row['description'].strip(), 'Podaj kategorię i opis kosztu.')
        amount = row.get('amountGrosz')
        require(type(amount) is int and 0 < abs(amount) <= 10000000000,
                'Kwota musi być zapisana jako liczba całkowita groszy, od 0,01 do 100 000 000 PLN.')
        require(bool(row['reversesId']) == (amount < 0), 'Ujemna kwota jest dozwolona tylko jako korekta pierwotnego kosztu.')
    by_id = {r['id']: r for r in rows}
    reversed_ids = set()
    for row in rows:
        if row['reversesId']:
            original = by_id.get(row['reversesId'])
            require(original is not None and original['amountGrosz'] > 0 and row['reversesId'] not in reversed_ids,
                    'Koszt można skorygować w całości tylko jeden raz.')
            require(row['amountGrosz'] == -original['amountGrosz'] and row['protocolId'] == original['protocolId']
                    and row['category'] == original['category'] and row['date'] >= original['date'],
                    'Korekta musi odwracać kwotę tego samego protokołu i kategorii, z datą nie wcześniejszą niż koszt.')
            reversed_ids.add(row['reversesId'])
    return rows


def address_key(value):
    return ' '.join(value.split()).casefold()


def validate_elements(panel):
    rows = panel['elements']
    require(isinstance(rows, list) and len(rows) <= 5000, 'Słownik centrali może zawierać do 5000 elementów.')
    ids, addresses = set(), set()
    for element in rows:
        require(isinstance(element, dict), 'Nieprawidłowy element słownika.')
        for key, maximum in (('id',120),('address',200),('type',120),('location',500),('notes',2000)):
            element.setdefault(key, '')
            require(isinstance(element[key], str) and len(element[key]) <= maximum, 'Nieprawidłowe pole elementu: ' + key)
        require(element['id'] and element['id'] not in ids, 'Powtórzony lub pusty identyfikator elementu.')
        normalized = address_key(element['address'])
        require(normalized and normalized not in addresses, 'Adres elementu jest pusty lub już istnieje w tej centrali (także w archiwum).')
        element.setdefault('archived', False)
        require(type(element['archived']) is bool, 'Nieprawidłowy stan archiwizacji elementu.')
        ids.add(element['id']); addresses.add(normalized)


def validate_database(data, partial=False):
    require(isinstance(data, dict), 'Baza musi być obiektem JSON.')
    require(data.get('schemaVersion', 1) in (1, 2, 3, 4, 5, 6, 7, 8), 'Nieobsługiwana wersja bazy. Zaktualizuj aplikację.')
    defaults = {
        'panels': {'model': '', 'location': '', 'spot': '', 'serialNo': '', 'intervalMonths': 3,
                   'lastInspection': '', 'condition': 'Niezweryfikowana', 'archived': False, 'coverage': '',
                   'serviceContact': '', 'documents': [], 'elements': [], 'inspectionPlanDate': '',
                   'inspectionPlanAssignee': '', 'inspectionPlanNote': '', 'inspectionPlanId': ''},
        'faults': {'date': '', 'panelId': '', 'reporter': '', 'desc': '', 'number': '', 'status': 'Nowe',
                   'priority': 'Normalny', 'assignee': '', 'dueDate': '', 'timeline': [], 'elementAddress': '',
                   'occurredAt': '', 'relatedFaultId': '', 'relationType': '', 'sourceProtocolId': '',
                   'cause': '', 'resolution': '', 'verification': '', 'workStage': '', 'elementId': '', 'elementType': '', 'elementLocation': ''},
        'history': {'date': '', 'panelId': '', 'type': 'Serwis', 'contractor': '', 'protocolNo': '', 'inspectionNo': '',
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
                elif field in ('timeline', 'documents', 'elements'):
                    require(isinstance(row[field], list) and len(row[field]) <= 20000,
                            'Nieprawidłowa historia zgłoszenia.')
            valid_date(row.get('date'), 'data wpisu')
            if key == 'panels':
                require(type(row['intervalMonths']) is int and 1 <= row['intervalMonths'] <= 120, 'Interwał: 1–120 miesięcy.')
                require(type(row['archived']) is bool, 'Nieprawidłowy stan archiwizacji.')
                valid_date(row['lastInspection'], 'ostatni przegląd')
                planned = row['inspectionPlanDate']
                if planned:
                    require(re.fullmatch(r'\d{4}-\d{2}-\d{2}', planned), 'Data wizyty musi mieć format RRRR-MM-DD.')
                    try:
                        date.fromisoformat(planned)
                    except ValueError:
                        raise ValueError('Nieprawidłowa data planowanej wizyty.')
                else:
                    require(not row['inspectionPlanAssignee'] and not row['inspectionPlanNote']
                            and not row['inspectionPlanId'], 'Plan bez daty musi być wyczyszczony.')
                require(len(row['inspectionPlanAssignee']) <= 250 and len(row['inspectionPlanNote']) <= 2000
                        and len(row['inspectionPlanId']) <= 120, 'Zbyt długie dane planu.')
                validate_elements(row)
                require(len(row['documents']) <= 20, 'Maksymalnie 20 dokumentów centrali.')
                doc_ids = set()
                for doc in row['documents']:
                    require(isinstance(doc, dict), 'Nieprawidłowy dokument.')
                    require(isinstance(doc.get('id'), str) and 0 < len(doc['id']) <= 120
                            and doc['id'] not in doc_ids, 'Nieprawidłowy identyfikator dokumentu.')
                    doc_ids.add(doc['id'])
                    require(isinstance(doc.get('name'), str) and 0 < len(doc['name']) <= 200
                            and '/' not in doc['name'] and '\\' not in doc['name'], 'Nieprawidłowa nazwa dokumentu.')
                    require(Path(doc['name']).suffix.lower() in ('.pdf', '.png', '.jpg', '.jpeg', '.txt'),
                            'Dozwolone dokumenty: PDF, PNG, JPG, TXT.')
                    require(isinstance(doc.get('data'), str) and len(doc['data']) <= 2800000,
                            'Dokument jest zbyt duży (limit 2 MB).')
                    try:
                        decoded = base64.b64decode(doc['data'], validate=True)
                    except (ValueError, binascii.Error):
                        raise ValueError('Nieprawidłowa zawartość dokumentu.')
                    require(0 < len(decoded) <= 2 * 1024 * 1024, 'Limit dokumentu: 2 MB.')
            elif key == 'faults':
                legacy = row['status']
                if legacy in LEGACY_STATUSES:
                    row.setdefault('legacyStatus', legacy)
                row['status'] = LEGACY_STATUSES.get(legacy, legacy)
                require(row['status'] in FAULT_STATUSES, 'Nieprawidłowy status zgłoszenia.')
                require(row['priority'] in ('Niski', 'Normalny', 'Wysoki', 'Krytyczny'), 'Nieprawidłowy priorytet.')
                valid_date(row['dueDate'], 'termin zgłoszenia')
                valid_date(row['occurredAt'], 'wystąpienie usterki')
                require(row['workStage'] in ('', 'Diagnoza', 'Naprawa', 'Oczekiwanie na części', 'Oczekiwanie na serwis', 'Weryfikacja'), 'Nieprawidłowy etap prac.')
                require(row['relationType'] in ('', 'Nawrót', 'Duplikat', 'Powiązane'), 'Nieprawidłowy rodzaj powiązania.')
                seen = set()
                for entry in row['timeline']:
                    require(isinstance(entry, dict), 'Nieprawidłowy wpis historii zgłoszenia.')
                    eid = entry.get('id')
                    require(isinstance(eid, str) and 1 <= len(eid) <= 120 and eid not in seen,
                            'Nieprawidłowy identyfikator wpisu historii.')
                    seen.add(eid)
                    require(entry.get('type') in ('created', 'action', 'status', 'protocol', 'migration', 'updated'),
                            'Nieprawidłowy rodzaj wpisu historii.')
                    for entry_field in ('author', 'text'):
                        require(isinstance(entry.get(entry_field), str) and len(entry[entry_field]) <= 10000,
                                'Nieprawidłowe pole historii: ' + entry_field)
                    require(isinstance(entry.get('at', ''), str), 'Nieprawidłowy czas wpisu.')
                    valid_date(entry.get('at', ''), 'czas wpisu')
                    for status_field in ('fromStatus', 'toStatus'):
                        require(status_field not in entry or entry[status_field] in ('', *FAULT_STATUSES),
                                'Nieprawidłowa zmiana statusu w historii.')
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
    validate_costs(data)
    panel_ids = {p['id'] for p in data['panels']}
    faults_by_id = {f['id']: f for f in data['faults']}
    histories_by_id = {h['id']: h for h in data['history']}
    panel_by_id = {p['id']: p for p in data['panels']}
    for fault in data['faults']:
        require(len(fault['elementId']) <= 120, 'Nieprawidłowy identyfikator elementu.')
        require(not fault['elementId'] or (partial and fault['panelId'] not in panel_by_id) or any(e['id'] == fault['elementId'] for e in panel_by_id.get(fault['panelId'], {}).get('elements', [])),
                'Element musi należeć do wskazanej centrali.')
        related = fault.get('relatedFaultId')
        require(not related or (related in faults_by_id and related != fault['id']
                and faults_by_id[related]['panelId'] == fault['panelId']), 'Nieprawidłowe powiązanie zgłoszeń.')
        require(bool(related) == bool(fault.get('relationType')), 'Uzupełnij rodzaj i cel powiązania.')
        source = fault.get('sourceProtocolId')
        require(not source or (partial and source not in histories_by_id) or (source in histories_by_id and histories_by_id[source]['panelId'] == fault['panelId']),
                'Nieprawidłowy protokół źródłowy.')
    if 'activeSessions' in data:
        require(isinstance(data['activeSessions'], dict), 'Nieprawidłowe sesje w bazie.')
        for lock_key in data['activeSessions']:
            checked_resource(lock_key)
    for collection, field in (('faults', 'number'), ('history', 'protocolNo'),
                              ('history', 'inspectionNo')):
        numbers = [row[field] for row in data[collection] if row[field]]
        require(len(numbers) == len(set(numbers)), 'Powtórzona numeracja: ' + field)
    data['schemaVersion'] = 8
    require(isinstance(data.get('audit', []), list), 'Nieprawidłowy dziennik zmian.')
    data.setdefault('audit', [])
    validate_users(data)
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
    numbering = result.get('numbering')
    require(isinstance(numbering, dict), 'Nieprawidłowa konfiguracja numeracji.')
    # Older clients configured only protocolPrefix; continue to honor changes
    # until they explicitly set a different numbering.protocol.prefix.
    if (result['protocolPrefix'] != DEFAULT_SERVICE['protocolPrefix'] and
            numbering.get('protocol', {}).get('prefix') == DEFAULT_SERVICE['numbering']['protocol']['prefix']):
        numbering = deepcopy(numbering)
        numbering['protocol'] = dict(numbering['protocol'], prefix=result['protocolPrefix'])
        result['numbering'] = numbering
    normalized = {}
    for kind in ('fault', 'inspection', 'protocol'):
        require(kind not in numbering or isinstance(numbering[kind], dict),
                'Nieprawidłowa seria numeracji: ' + kind)
        value = number_rule(result, kind)
        require(isinstance(value, dict), 'Nieprawidłowa seria numerów: ' + kind)
        require(isinstance(value.get('prefix'), str) and
                re.fullmatch(r'[A-Za-z0-9_-]{1,16}', value['prefix']),
                'Prefiks numeracji: 1–16 liter, cyfr, _ lub -.')
        require(type(value.get('start')) is int and 1 <= value['start'] <= 99999999,
                'Numer początkowy musi być w zakresie 1–99999999.')
        require(type(value.get('digits')) is int and 1 <= value['digits'] <= 9,
                'Liczba cyfr numeracji musi być w zakresie 1–9.')
        require(type(value.get('annual')) is bool,
                'Tryb numeracji rocznej musi być włączony lub wyłączony.')
        normalized[kind] = {name: value[name] for name in ('prefix','start','digits','annual')}
    require(len({r['prefix'] for r in normalized.values()}) == 3,
            'Każda seria numeracji musi mieć inny prefiks.')
    result['numbering'] = normalized
    for field in ('technicians', 'checklist'):
        require(isinstance(result[field], list) and len(result[field]) <= 100
                and all(isinstance(x, str) and 0 < len(x.strip()) <= 500 for x in result[field]), 'Nieprawidłowa lista: ' + field)
    require(type(result['inspectionMonths']) is int and 1 <= result['inspectionMonths'] <= 120, 'Interwał: 1–120 miesięcy.')
    require(type(result['reminderDays']) is int and 1 <= result['reminderDays'] <= 365, 'Przypomnienie: 1–365 dni.')
    return result


def audit_record_label(field, row, protocols=None):
    if field == 'costs':
        amount = row['amountGrosz']
        text = ('-' if amount < 0 else '') + str(abs(amount) // 100) + ',' + str(abs(amount) % 100).zfill(2) + ' PLN'
        return 'Koszt: ' + row['date'] + ' · ' + row['category'] + ' · ' + text + ' · Protokół: ' + ((protocols or {}).get(row['protocolId'], {}).get('protocolNo') or row['protocolId'])
    if field == 'faults':
        number = row.get('number') or row['id']
        description = ' '.join(str(row.get('desc', '')).split())[:120]
        return 'Zgłoszenie: ' + number + ' · Centrala: ' + row.get('panelId', '—') + ((' · ' + description) if description else '')
    if field == 'history':
        return 'Protokół: ' + (row.get('protocolNo') or 'Szkic') + ' · Centrala: ' + row.get('panelId', '—')
    return 'Centrala: ' + row['id']


def apply_workflow(data, old, service, replace=False, actor=None):
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    generated_protocol_events = set()
    plan_events = []
    old = old or deepcopy(EMPTY_DB)
    old_costs = {r['id']: r for r in old.get('costs', [])}
    if not replace:
        proposed_costs = {r['id']: r for r in data.get('costs', [])}
        require(all(proposed_costs.get(key) == value for key, value in old_costs.items()),
                'Rejestr kosztów jest niezmienny. Dodaj korektę.')
        for cost in data.get('costs', []):
            if cost['id'] not in old_costs:
                require(cost['date'] <= date.today().isoformat(), 'Koszt rzeczywisty nie może mieć przyszłej daty.')
                cost['createdAt'] = now
                cost['createdBy'] = actor['displayName'] if actor else 'System'
        validate_costs(data)

    previous = {h['id']: h for h in old['history']}
    old_faults = {f['id']: f for f in old['faults']}
    panels = {p['id']: p for p in data['panels']}
    faults = {f['id']: f for f in data['faults']}
    old_panels = {p['id']: p for p in old['panels']}
    plan_fields = ('inspectionPlanDate', 'inspectionPlanAssignee', 'inspectionPlanNote')
    if not replace:
        for panel in data['panels']:
            previous_elements = {e['id']: e for e in old_panels.get(panel['id'], {}).get('elements', [])}
            current_elements = {e['id']: e for e in panel['elements']}
            require(previous_elements.keys() <= current_elements.keys(), 'Nie usuwaj elementów słownika. Użyj archiwizacji.')
            if previous_elements != current_elements:
                require(not panel['archived'], 'Przywróć centralę z archiwum, aby zmienić słownik.')
                for eid, element in current_elements.items():
                    before = previous_elements.get(eid)
                    if before != element:
                        label = 'Element: ' + panel['id'] + ' · ' + element['address']
                        detail = ('dodano' if before is None else '; '.join(
                            key + ': ' + str(before.get(key, '')) + ' → ' + str(element.get(key, ''))
                            for key in ('address','type','location','notes','archived') if before.get(key) != element.get(key)))
                        plan_events.append(label + ' — ' + detail)
        for fault in data['faults']:
            before = old_faults.get(fault['id'], {})
            eid = fault.get('elementId', '')
            if eid and (before.get('elementId') != eid or before.get('panelId') != fault['panelId']):
                element = next((e for e in panels.get(fault['panelId'], {}).get('elements', []) if e['id'] == eid), None)
                require(element is not None and not element['archived'], 'Wybierz aktywny element wskazanej centrali.')
                fault.update(elementAddress=element['address'], elementType=element['type'], elementLocation=element['location'])
            elif eid:
                require(all(fault.get(key, '') == before.get(key, '') for key in ('elementAddress','elementType','elementLocation')),
                        'Zachowaj dane historyczne elementu albo wybierz inny element.')
            else:
                fault['elementType'] = ''
                fault['elementLocation'] = ''

    for panel in data['panels']:
        before = old_panels.get(panel['id'], {})
        changed = any(panel.get(k, '') != before.get(k, '') for k in plan_fields)
        if not replace:
            require(panel.get('inspectionPlanId', '') in (('', before.get('inspectionPlanId', '')) if changed else (before.get('inspectionPlanId', ''),)),
                    'Identyfikator wizyty nadaje aplikacja.')
        if changed and not replace:
            require(not panel['archived'] or not panel['inspectionPlanDate'],
                    'Nie można planować przeglądu archiwalnej centrali.')
            panel['inspectionPlanId'] = ('PLAN-' + uuid.uuid4().hex) if panel['inspectionPlanDate'] else ''
            plan_events.append('Plan przeglądu: ' + panel['id'] + ' — ' +
                ('; '.join(label + ': ' + (before.get(k) or '—') + ' → ' + (panel.get(k) or '—')
                           for k, label in zip(plan_fields, ('Data wizyty', 'Wykonawca', 'Uwagi'))
                           if before.get(k, '') != panel.get(k, ''))))
        elif replace and panel['inspectionPlanDate'] and not panel.get('inspectionPlanId'):
            panel['inspectionPlanId'] = 'PLAN-' + uuid.uuid4().hex
    if not replace:
        for row in data['history']:
            before = previous.get(row['id'])
            if row['protocolStatus'] != 'final':
                require(row.get('protocolNo', '') == (before.get('protocolNo', '') if before else '') and
                        row.get('inspectionNo', '') == (before.get('inspectionNo', '') if before else ''),
                        'Numer dokumentu można nadać wyłącznie podczas zatwierdzania.')
        incoming = {h['id']: h for h in data['history']}
        for key, record in previous.items():
            if record['protocolStatus'] == 'final':
                require(incoming.get(key) == record, 'Zatwierdzony protokół jest niezmienny. Utwórz nowy protokół uzupełniający.')
        for collection in ('panels', 'faults'):
            require({r['id'] for r in old[collection]} <= {r['id'] for r in data[collection]},
                    'Nie usuwaj ewidencji. Użyj archiwizacji lub zamknięcia zgłoszenia.')
    for fault in data['faults']:
        before = old_faults.get(fault['id'])
        if not before and not replace:
            require(not fault.get('number'), 'Numer nowego zgłoszenia nadaje automatycznie serwer.')
            fault['number'] = next_document_number(data['faults'], 'number', service, 'fault', fault['date'] or now)
        elif before and not replace:
            require(fault['number'] == before['number'], 'Numer zgłoszenia jest niezmienny.')
    for fault in data['faults']:
        related = fault.get('relatedFaultId')
        require(not related or (related in faults and related != fault['id']
                and faults[related]['panelId'] == fault['panelId']),
                'Powiązane zgłoszenie musi dotyczyć tej samej centrali i być inną sprawą.')
        require(bool(related) == bool(fault.get('relationType')), 'Wybierz zgłoszenie i rodzaj powiązania.')
        source = fault.get('sourceProtocolId')
        require(not source or any(h['id'] == source and h['panelId'] == fault['panelId']
                for h in data['history']), 'Protokół źródłowy musi dotyczyć tej samej centrali.')
        if not replace and old_faults.get(fault['id'], {}).get('status') != 'Zakończone' and fault['status'] == 'Zakończone':
            require(all(fault.get(k, '').strip() for k in ('cause', 'resolution', 'verification')),
                    'Zakończenie wymaga przyczyny, sposobu usunięcia i wyniku sprawdzenia.')
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
        require(not row.get('protocolNo') and not row.get('inspectionNo'),
                'Numer zatwierdzanego dokumentu nadaje automatycznie serwer.')
        row['protocolNo'] = next_document_number(data['history'], 'protocolNo', service, 'protocol', row['date'])
        if row['type'] == 'Przegląd':
            row['inspectionNo'] = next_document_number(data['history'], 'inspectionNo', service, 'inspection', row['date'])
        used.add(row['protocolNo'])
        row['finalizedAt'] = now
        row['panelSnapshot'] = deepcopy({k: v for k, v in panel.items() if k not in ('documents', 'elements')})
        row['serviceSnapshot'] = deepcopy(service)
        row['contractor'] = row['technician']
        if (row['type'] == 'Przegląd' and row.get('inspectionPlanId')
                and row['inspectionPlanId'] == panel.get('inspectionPlanId')):
            row['inspectionPlanSnapshot'] = {k: panel.get(k, '') for k in (*plan_fields, 'inspectionPlanId')}
            for key in (*plan_fields, 'inspectionPlanId'):
                panel[key] = ''
            plan_events.append('Plan przeglądu: ' + panel['id'] + ' — wizyta rozliczona protokołem ' + row['protocolNo']
                               + ' (wynik: ' + row['result'] + ').')
        if row['type'] == 'Przegląd' and row['result'] == 'Pozytywny':
            panel['lastInspection'] = max(panel['lastInspection'], row['date'])
        if row['result'] != 'Pozytywny':
            panel['condition'] = 'Wymaga serwisu'
        fault = faults.get(row.get('faultId')) if row.get('faultId') else None
        if row.get('faultId'):
            require(fault is not None and fault['panelId'] == row['panelId'], 'Nieprawidłowe powiązanie zgłoszenia.')
        if row.get('closeFault'):
            require(row['result'] == 'Pozytywny', 'Zgłoszenie można zamknąć tylko po pozytywnym wyniku.')
            require(fault is not None, 'Wybierz zgłoszenie do zakończenia.')
            require(fault['status'] != 'Anulowane', 'Anulowane zgłoszenie trzeba najpierw wznowić.')
            fault['status'] = 'Zakończone'
            fault['closedAt'] = now
            fault['cause'] = fault.get('cause') or 'Według protokołu ' + row['protocolNo']
            fault['resolution'] = row['desc']
            fault['verification'] = 'Pozytywny wynik protokołu ' + row['protocolNo']
        if fault:
            note = ('Zgłoszenie zakończone po zatwierdzeniu protokołu ' if row.get('closeFault') else 'Zatwierdzono powiązany protokół ')
            note += row['protocolNo'] + ' (wynik: ' + row['result'] + ', wykonawca: ' + row['technician'] + ').'
            event = make_activity(now, 'protocol', 'System', note,
                                  old_faults.get(fault['id'], {}).get('status', 'Nowe'), fault['status'])
            fault.setdefault('timeline', []).append(event)
            generated_protocol_events.add(event['id'])
    if not replace:
        old_panels = {p['id']: p for p in old['panels']}
        for panel in data['panels']:
            if panel['archived'] and not old_panels.get(panel['id'], {}).get('archived'):
                require(not panel.get('inspectionPlanDate'), 'Najpierw odwołaj zaplanowaną wizytę centrali.')
                require(not any(f['panelId'] == panel['id'] and active_fault(f) for f in data['faults'])
                        and not any(h['panelId'] == panel['id'] and h['protocolStatus'] == 'draft' for h in data['history']),
                        'Nie można archiwizować centrali z otwartymi zgłoszeniami lub szkicami.')
        for field in ('faults', 'history'):
            old_by_id = {r['id']: r for r in old[field]}
            for row in data[field]:
                if row != old_by_id.get(row['id']):
                    require(row['panelId'] in panels, 'Wpis musi być powiązany z istniejącą centralą.')
    # Activity is append-only. Entry time and generated events are authoritative on the server.
    if not replace:
        for fault in data['faults']:
            before = old_faults.get(fault['id'])
            if not before or (active_fault(fault) and not active_fault(before)):
                require(not panels[fault['panelId']]['archived'],
                        'Najpierw przywróć centralę z archiwum, aby otworzyć zgłoszenie.')
            original = deepcopy(before.get('timeline', [])) if before else []
            incoming = fault['timeline']
            require(incoming[:len(original)] == original,
                    'Historia zgłoszenia jest niezmienna. Można tylko dodawać wpisy.')
            added = incoming[len(original):]
            protocol_events = [e for e in added if e['id'] in generated_protocol_events]
            user_entries = [e for e in added if e['id'] not in generated_protocol_events]
            # The only automatic protocol entry may be created in this same transaction.
            require(all(e['at'] == now and e['author'] == 'System'
                     for e in protocol_events), 'Nie można ręcznie dopisywać zdarzeń protokołu.')
            require(len(user_entries) <= 1, 'Dodaj jeden wpis zgłoszenia na raz.')
            for entry in user_entries:
                require(entry['type'] == 'action' and entry['author'].strip()
                        and entry['text'].strip() and not entry.get('at'),
                        'Wpis musi zawierać wykonawcę i opis działania.')
                require(not any(k in entry for k in ('fromStatus', 'toStatus')),
                        'Zmianę statusu wskaż w formularzu zgłoszenia.')
                if actor:
                    if entry['author'].strip() != actor['displayName']:
                        entry['performedBy'] = entry['author'].strip()
                    entry['author'] = actor['displayName']
                    entry['userId'] = actor['id']
                entry['at'] = now
            if not before:
                require(fault['status'] == 'Nowe' or (fault['status'] == 'Zakończone' and protocol_events),
                        'Nowe zgłoszenie zaczyna od statusu „Nowe”.')
                require(not user_entries, 'Najpierw utwórz zgłoszenie, a następnie dodaj działanie.')
                fault['timeline'].insert(0, make_activity(
                    now, 'created', 'System', 'Zgłoszenie zarejestrowane.'))
            else:
                if not original:
                    fault['timeline'].insert(0, make_activity(
                        now, 'migration', 'System',
                        'Zgłoszenie przeniesione ze starszej wersji. Wcześniejsze czynności nie były rejestrowane.'
                        + (' Poprzedni status: ' + before['legacyStatus'] + '.' if before.get('legacyStatus') else '')))
                old_status = before['status']
                changed = fault['status'] != old_status
                if changed and not protocol_events:
                    require(len(user_entries) == 1,
                            'Zmiana statusu wymaga wpisu z wykonawcą i opisem działania.')
                    user_entries[0]['fromStatus'] = old_status
                    user_entries[0]['toStatus'] = fault['status']
                    if fault['status'] == 'Zakończone':
                        fault['closedAt'] = now
                    else:
                        fault.pop('closedAt', None)
                elif changed and protocol_events:
                    require(not user_entries, 'Zmiana statusu przez protokół odbywa się automatycznie.')
                elif user_entries and not changed:
                    # A note without a status change is still a permanent service action.
                    pass
                if before and any(fault.get(k) != before.get(k) for k in
                                  ('date', 'panelId', 'reporter', 'desc', 'priority', 'assignee', 'dueDate',
                                   'elementAddress', 'elementId', 'elementType', 'elementLocation', 'occurredAt', 'relatedFaultId', 'relationType', 'cause', 'resolution', 'verification', 'workStage')):
                    fault['timeline'].append(make_activity(
                        now, 'updated', actor['displayName'] if actor else 'System',
                        'Zmiana danych:\n' + '\n'.join(
                            label + ': ' + str(before.get(key) or '—') + ' → ' + str(fault.get(key) or '—')
                            for key, label in FAULT_CHANGE_LABELS.items() if fault.get(key) != before.get(key))))
            # Only server-generated protocol events may close without a user action.
    else:
        # Imports are replacements; imported events are retained exactly as recorded.
        pass
    changes = list(plan_events)
    audit_protocols = {h['id']: h for h in data['history']}
    for field, label in (('panels', 'Centrala'), ('faults', 'Zgłoszenie'), ('history', 'Protokół'), ('costs', 'Koszt')):
        old_by_id = {r['id']: r for r in old[field]}
        for row in data[field]:
            if row != old_by_id.get(row['id']):
                changes.append(audit_record_label(field, row, audit_protocols) + (' — dodano' if row['id'] not in old_by_id else ' — zmieniono'))
    for record in old['history']:
        if not any(h['id'] == record['id'] for h in data['history']):
            changes.append(audit_record_label('history', record) + ' — usunięto')
    data['audit'] = deepcopy(old.get('audit', []))[-999:]
    data['audit'].append({'date': now, 'action': 'Import / przywrócenie bazy' if replace else 'Zapis',
                          'user': actor['displayName'] if actor else 'System',
                          'userId': actor['id'] if actor else '', 'details': changes[:200]})
    return data


FAULT_CHANGE_LABELS = dict(date='Data zgłoszenia', panelId='Centrala', reporter='Zgłaszający',
    desc='Opis', priority='Priorytet', assignee='Odpowiedzialny', dueDate='Termin',
    elementAddress='Adres elementu', elementId='Element słownika', elementType='Typ elementu', elementLocation='Lokalizacja elementu', occurredAt='Wystąpienie', relatedFaultId='Powiązana sprawa',
    relationType='Rodzaj powiązania', workStage='Etap prac', cause='Przyczyna', resolution='Sposób usunięcia', verification='Sprawdzenie')


def database_summary(data):
    return {'schemaVersion': data['schemaVersion'], 'panels': len(data['panels']),
            'faults': len(data['faults']), 'history': len(data['history']),
            'documents': sum(len(p.get('documents', [])) for p in data['panels']),
            'lastEvent': max((a['date'] for a in data.get('audit', [])), default=''),
            'elements': sum(len(p.get('elements', [])) for p in data['panels']), 'costs': len(data.get('costs', [])), 'configuration': 'serviceConfig' in data, 'accounts': len(data.get('users', []))}


def inspect_backup(path, decoder=decode_database):
    result = {'name': path.name, 'size': path.stat().st_size,
              'modifiedAt': datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec='seconds')}
    try:
        require(not path.is_symlink(), 'Kopia nie może być dowiązaniem.')
        raw = path.read_bytes()
        data = decoder(raw)
        if 'serviceConfig' in data:
            validate_service(data['serviceConfig'])
        result.update(valid=True, sha256=revision(raw), summary=database_summary(data))
    except (ValueError, OSError, TypeError, KeyError) as error:
        result.update(valid=False, error=str(error))
    return result


def database_codec(root, database):
    """Use the same JSON/CFDB format in the server and local maintenance tools."""
    encrypted = database.suffix.lower() == '.cfdb'
    if encrypted:
        from cf_crypto import encrypt as cf_encrypt, decrypt as cf_decrypt, unprotect_windows
        key_path = root / 'cfdb-key.dpapi'
        require(key_path.is_file(), 'Brak lokalnego klucza cfdb-key.dpapi. Skonfiguruj stanowisko.')
        cf_key = unprotect_windows(key_path.read_bytes())
        require(len(cf_key) == 32, 'Nieprawidlowy klucz CFDB.')
    def db_decode(raw):
        return decode_database(cf_decrypt(raw, cf_key) if encrypted else raw)
    def db_encode(data):
        plain = encode(data)
        return cf_encrypt(plain, cf_key) if encrypted else plain
    return db_decode, db_encode


def make_server(root, port, control_token=None):
    config_path = root / 'config.json'
    if not config_path.exists():
        atomic_write(config_path, encode(DEFAULT_CONFIG))
    config = json.loads(config_path.read_text(encoding='utf-8-sig'))
    require(isinstance(config, dict), 'Konfiguracja musi być obiektem JSON.')
    config['service'] = validate_service(config.get('service', {}))
    filename = config.get('database', DEFAULT_CONFIG['database'])
    require(isinstance(filename, str) and filename.lower().endswith(('.json', '.cfdb'))
            and len(filename) <= 1024 and filename.strip(), 'Nieprawidłowa ścieżka bazy.')
    database = Path(filename)
    if not database.is_absolute():
        database = root / filename
    # On Windows, UNC paths (\\SERVER\share\data.json) are absolute.
    require(database.name.lower() not in ('config.json',), 'Nieprawidłowa nazwa bazy.')
    require(database.parent.is_dir(), 'Nie znaleziono folderu wspólnej bazy: ' + str(database.parent))
    require(not database.is_symlink(), 'Baza nie może być dowiązaniem symbolicznym.')
    encrypted = database.suffix.lower() == ".cfdb"
    db_decode, db_encode = database_codec(root, database)
    backup_dir = database.parent / 'backups'
    owner = getpass.getuser() + ' @ ' + socket.gethostname()
    auth_sessions = LoginSessions()
    local_leases = set()  # (resource, token hash) claimed through this local server

    selected_port = config.get('port', 8765) if port is None else port
    require(type(selected_port) is int and 0 <= selected_port <= 65535, 'Nieprawidłowy port.')

    def backup(raw):
        if raw is None:
            return None
        db_decode(raw)  # Never rotate good copies on invalid input.
        backup_dir.mkdir(exist_ok=True)
        name = database.stem + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + database.suffix
        atomic_write(backup_dir / name, raw)
        require((backup_dir / name).read_bytes() == raw, 'Weryfikacja zapisu kopii nie powiodła się.')
        atomic_write(database.with_name(database.name + '.bak'), raw)
        # Keep the newest 30 for this database only.
        for p in sorted(backup_dir.glob(database.stem + '-*' + database.suffix), reverse=True)[30:]:
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
            data = db_decode(raw)
            return data, content_revision(data), raw

        def snapshot(self):
            data, rev, raw = self.current()
            if data is None:
                data = deepcopy(EMPTY_DB)
                rev = content_revision(data)
            return data, rev, raw

        def shared_service(self, data):
            return validate_service(data.get('serviceConfig', config['service']))

        def respond_problem(self, error):
            code = 423 if isinstance(error, LockedError) else 409 if isinstance(error, ConflictError) else 400
            return self.respond(code, {'error': str(error)})

        def request_payload(self, limit=65536):
            try:
                length = int(self.headers.get('Content-Length', '0'))
            except ValueError:
                raise ValueError('Nieprawidłowa długość żądania.')
            require(0 < length <= limit, 'Nieprawidłowy rozmiar danych.')
            value = json.loads(self.rfile.read(length))
            require(isinstance(value, dict), 'Oczekiwano danych JSON.')
            return value

        def current_user(self, data, permission=None, allow_password_change=False, refresh_session=True):
            token = self.headers.get('X-SSP-Session', '')
            user = auth_sessions.user_for(token, data['users'], refresh=refresh_session)
            if not user:
                raise PermissionError('Wymagane logowanie lub sesja wygasła.')
            if user.get('mustChangePassword') and not allow_password_change:
                raise PermissionError('Najpierw zmień hasło początkowe.')
            if permission and permission not in permissions_for(user):
                raise PermissionError('Brak uprawnienia: ' + PERMISSIONS[permission])
            return user

        def current_admin(self, data):
            user = self.current_user(data)
            if user['role'] != 'ADMIN':
                raise PermissionError('Operacje na bazie danych są dostępne tylko dla administratora.')
            return user

        def client_database(self, data, user):
            result = deepcopy(data)
            result.pop('users', None)
            perms = permissions_for(user)
            for collection, permission in [('panels', 'panels.view'), ('faults', 'faults.view'),
                                           ('history', 'protocols.view'), ('costs', 'protocols.view'), ('audit', 'audit.view')]:
                if permission not in perms:
                    result[collection] = []
            # The hash of another editor's random lock token is internal state.
            # Do not leak names or record identifiers for areas this user
            # cannot even view. Session tokens and user IDs never leave server.
            def may_view_lock(key):
                section = key.partition('/')[0]
                needed = {'panels': 'panels.view', 'faults': 'faults.view',
                          'history': 'protocols.view', 'settings': 'settings.view'}
                return ((key == 'import' and user['role'] == 'ADMIN')
                        or (section in needed and needed[section] in perms))
            result['activeSessions'] = {key: {'owner': v['owner'], 'lastActivity': v['lastActivity']}
                                        for key, v in result.get('activeSessions', {}).items()
                                        if may_view_lock(key)}
            return result

        def require_changes_allowed(self, old, proposed, user):
            perms = set(permissions_for(user))
            for collection, permission in [('panels', 'panels.edit'), ('faults', 'faults.edit'),
                                           ('history', 'protocols.edit'), ('costs', 'protocols.edit')]:
                before = {item['id']: item for item in old[collection]}
                after = {item['id']: item for item in proposed[collection]}
                if before != after and permission not in perms:
                    raise PermissionError('Brak uprawnienia: ' + PERMISSIONS[permission])
            old_history = {item['id']: item for item in old['history']}
            for item in proposed['history']:
                previous = old_history.get(item['id'])
                if (item.get('protocolStatus') == 'final' and
                        (previous is None or previous.get('protocolStatus') != 'final') and
                        'protocols.finalize' not in perms):
                    raise PermissionError('Brak uprawnienia do zatwierdzania protokołów.')

        def append_security_audit(self, data, actor, action, details):
            data.setdefault('audit', []).append({'date': datetime.now().astimezone().isoformat(timespec='seconds'),
                                                'action': action, 'user': actor['displayName'],
                                                'userId': actor['id'], 'details': [details]})
            data['audit'] = data['audit'][-1000:]

        def respond_auth_error(self, error):
            return self.respond(401 if 'logowanie' in str(error).lower() or 'wygasła' in str(error).lower()
                                or 'zmień hasło' in str(error).lower() else 403, {'error': str(error)})

        def authorized_control(self):
            supplied = self.headers.get('X-SSP-Control', '')
            return (bool(control_token) and self.trusted()
                    and secrets.compare_digest(supplied, control_token))

        def do_GET(self):
            if not self.trusted():
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            if self.path == '/__control/database-health':
                if not self.authorized_control():
                    return self.respond(403, {'error': 'Brak dostępu do sterowania.'})
                try:
                    with database_mutex(database):
                        self.snapshot()
                    return self.respond(200, {'ok': True})
                except (OSError, ValueError) as error:
                    return self.respond(500, {'error': 'Nie można odczytać bazy: ' + str(error)})
            if self.path == '/__control/status':
                if not self.authorized_control():
                    return self.respond(403, {'error': 'Brak dostępu do sterowania.'})
                return self.respond(200, {'running': True, 'pid': os.getpid(),
                                          'version': VERSION, 'root': str(root.resolve()),
                                          'port': self.server.server_port,
                                          'localEditors': len(local_leases)})
            try:
                if self.path == '/api/auth/setup':
                    with database_mutex(database):
                        data, _, _ = self.snapshot()
                        return self.respond(200, {'needsAdmin': not bool(data['users'])})
                if self.path == '/api/auth/me':
                    with database_mutex(database):
                        data, _, _ = self.snapshot()
                        user = self.current_user(data, allow_password_change=True)
                        return self.respond(200, {'user': public_user(user),
                                                  'permissions': PERMISSIONS, 'roles': ROLE_DEFAULTS})
                files = {'/': ('index.html', 'text/html'), '/index.html': ('index.html', 'text/html'),
                         '/app.js': ('app.js', 'text/javascript'), '/style.css': ('style.css', 'text/css'),
                         '/favicon.ico': ('favicon.ico', 'image/x-icon'),
                         '/favicon.png': ('favicon.png', 'image/png'),
                         '/licencja': ('licencja.html', 'text/html'),
                         '/licencja.html': ('licencja.html', 'text/html')}
                # Only explicit public files are served; never expose the database or config.
                static_path = self.path.partition('?')[0]
                if static_path in files:
                    name, mime = files[static_path]
                    if mime.startswith('image/'):
                        return self.respond(200, (root / name).read_bytes(), mime)
                    return self.respond(200, (root / name).read_bytes(), mime + '; charset=utf-8')
                with database_mutex(database):
                    data, rev, _ = self.snapshot()
                    user = self.current_user(data, refresh_session=self.path != '/api/sync')
                    if self.path == '/api/sync':
                        # The 5-second background check must NOT renew the login
                        # idle timer, and must never touch/renew editor leases.
                        # Return small metadata; transfer full data only on change.
                        sessions(data)
                        visible = self.client_database(data, user)
                        return self.respond(200, {
                            'revision': content_revision(visible),
                            'configRevision': service_revision(self.shared_service(data)),
                            'locks': visible['activeSessions'],
                        })
                    if self.path == '/api/database':
                        sessions(data)
                        visible = self.client_database(data, user)
                        return self.respond(200, {'database': visible,
                                                  'revision': content_revision(visible)})
                    if self.path == '/api/config':
                        service = self.shared_service(data)
                        return self.respond(200, {'service': service, 'revision': service_revision(service),
                                                 'version': VERSION, 'database': str(database)})
                    if self.path == '/api/users':
                        self.current_user(data, 'users.manage')
                        return self.respond(200, {'users': [public_user(u) for u in data['users']],
                                                  'permissions': PERMISSIONS, 'roles': ROLE_DEFAULTS})
                    if self.path.startswith('/api/backups'):
                        self.current_admin(data)
                    if self.path == '/api/backups':
                        items = sorted(backup_dir.glob(database.stem + '-*' + database.suffix), reverse=True) if backup_dir.exists() else []
                        return self.respond(200, [inspect_backup(p, db_decode) for p in items])
                    if self.path.startswith('/api/backups/'):
                        name = self.path[len('/api/backups/'):]
                        require('/' not in name and '\\' not in name and name.startswith(database.stem + '-')
                                and name.endswith(database.suffix), 'Nieprawidłowa kopia.')
                        path = backup_dir / name
                        require(not path.is_symlink(), 'Nieprawidłowa kopia.')
                        require(inspect_backup(path, db_decode)['valid'], 'Ta kopia jest uszkodzona. Nie można jej pobrać do odtworzenia.')
                        return self.respond(200, path.read_bytes())
                return self.respond(404, {'error': 'Nie znaleziono.'})
            except PermissionError as error:
                self.respond_auth_error(error)
            except (ValueError, OSError) as error:
                self.respond(500, {'error': 'Nie można odczytać danych: ' + str(error)})

        def do_POST(self):
            if self.path == '/__control/stop':
                if not self.authorized_control():
                    return self.respond(403, {'error': 'Brak dostępu do sterowania.'})
                self.respond(200, {'stopping': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            if not self.trusted(write=True):
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            if self.path in ('/api/auth/login', '/api/auth/logout', '/api/auth/change-password', '/api/users'):
                try:
                    payload = self.request_payload(8192)
                    with database_mutex(database):
                        data, _, raw = self.snapshot()
                        if self.path == '/api/auth/login':
                            if not data['users']:
                                raise ValueError('Najpierw utwórz pierwszego administratora przez kreator.')
                            token, user = auth_sessions.authenticate(data['users'],
                                                                     payload.get('username', ''), payload.get('password', ''))
                            return self.respond(200, {'token': token, 'user': public_user(user),
                                                      'permissions': PERMISSIONS, 'roles': ROLE_DEFAULTS})
                        if self.path == '/api/auth/logout':
                            auth_sessions.logout(self.headers.get('X-SSP-Session', ''))
                            return self.respond(200, {'ok': True})
                        if self.path == '/api/auth/change-password':
                            user = self.current_user(data, allow_password_change=True)
                            if not verify_password(user, payload.get('oldPassword', '')):
                                raise PermissionError('Nieprawidłowe dotychczasowe hasło.')
                            user.update(password_record(payload.get('newPassword')))
                            user['mustChangePassword'] = False
                            record_account_change(user)
                            data['activeSessions'] = {k:v for k,v in data.get('activeSessions', {}).items() if v.get('userId') != user['id']}
                            self.append_security_audit(data, user, 'Zmiana hasła', 'Użytkownik zmienił swoje hasło.')
                            backup(raw)
                            atomic_write(database, db_encode(data))
                            auth_sessions.logout(self.headers.get('X-SSP-Session', ''))
                            return self.respond(200, {'ok': True, 'loginAgain': True})
                        actor = self.current_user(data, 'users.manage')
                        action = payload.get('action')
                        users = data['users']
                        target = next((u for u in users if u['id'] == payload.get('id')), None)
                        if action == 'create':
                            new = new_user(payload.get('username'), payload.get('displayName'),
                                           payload.get('password'), payload.get('role'),
                                           payload.get('permissions'), True)
                            if any(u['username'] == new['username'] for u in users):
                                raise ValueError('Ten login jest już zajęty.')
                            users.append(new)
                            detail = 'Utworzono konto: ' + new['username']
                        elif action == 'update':
                            if not target:
                                raise ValueError('Nie znaleziono konta.')
                            role = payload.get('role')
                            perms = payload.get('permissions')
                            if role not in ROLE_DEFAULTS or not isinstance(perms, list) or not set(perms) <= set(PERMISSIONS):
                                raise ValueError('Nieprawidłowa rola lub uprawnienia.')
                            display = payload.get('displayName')
                            if not isinstance(display, str) or not 1 <= len(display.strip()) <= 120:
                                raise ValueError('Nieprawidłowe imię i nazwisko.')
                            if not isinstance(payload.get('enabled'), bool):
                                raise ValueError('Nieprawidłowy status konta.')
                            target.update(displayName=display.strip(), role=role, permissions=list(dict.fromkeys(perms)),
                                          enabled=payload['enabled'])
                            if active_admins(users) == 0:
                                raise ValueError('Nie można wyłączyć ostatniego aktywnego administratora.')
                            record_account_change(target)
                            detail = 'Zmieniono konto: ' + target['username']
                        elif action == 'reset-password':
                            if not target:
                                raise ValueError('Nie znaleziono konta.')
                            target.update(password_record(payload.get('password')))
                            target['mustChangePassword'] = True
                            record_account_change(target)
                            detail = 'Zresetowano hasło konta: ' + target['username']
                        else:
                            raise ValueError('Nieznana operacja zarządzania kontem.')
                        if target and action in ('update', 'reset-password'):
                            data['activeSessions'] = {k:v for k,v in data.get('activeSessions', {}).items() if v.get('userId') != target['id']}
                        self.append_security_audit(data, actor, 'Zarządzanie użytkownikami', detail)
                        validate_users(data)
                        backup(raw)
                        atomic_write(database, db_encode(data))
                        return self.respond(200, {'users': [public_user(u) for u in users]})
                except PermissionError as error:
                    return (self.respond(401, {'error': str(error)}) if self.path == '/api/auth/login'
                            else self.respond_auth_error(error))
                except (ValueError, TypeError, OSError, UnicodeEncodeError) as error:
                    return self.respond(400, {'error': str(error)})
            if self.path == '/api/import-cfdb-decode':
                try:
                    require(encrypted, 'Import CFDB wymaga aktywnej bazy CFDB.')
                    payload = self.request_payload(28 * 1024 * 1024)
                    with database_mutex(database):
                        current, _, _ = self.snapshot()
                        self.current_admin(current)
                    encoded = payload.get('file')
                    require(isinstance(encoded, str) and len(encoded) <= 28 * 1024 * 1024,
                            'Nieprawidłowy rozmiar pliku CFDB.')
                    raw = base64.b64decode(encoded, validate=True)
                    require(len(raw) <= 20 * 1024 * 1024, 'Limit importu wynosi 20 MB.')
                    proposed = validate_database(db_decode(raw))
                    # Never return imported account hashes or active sessions to the browser.
                    proposed.pop('users', None)
                    proposed.pop('activeSessions', None)
                    proposed.pop('serviceConfig', None)
                    return self.respond(200, {'database': proposed})
                except PermissionError as error:
                    return self.respond_auth_error(error)
                except (ValueError, TypeError, KeyError, OSError, binascii.Error) as error:
                    return self.respond_problem(error)
            if self.path == '/api/import-preview':
                try:
                    payload = self.request_payload(20 * 1024 * 1024)
                    with database_mutex(database):
                        data, _, _ = self.snapshot()
                        self.current_admin(data)
                        proposed = validate_database(payload.get('database'))
                        return self.respond(200, {'summary': database_summary(proposed),
                            'current': database_summary(data), 'configurationPreserved': True, 'accountsPreserved': True})
                except PermissionError as error:
                    return self.respond_auth_error(error)
                except (ValueError, TypeError, KeyError, OSError) as error:
                    return self.respond_problem(error)
            if self.path not in ('/api/backup', '/api/lock'):
                return self.respond(404, {'error': 'Nie znaleziono.'})
            try:
                payload = {}
                if self.path == '/api/lock':
                    length = int(self.headers.get('Content-Length', '0'))
                    require(0 < length <= 2048, 'Nieprawidłowe żądanie blokady.')
                    payload = json.loads(self.rfile.read(length))
                    require(isinstance(payload, dict), 'Nieprawidłowe dane blokady.')
                with database_mutex(database):
                    data, _, raw = self.snapshot()
                    if self.path == '/api/backup':
                        self.current_admin(data)
                        return self.respond(200, {'name': backup(raw)})
                    resource = checked_resource(payload.get('resource'))
                    permission = ('panels.edit' if resource.startswith('panels/') else
                                  'faults.edit' if resource.startswith('faults/') else
                                  'protocols.edit' if resource.startswith('history/') else
                                  'settings.edit' if resource == 'settings' else 'backups.manage')
                    if resource.startswith('panels/'):
                        actor = self.current_user(data)
                        require_permissions = set(permissions_for(actor))
                        if not ({'panels.edit', 'protocols.edit'} & require_permissions):
                            raise PermissionError('Brak uprawnienia do edycji centrali lub przygotowania przeglądu.')
                    else:
                        actor = self.current_admin(data) if resource == 'import' else self.current_user(data, permission)
                    state = sessions(data)
                    token = token_digest(payload.get('token'))
                    action = payload.get('action')
                    current = state.get(resource)
                    if current and current.get('userId') not in (None, actor['id']):
                        raise LockedError('Rekord edytuje inne konto: ' + current['owner'])
                    if action == 'claim':
                        if resource == 'import' and any(key != resource for key in state):
                            raise LockedError('Inni użytkownicy edytują dane. Import jest zablokowany.')
                        if resource != 'import' and 'import' in state:
                            raise LockedError('Trwa import wspólnej bazy. Spróbuj później.')
                        if current and current['tokenHash'] != token:
                            raise LockedError('Rekord jest aktualnie edytowany przez: ' + current['owner'] + '.')
                        state[resource] = {'owner': actor['displayName'] + ' @ ' + socket.gethostname(), 'userId': actor['id'], 'tokenHash': token, 'lastActivity': time.time()}
                    elif action == 'touch':
                        check_edit_lock(state, resource, payload.get('token'))
                        state[resource]['lastActivity'] = time.time()
                    elif action == 'release':
                        if current and current['tokenHash'] == token:
                            del state[resource]
                    else:
                        raise ValueError('Nieznane działanie blokady.')
                    if raw is None and action == 'release' and not current:
                        return self.respond(200, {'released': True})
                    atomic_write(database, db_encode(data))
                    key = (resource, token)
                    if action == 'claim':
                        local_leases.add(key)
                    elif action == 'release':
                        local_leases.discard(key)
                    return self.respond(200, {'resource': resource, 'owner': actor['displayName'],
                                             'expiresAfterSeconds': 1800, 'released': action == 'release'})
            except PermissionError as error:
                return self.respond_auth_error(error)
            except (LockedError, ConflictError, ValueError, OSError, TypeError) as error:
                return self.respond_problem(error)

        def do_PUT(self):
            if not self.trusted(write=True):
                return self.respond(403, {'error': 'Niedozwolone źródło żądania.'})
            if self.path not in ('/api/database', '/api/config'):
                return self.respond(404, {'error': 'Nie znaleziono.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 64 * 1024 * 1024:
                    return self.respond(413, {'error': 'Limit żądania wynosi 64 MB; baza do 20 MB.'})
                payload = json.loads(self.rfile.read(length))
                require(isinstance(payload, dict) and 'revision' in payload, 'Brak wersji danych.')
                with database_mutex(database):
                    current, rev, raw = self.snapshot()
                    actor = self.current_user(current)
                    state = sessions(current)
                    token = payload.get('token', '')
                    if token:
                        digest = token_digest(token)
                        if any(lease.get('tokenHash') == digest and lease.get('userId') not in (None, actor['id'])
                               for lease in state.values()):
                            raise LockedError('Ta blokada należy do innego konta.')
                    # Import is a global exclusive operation. Even insertion of a
                    # *new* row (which normally needs no per-record lease) must
                    # not modify the file while an import is being prepared.
                    if 'import' in state and not (
                            self.path == '/api/database' and payload.get('mode') == 'replace'
                            and own_lease(state, 'import', token)):
                        raise LockedError('Trwa import wspólnej bazy. Inne zapisy są teraz zablokowane.')
                    if self.path == '/api/config':
                        self.current_user(current, 'settings.edit')
                        check_edit_lock(state, 'settings', token)
                        previous = self.shared_service(current)
                        if payload['revision'] != service_revision(previous):
                            raise ConflictError('Inny użytkownik zmienił konfigurację. Odśwież stronę.')
                        saved = validate_service(payload.get('service'))
                        current['serviceConfig'] = saved
                        backup(raw)
                        atomic_write(database, db_encode(current))
                        return self.respond(200, {'service': saved, 'revision': service_revision(saved)})
                    incoming = validate_database(payload.get('database'), partial=payload.get('mode') != 'replace')
                    replace = payload.get('mode') == 'replace'
                    if replace:
                        self.current_admin(current)
                        check_edit_lock(state, 'import', token)
                        require(not any(k != 'import' for k in state), 'Inni użytkownicy edytują bazę.')
                        if payload['revision'] != rev:
                            raise ConflictError('Baza zmieniła się. Odśwież stronę przed importem.')
                        proposed = incoming
                        proposed['activeSessions'] = state
                        proposed['users'] = deepcopy(current['users'])
                        proposed['serviceConfig'] = current.get('serviceConfig', config['service'])
                    else:
                        base = validate_database(payload.get('base'), partial=True)
                        # Verify client did not silently modify a stale baseline.
                        require(payload['revision'] == content_revision(base), 'Błąd wersji formularza.')
                        require(payload['revision'] is None or rev is not None, 'Baza nie została jeszcze utworzona.')
                        proposed = merge_changed_rows(current, base, incoming, state, token)
                    proposed = validate_database(proposed)
                    if not replace:
                        self.require_changes_allowed(current, proposed, actor)
                    if not replace:
                        # Protocol approval may alter a panel or a linked fault even
                        # though the incoming changes only touch the protocol.
                        old_history = {h['id']: h for h in current['history']}
                        for protocol in proposed['history']:
                            before = old_history.get(protocol['id'])
                            if protocol.get('protocolStatus') == 'final' and (not before or before.get('protocolStatus') != 'final'):
                                for resource in ['panels/' + protocol['panelId']] + (
                                        ['faults/' + protocol['faultId']] if protocol.get('faultId') else []):
                                    lease = state.get(resource)
                                    if lease and lease['tokenHash'] != token_digest(token):
                                        raise LockedError('Nie można zatwierdzić protokołu — ' +
                                                          resource + ' edytuje ' + lease['owner'])
                    proposed = apply_workflow(proposed, current if raw else None, self.shared_service(current), replace=replace, actor=actor)
                    proposed['activeSessions'] = state
                    proposed['users'] = deepcopy(current['users'])
                    proposed['serviceConfig'] = current.get('serviceConfig', config['service'])
                    content = db_encode(proposed)
                    require(len(content) <= 20 * 1024 * 1024, 'Baza przekracza 20 MB. Zmniejsz załączniki.')
                    backup(raw)
                    atomic_write(database, content)
                    return self.respond(200, {'revision': content_revision(self.client_database(proposed, actor)),
                                              'database': self.client_database(proposed, actor)})
            except PermissionError as error:
                self.respond_auth_error(error)
            except (LockedError, ConflictError, ValueError, OSError, TypeError) as error:
                self.respond_problem(error)

    server = HTTPServer(('127.0.0.1', selected_port), Handler)
    server.timeout = 10

    def clean_local_leases():
        # A normal Stop/Ctrl+C releases leases belonging to this local process.
        # Crash/network outage still relies on the original 30-minute expiry.
        if not local_leases or not database.exists():
            return
        with database_mutex(database):
            raw = database.read_bytes()
            data = db_decode(raw)
            state = sessions(data)
            old_count = len(state)
            for resource, digest in local_leases:
                if resource in state and state[resource]['tokenHash'] == digest:
                    del state[resource]
            if len(state) != old_count:
                atomic_write(database, db_encode(data))

    server.clean_local_leases = clean_local_leases
    return server, config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--port', type=int)
    args = parser.parse_args()
    try:
        server, config = make_server(ROOT, args.port, os.environ.pop('SSP_CONTROL_TOKEN', None))
        url = 'http://127.0.0.1:' + str(server.server_port)
        print('CommandFIRE SSP Serwis ' + VERSION + ': ' + url + '\nAby zakończyć pracę, użyj Zatrzymaj_SSP_Polon.vbs lub Ctrl+C.', flush=True)
        if config.get('open_browser', True) and not args.no_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            try:
                server.clean_local_leases()
            except (OSError, ValueError) as error:
                print('Nie udało się zwolnić blokad przy zamykaniu: ' + str(error), flush=True)
            server.server_close()
    except (OSError, ValueError) as error:
        print('Nie można uruchomić aplikacji: ' + str(error))
        raise SystemExit(1)


if __name__ == '__main__':
    main()
