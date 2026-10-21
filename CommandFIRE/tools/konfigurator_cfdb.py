"""CommandFIRE workstation provisioning. JSON on stdin, JSON on stdout; never log keys."""
import json, os, sys, secrets, datetime, base64
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cf_crypto import encrypt,decrypt,protect_windows,unprotect_windows
from server import atomic_write, database_mutex,decode_database,encode,DEFAULT_CONFIG
from auth_users import new_user

def run(req):
    # Serialize local configuration, including key creation.
    with database_mutex(ROOT / "config.json"):
        return _run(req)

def _run(req):
    configpath=ROOT/"config.json"
    config=json.loads(configpath.read_text(encoding="utf-8-sig")) if configpath.exists() else dict(DEFAULT_CONFIG)
    if not isinstance(config,dict):raise ValueError("Konfiguracja musi być obiektem JSON.")
    action=req.get('action')
    target=Path(req.get('path','').strip().strip('"'))
    if action not in ('new','join','migrate') or not target.is_absolute():
        raise ValueError('Wybierz operacje i pelna sciezke do pliku CFDB.')
    if not target.suffix: target=target.with_suffix('.cfdb')
    if target.suffix.lower()!='.cfdb':raise ValueError('Plik docelowy musi miec rozszerzenie .cfdb.')
    if not target.parent.is_dir():raise ValueError('Folder bazy nie istnieje.')
    keyfile=ROOT/'cfdb-key.dpapi'
    if action=='join':
        if not target.is_file():raise FileNotFoundError('Nie znaleziono wskazanej bazy CFDB.')
        key=bytes.fromhex(req.get('key','').strip())
        if len(key)!=32:raise ValueError('Klucz musi miec 64 znaki HEX.')
        with database_mutex(target):decode_database(decrypt(target.read_bytes(),key))
    else:
        if target.exists():raise FileExistsError('Baza CFDB juz istnieje. Nie nadpisuje.')
        if keyfile.exists():raise FileExistsError('Istnieje lokalny klucz DPAPI. Nie tworz nowej bazy w tej instalacji.')
        if action=='migrate':
            source=Path(req.get('source','').strip().strip('"'))
            if not source.is_file() or source.suffix.lower()!='.json':raise ValueError('Wskaz istniejaca baze JSON.')
            with database_mutex(source):
                plain=source.read_bytes();decode_database(plain)
                backup=source.with_name(source.name+'.przed-cfdb-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.bak')
                atomic_write(backup,plain)
                if backup.read_bytes()!=plain:raise OSError('Kopia JSON nie przeszla weryfikacji.')
        else:
            # New DB uses the same validated schema as server first-run initialization.
            from server import EMPTY_DB
            data=deepcopy(EMPTY_DB)
            admin=req.get('admin')
            if not isinstance(admin,dict):raise ValueError('Nowa baza wymaga utworzenia administratora.')
            password_hex=admin.get('password_hex','').strip().lstrip('\ufeff')
            if not isinstance(password_hex,str) or not password_hex or len(password_hex)%2 or any(c not in '0123456789abcdefABCDEF' for c in password_hex):
                raise ValueError('Nieprawidlowe dane hasla z okna kreatora. Uruchom konfigurator ponownie.')
            password=bytes.fromhex(password_hex).decode('utf-8')
            if not 12 <= len(password) <= 128:
                raise ValueError('Haslo administratora musi miec 12-128 znakow.')
            data['users']=[new_user(admin.get('username',''),admin.get('display',''),password,'ADMIN',must_change=False)]
            plain=encode(data)
            decode_database(plain)
        key=secrets.token_bytes(32)
        # Protect and persist the key BEFORE creating any encrypted database.
        # A later write failure leaves a recoverable local key, never an orphan CFDB.
        protected=protect_windows(key)
        with database_mutex(target):
            if target.exists():raise FileExistsError('Baza juz istnieje.')
            atomic_write(keyfile,protected)
            atomic_write(target,encrypt(plain,key))
            decode_database(decrypt(target.read_bytes(),key))
    if keyfile.exists():
        if unprotect_windows(keyfile.read_bytes())!=key:raise ValueError('Lokalny klucz dotyczy innej bazy.')
    else:atomic_write(keyfile,protect_windows(key))
    if configpath.exists():
        backup=configpath.with_name('config.json.przed-konfiguracja.bak')
        if not backup.exists():atomic_write(backup,configpath.read_bytes())
    config['database']=str(target)
    atomic_write(configpath,json.dumps(config,ensure_ascii=False,indent=2).encode('utf-8'))
    return {'ok':True,'message':'Stanowisko skonfigurowane. Uruchom CommandFIRE.', 'recovery':key.hex() if action!='join' else None}

if __name__=='__main__':
    try:
        if os.name!='nt':raise OSError('Konfigurator DPAPI dziala tylko na Windows.')
        print(json.dumps(run(json.loads(sys.stdin.readline())),ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'ok':False,'message':str(exc)},ensure_ascii=False))
        sys.exit(1)
