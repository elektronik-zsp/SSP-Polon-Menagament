"""Local-session authentication and shared-JSON user records for CommandFIRE SSP Serwis.

The browser never receives password hashes. Account records live in the same SMB
file as other data, protected by the cross-host database mutex in server.py.
"""
import hashlib
import hmac
import re
import secrets
import time
import uuid
from datetime import datetime

PERMISSIONS = {
    'dashboard.view': 'Pulpit i wskaźniki',
    'panels.view': 'Podgląd central',
    'panels.edit': 'Dodawanie i edycja central',
    'faults.view': 'Podgląd zgłoszeń i historii działań',
    'faults.edit': 'Obsługa zgłoszeń i zmiana statusów',
    'protocols.view': 'Podgląd protokołów i przeglądów',
    'protocols.edit': 'Tworzenie i edycja szkiców',
    'protocols.finalize': 'Zatwierdzanie protokołów i przeglądów',
    'settings.view': 'Podgląd konfiguracji',
    'settings.edit': 'Zmiana konfiguracji i numeracji',
    'backups.view': 'Przeglądanie kopii (tylko ADMIN)',
    'backups.manage': 'Eksport, kopie i import (tylko ADMIN)',
    'audit.view': 'Podgląd dziennika zmian',
    'users.manage': 'Zarządzanie użytkownikami (tylko administrator)',
}
ROLE_DEFAULTS = {
    'ADMIN': list(PERMISSIONS),
    'SERWISANT': ['dashboard.view', 'panels.view', 'faults.view', 'faults.edit',
                  'protocols.view', 'protocols.edit', 'settings.view'],
    'DYSPOZYTOR': ['dashboard.view', 'panels.view', 'faults.view', 'faults.edit',
                   'protocols.view', 'settings.view'],
    'ODCZYT': ['dashboard.view', 'panels.view', 'faults.view',
               'protocols.view', 'settings.view'],
}
ADMIN_ONLY_PERMISSIONS = {'users.manage', 'backups.view', 'backups.manage'}
PASSWORD_ITERATIONS = 350_000
SESSION_IDLE_SECONDS = 8 * 3600


def check_username(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9._-]{3,40}', value):
        raise ValueError('Login: 3–40 znaków (litery bez polskich znaków, cyfry, kropka, _ lub -).')
    return value.lower()


def check_password(password):
    if not isinstance(password, str) or len(password) < 12 or len(password) > 128:
        raise ValueError('Hasło musi mieć od 12 do 128 znaków.')
    if password.isspace():
        raise ValueError('Hasło nie może składać się wyłącznie z odstępów.')


def password_record(password):
    check_password(password)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, PASSWORD_ITERATIONS)
    return {'salt': salt.hex(), 'passwordHash': digest.hex(), 'iterations': PASSWORD_ITERATIONS}


def verify_password(user, password):
    if not isinstance(password, str) or len(password) > 128:
        return False
    try:
        iters = user['iterations']
        if not isinstance(iters, int) or not 100_000 <= iters <= 1_000_000:
            return False
        result = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                      bytes.fromhex(user['salt']), iters)
        return hmac.compare_digest(result, bytes.fromhex(user['passwordHash']))
    except (KeyError, ValueError, TypeError):
        return False


def permissions_for(user):
    if user['role'] == 'ADMIN':
        return list(PERMISSIONS)
    return [key for key in user.get('permissions', []) if key in PERMISSIONS and key not in ADMIN_ONLY_PERMISSIONS]


def public_user(user):
    return {key: user.get(key) for key in
            ('id', 'username', 'displayName', 'role', 'enabled', 'mustChangePassword', 'createdAt', 'updatedAt') } | {
                'permissions': permissions_for(user)}


