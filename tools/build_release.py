"""Build full and update archives. Never include user data or configuration."""
import hashlib
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'downloads'
FILES=['index.html','app.js','style.css','server.py','Uruchom.bat','README.md',
       'docs/PLAN-ROZWOJU.md','docs/ZMIANY-2.0.md',
       'tests/test_server.py','tests/browser_smoke.py','tools/build_release.py']


def build(name,include_runtime):
    paths=[ROOT/name for name in FILES]
    if include_runtime:
        for required in ['python.exe','python313.dll','Lib/http/server.py','LICENSE.txt']:
            if not (ROOT/'runtime'/required).is_file():
                raise SystemExit('Brak zweryfikowanego runtime: '+required)
        paths.extend(p for p in (ROOT/'runtime').rglob('*') if p.is_file()
                     and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.tmp'))
    archive=OUT/name
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for path in sorted(paths):
            z.write(path,'SSP-Polon/'+path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(n.endswith('/config.json') or n.endswith('/db_polon_ssp.json') or '/backups/' in n for n in z.namelist())
    print(name,archive.stat().st_size,'bytes; ZIP verified')
    return hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+name


if __name__=='__main__':
    OUT.mkdir(exist_ok=True)
    lines=[build('SSP-Polon-Portable-Windows-x64.zip',True),build('SSP-Polon-Aktualizacja-2.0.zip',False)]
    (OUT/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
