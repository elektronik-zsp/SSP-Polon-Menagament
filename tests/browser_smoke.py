import sys, tempfile, shutil, threading, json
from pathlib import Path
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
import server
from playwright.sync_api import sync_playwright
with tempfile.TemporaryDirectory() as directory:
 root=Path(directory)
 shutil.copy(PROJECT / 'index.html', root / 'index.html')
 http,_=server.make_server(root,0)
 threading.Thread(target=http.serve_forever,daemon=True).start()
 url=f'http://127.0.0.1:{http.server_port}'
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('chromium-browser'),args=['--no-sandbox'])
  page=browser.new_page()
  errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('dialog',lambda d:d.accept())
  page.goto(url)
  assert page.locator('#kpi-total-panels').inner_text()=='26'
  page.evaluate("openPanelEditModal('CSP-01')")
  page.locator('#edit-panel-loc').fill('Test Łódź — zapis na dysku')
  page.evaluate('savePanelEdit()')
  data=json.loads((root/'db_polon_ssp.json').read_text())
  assert data['panels'][0]['location']=='Test Łódź — zapis na dysku'
  page.reload()
  assert page.evaluate('db.panels[0].location')=='Test Łódź — zapis na dysku'
  assert not errors, errors
  print('PASS browser: initial demo, panel edit, file persistence, reload; no JS errors')
  browser.close()
 http.shutdown(); http.server_close()
 # Restart against the same database and test empty database separately.
 http,_=server.make_server(root,0)
 threading.Thread(target=http.serve_forever,daemon=True).start()
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('chromium-browser'),args=['--no-sandbox'])
  page=browser.new_page(); errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(f'http://127.0.0.1:{http.server_port}')
  assert page.evaluate('db.panels[0].location')=='Test Łódź — zapis na dysku'
  (root/'db_polon_ssp.json').unlink()
  page.on('dialog',lambda d:d.dismiss())
  page.reload()
  assert page.evaluate('db.panels.length')==0
  assert page.locator('#kpi-total-panels').inner_text()=='0'
  assert not errors,errors
  print('PASS browser: server restart; empty database stays empty')
  browser.close()
 http.shutdown();http.server_close()