def validate_users(data):
    users = data.setdefault('users', [])
    if not isinstance(users, list) or len(users) > 300:
        raise ValueError('Nieprawidłowa lista użytkowników.')
    names = set()
    ids = set()
    for user in users:
        if not isinstance(user, dict):
            raise ValueError('Nieprawidłowy wpis użytkownika.')
        name = check_username(user.get('username'))
        if name in names or not isinstance(user.get('id'), str) or user['id'] in ids:
            raise ValueError('Zduplikowane konto użytkownika.')
        names.add(name)
        ids.add(user['id'])
        if not isinstance(user.get('displayName'), str) or not (1 <= len(user['displayName'].strip()) <= 120):
            raise ValueError('Nieprawidłowe imię i nazwisko użytkownika.')
        if user.get('role') not in ROLE_DEFAULTS or not isinstance(user.get('enabled'), bool):
            raise ValueError('Nieprawidłowa rola lub stan konta.')
        if not isinstance(user.get('permissions'), list) or len(set(user['permissions'])) != len(user['permissions']) or not set(user['permissions']) <= set(PERMISSIONS):
            raise ValueError('Nieprawidłowe uprawnienia użytkownika.')
        if not isinstance(user.get('salt'), str) or not isinstance(user.get('passwordHash'), str):
            raise ValueError('Nieprawidłowe hasło użytkownika.')
        if not isinstance(user.get('authVersion'), int) or not isinstance(user.get('mustChangePassword'), bool):
            raise ValueError('Nieprawidłowa wersja autoryzacji konta.')
    return users


def new_user(username, display_name, password, role, permissions=None, must_change=True):
    username = check_username(username)
    if not isinstance(display_name, str):
        raise ValueError('Podaj imię i nazwisko użytkownika.')
    display_name = display_name.strip()
    if not (1 <= len(display_name) <= 120):
        raise ValueError('Podaj imię i nazwisko (1–120 znaków).')
    if role not in ROLE_DEFAULTS:
        raise ValueError('Nieprawidłowa rola.')
    chosen = list(ROLE_DEFAULTS[role] if permissions is None else permissions)
    if len(set(chosen)) != len(chosen) or not set(chosen) <= set(PERMISSIONS):
        raise ValueError('Nieprawidłowe uprawnienia.')
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    return {'id': 'USR-' + uuid.uuid4().hex, 'username': username, 'displayName': display_name,
            'role': role, 'permissions': chosen, 'enabled': True,
            'mustChangePassword': bool(must_change), 'authVersion': 1,
            'createdAt': now, 'updatedAt': now, **password_record(password)}


def record_account_change(user):
    user['authVersion'] += 1
    user['updatedAt'] = datetime.now().astimezone().isoformat(timespec='seconds')


def active_admins(users):
    return sum(1 for u in users if u['role'] == 'ADMIN' and u['enabled'])


class LoginSessions:
    """Session tokens live only in memory of the local server, never on the SMB share."""
    def __init__(self):
        self.entries = {}
        self.attempts = {}

    def authenticate(self, users, username, password):
        name = check_username(username)
        if not isinstance(password, str) or len(password) > 128:
            raise PermissionError('Nieprawidłowy login lub hasło.')
        now = time.monotonic()
        attempts = [t for t in self.attempts.get(name, []) if now - t < 600]
        if len(attempts) >= 6:
            raise PermissionError('Za dużo prób. Spróbuj ponownie za 10 minut.')
        user = next((u for u in users if u['username'] == name and u['enabled']), None)
        # Do comparable hashing for nonexistent users, avoiding trivial user enumeration.
        if not user:
            hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), b'\x00'*16, PASSWORD_ITERATIONS)
        if not user or not verify_password(user, password):
            attempts.append(now)
            self.attempts[name] = attempts
            raise PermissionError('Nieprawidłowy login lub hasło.')
        self.attempts.pop(name, None)
        token = secrets.token_urlsafe(32)
        self.entries[token] = {'id': user['id'], 'version': user['authVersion'], 'last': now}
        return token, user

    def user_for(self, token, users, refresh=True):
        if not token:
            return None
        entry = self.entries.get(token)
        if not entry:
            return None
        now = time.monotonic()
        if now - entry['last'] >= SESSION_IDLE_SECONDS:
            self.entries.pop(token, None)
            return None
        user = next((u for u in users if u['id'] == entry['id'] and u['enabled']
                     and u['authVersion'] == entry['version']), None)
        if not user:
            self.entries.pop(token, None)
            return None
        if refresh:
            entry['last'] = now
        return user

    def logout(self, token):
        self.entries.pop(token, None)
