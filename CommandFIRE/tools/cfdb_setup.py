"""Windows-only explicit provisioning and migration. Run only after all stations stop."""
import sys, os, json, secrets, hashlib, getpass, shutil, datetime
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from cf_crypto import encrypt, decrypt, protect_windows
from server import database_mutex, decode_database, atomic_write
ROOT=Path(__file__).resolve().parent.parent

def configure(target):
    config_path=ROOT/'config.json'
    config=json.loads(config_path.read_text(encoding='utf-8-sig')) if config_path.exists() else {}
    if not isinstance(config,dict): raise ValueError('Nieprawidlowy config.json')
    if config_path.exists():
        original=config_path.read_bytes()
        backup=config_path.with_name('config.json.przed-cfdb.bak')
        if not backup.exists(): atomic_write(backup,original)
    config['database']=str(target.resolve())
    atomic_write(config_path,json.dumps(config,ensure_ascii=False,indent=2).encode('utf-8'))
    print('Ustawiono baze w config.json:',target.resolve())

def main():
    if os.name != 'nt': raise OSError('Konfiguracja DPAPI wymaga Windows.')
    print('CommandFIRE 2.12.1 TEST - migracja i konfiguracja. ZAMKNIJ wszystkie stanowiska.')
    print('1 - nowa baza CFDB z JSON; 2 - dodaj stanowisko do istniejacej CFDB')
    action=input('Wybierz 1/2: ').strip()
    # Validate local configuration before any migration writes.
    configpath=ROOT/'config.json'
    if configpath.exists():
        config=json.loads(configpath.read_text(encoding='utf-8-sig'))
        if not isinstance(config,dict):raise ValueError('Nieprawidlowy config.json')
    if action=='1':
        keyfile=ROOT/'cfdb-key.dpapi'
        if keyfile.exists():raise FileExistsError('Lokalny klucz juz istnieje; nie nadpisuje.')
        source=Path(input('Pelna sciezka JSON: ').strip().strip('"'))
        if not source.is_file() or source.suffix.lower() != '.json': raise ValueError('Wybierz istniejaca baze JSON.')
        target=source.with_suffix('.cfdb')
        if target.exists(): raise FileExistsError('CFDB juz istnieje; nie nadpisuje.')
        with database_mutex(source):
            plain=source.read_bytes();decode_database(plain)
            backup=source.with_name(source.name+'.przed-cfdb-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.bak')
            if backup.exists(): raise FileExistsError(backup)
            atomic_write(backup,plain)
            if backup.read_bytes()!=plain: raise OSError('Nieudana weryfikacja kopii JSON.')
            key=secrets.token_bytes(32)
            wrapped=protect_windows(key)
            recovery=key.hex()
            print('KLUCZ ODZYSKIWANIA / DODAWANIA STANOWISK (zapisz w bezpiecznym miejscu, NIE na udziale):')
            print(recovery)
            if input('Potwierdz zapisanie klucza wpisujac ZAPISANE: ').strip()!='ZAPISANE': return
            with database_mutex(target):
                if target.exists(): raise FileExistsError(target)
                atomic_write(keyfile,wrapped)
                atomic_write(target,encrypt(plain,key))
                if decrypt(target.read_bytes(),key)!=plain: raise ValueError('Weryfikacja migracji nie powiodla sie.')
        print('Utworzono:',target,'; JSON pozostawiono bez zmian; kopia:',backup)
        configure(target)
    elif action=='2':
        target=Path(input('Pelna sciezka istniejacej CFDB: ').strip().strip('"'))
        key=bytes.fromhex(getpass.getpass('64 znaki klucza odzyskiwania: ').strip())
        if len(key)!=32: raise ValueError('Nieprawidlowy klucz.')
        with database_mutex(target): decode_database(decrypt(target.read_bytes(),key))
        keyfile=ROOT/'cfdb-key.dpapi'
        if keyfile.exists():
            from cf_crypto import unprotect_windows
            if unprotect_windows(keyfile.read_bytes()) != key: raise ValueError('Istniejacy klucz lokalny jest inny. Nie nadpisuje.')
        else: atomic_write(keyfile,protect_windows(key))
        print('Klucz lokalny skonfigurowany.')
        configure(target)
    else: raise ValueError('Wybierz 1 lub 2.')
    print('Konfiguracja stanowiska zakonczona.')
if __name__=='__main__': main()
