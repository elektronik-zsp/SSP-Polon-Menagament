"""Build a clean portable archive. Run outside the application directory."""
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'runtime','downloads','backups','update-backups','__pycache__','.git'}
def selected():
    for p in ROOT.rglob('*'):
        rel=p.relative_to(ROOT)
        if not p.is_file() or any(v in EXCLUDED for v in rel.parts):continue
        if p.suffix in ('.pyc','.tmp','.bak','.mutex','.log') or p.name in ('config.json','db_polon_ssp.json'):continue
        if p.suffix.lower() not in ('.py','.js','.cjs','.html','.css','.md','.txt','.bat','.vbs','.svg','.ico','.png','.ps1'):continue
        yield p
if __name__=='__main__':
    output=ROOT.parent/'CommandFIRE-2.12.10-TEST-Portable-Windows-x64.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(selected()):z.write(p,'SSP-Polon/'+p.relative_to(ROOT).as_posix())
        for p in sorted((ROOT/'runtime').rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:z.write(p,'SSP-Polon/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(output) as z:assert z.testzip() is None
    print(output)
