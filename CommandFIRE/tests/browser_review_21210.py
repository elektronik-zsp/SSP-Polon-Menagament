"""Optional browser regression: requires Playwright and /usr/bin/chromium on the test host."""
from pathlib import Path
import sys, tempfile, shutil, threading, copy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from auth_users import new_user
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(tempfile.mkdtemp(prefix='commandfire-screenshots-'))
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp)
 for f in ['index.html','style.css','app.js','favicon.ico','favicon.png','licencja.html']:shutil.copy(ROOT/f,root/f)
 shutil.copytree(ROOT/'assets',root/'assets')
 data=copy.deepcopy(server.EMPTY_DB)
 data['users']=[new_user('admin','Serwisant testowy','TestPassword123!','ADMIN',None,False)]
 data['panels']=[{'id':'C01','model':'Polon 6000','location':'Budynek testowy','spot':'Portiernia'}]
 (root/'db_polon_ssp.json').write_bytes(server.encode(server.validate_database(data)))
 http,_=server.make_server(root,0);thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
   page=browser.new_page(viewport={'width':1366,'height':900});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
   page.goto('http://127.0.0.1:'+str(http.server_port))
   page.locator('#auth-username').fill('admin');page.locator('#auth-password').fill('TestPassword123!');page.locator('#auth-form button').click()
   page.locator('[data-action="new-fault"]').first.click()
   page.locator('#f-reporter').fill('Dyżurny');page.locator('#f-desc').fill('Uszkodzona czujka — brak odpowiedzi')
   page.screenshot(path=str(OUT/'01-zgloszenie.png'))
   page.locator('#editor-actions button[type=submit]').click();page.locator('#editor').wait_for(state='hidden')
   page.locator('[data-action="log-fault"]').first.click()
   page.locator('#f-author').fill('Jan Kowalski');page.locator('#f-status').select_option('W realizacji');page.locator('#f-workStage').select_option('Oczekiwanie na części');page.locator('#f-text').fill('Potrzebna nowa czujka. Brak części na stanie.')
   page.locator('#editor-actions button[type=submit]').click();page.locator('#editor').wait_for(state='hidden')
   page.locator('[data-action="log-fault"]').first.click()
   page.locator('#f-author').fill('Anna Nowak');page.locator('#f-status').select_option('Zakończone');page.locator('#f-text').fill('Wymieniono czujkę i wykonano test.')
   assert page.locator('#f-cause').get_attribute('required') is not None
   page.locator('#editor-actions button[type=submit]').click()
   assert page.locator('#editor').is_visible(), 'Closure without completion fields should be blocked'
   for name,value in [('cause','Uszkodzona czujka'),('resolution','Wymiana na nową czujkę'),('verification','Test funkcjonalny zakończony poprawnie')]:page.locator('#f-'+name).fill(value)
   page.screenshot(path=str(OUT/'02-wpis-serwisowy.png'))
   page.set_viewport_size({'width':390,'height':844})
   assert page.locator('#editor').evaluate('(e)=>e.scrollWidth<=e.clientWidth'), 'Dialog overflows horizontally'
   assert page.locator('#editor-fields').evaluate('(e)=>e.scrollWidth<=e.clientWidth'), 'Fields overflow horizontally'
   page.screenshot(path=str(OUT/'03-formularz-telefon.png'))
   page.locator('#editor-actions button[type=submit]').click();page.locator('#editor').wait_for(state='hidden')
   saved=server.decode_database((root/'db_polon_ssp.json').read_bytes());fault=saved['faults'][0]
   assert fault['status']=='Zakończone'
   actions=[a for a in fault['timeline'] if a['type']=='action']
   assert len(actions)==2 and actions[0]['performedBy']=='Jan Kowalski' and actions[1]['performedBy']=='Anna Nowak',actions
   assert not errors, errors
   browser.close();print('PASS browser: create, waiting for parts, closure validation, two technicians, persisted timeline, mobile layout, no JS errors')
 finally:http.shutdown();http.server_close();thread.join()
