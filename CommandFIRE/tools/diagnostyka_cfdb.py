# CommandFIRE diagnostic only. Does not write to database or disclose keys.
import json, os, sys, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cf_crypto import decrypt, unprotect_windows
from server import decode_database, database_summary

def main():
    print('CommandFIRE CFDB - diagnostyka stanowiska (tylko odczyt)')
    cfg=ROOT/'config.json'; kp=ROOT/'cfdb-key.dpapi'
    if not cfg.is_file(): raise ValueError('Brak config.json. Uruchom konfigurator.')
    settings=json.loads(cfg.read_text(encoding='utf-8-sig'))
    db=Path(settings.get('database',''))
    if not db.is_absolute(): db=(ROOT/db).resolve()
    print('Baza:',db)
    print('Format:',db.suffix.lower())
    if not db.is_file(): raise FileNotFoundError('Baza niedostepna. Sprawdz sciezke UNC i uprawnienia SMB.')
    print('Rozmiar:',db.stat().st_size,'B')
    if db.suffix.lower()!='.cfdb': raise ValueError('Aktywna baza nie jest CFDB.')
    if not kp.is_file(): raise FileNotFoundError('Brak lokalnego cfdb-key.dpapi.')
    key=unprotect_windows(kp.read_bytes())
    if len(key)!=32: raise ValueError('Nieprawidlowa dlugosc klucza DPAPI.')
    raw=db.read_bytes()
    data=decode_database(decrypt(raw,key))
    print('Klucz DPAPI: poprawny dla tej bazy')
    print('Integralnosc bazy: OK')
    print('Podsumowanie:',json.dumps(database_summary(data),ensure_ascii=False))
    print('SHA256 pliku:',hashlib.sha256(raw).hexdigest())
    bdir=db.parent/'backups'
    files=sorted(bdir.glob(db.stem+'-*'+db.suffix),reverse=True)[:5] if bdir.is_dir() else []
    print('Ostatnie kopie:',len(files),'(maks. 5 wyswietlonych)')
    for p in files:
        try:
            decode_database(decrypt(p.read_bytes(),key))
            print('  OK:',p.name)
        except Exception as exc:
            print('  BLAD:',p.name,type(exc).__name__)
    print('WYNIK: OK. Diagnostyka nie zapisala zadnych danych.')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print('WYNIK: BLAD:',str(exc))
        sys.exit(1)
