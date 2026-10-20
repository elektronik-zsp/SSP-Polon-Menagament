"""End-to-end user workflows in an isolated temporary copy; requires Playwright."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import threading

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
import server
from playwright.sync_api import sync_playwright, expect


def run():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        for name in ['index.html','app.js','style.css']:
            shutil.copy(PROJECT/name,root/name)
        http,_=server.make_server(root,0)
        thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{http.server_port}'
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('chromium-browser'),args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1440,'height':1000})
                errors=[];external=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:external.append(r.url) if not r.url.startswith(url) else None)
                page.on('dialog',lambda d:d.accept())
                page.goto(url)
                expect(page.get_by_role('heading',name='Pulpit serwisowy')).to_be_visible()
                def click(action,id=None):
                    selector=f'[data-action="{action}"]'+(f'[data-id="{id}"]' if id is not None else '')
                    page.locator(selector).first.click()
                def fill(name,value):page.locator(f'#editor [name="{name}"]').fill(str(value))
                def choose(name,value):page.locator(f'#editor [name="{name}"]').select_option(value)
                def save():
                    page.locator('#editor button[type=submit]').first.click()
                    expect(page.locator('#editor')).not_to_be_visible()
                def current():return json.loads((root/'db_polon_ssp.json').read_text())
                click('navigate','settings');click('edit-settings')
                fill('company','Serwis Testowy Łódź');fill('site','Zakład A');fill('protocolPrefix','ZSP');fill('technicians','Jan Testowy\nAnna Serwis')
                save()
                click('navigate','panels');click('new-panel')
                fill('id','CSP-01');fill('location','Hala <img src=x onerror=alert(1)>');fill('spot','Dyspozytornia');fill('serialNo','SN-123');fill('lastInspection','2025-01-31T09:00')
                save()
                expect(page.get_by_role('cell').filter(has_text='Hala <img src=x onerror=alert(1)>')).to_be_visible()
                assert page.locator('img').count()==0
                assert page.evaluate("nextDate({lastInspection:'2024-01-31 09:00',intervalMonths:1})")=='2024-02-29'
                assert page.evaluate("nextDate({lastInspection:'2025-01-31 09:00',intervalMonths:1})")=='2025-02-28'
                click('navigate','faults');click('new-fault')
                fill('reporter','Dyżurny');fill('desc','Usterka zasilania rezerwowego');choose('priority','Wysoki');fill('assignee','Jan Testowy');fill('dueDate','2025-01-01');save()
                fault_id=current()['faults'][0]['id']
                click('service-fault',fault_id)
                fill('technician','Jan Testowy');fill('desc','Wymieniono akumulator i wykonano próbę.');choose('result','Pozytywny');fill('parts','Akumulator 12V 18Ah — 2 szt.');fill('hours','1.5');fill('recipient','Kierownik obiektu')
                page.locator('#editor [name="closeFault"]').check()
                page.locator('#editor button[value=final]').click();expect(page.locator('#editor')).not_to_be_visible()
                data=current();assert data['faults'][0]['status']=='Zamknięte';assert data['history'][0]['protocolNo'].startswith('ZSP/')
                first=data['history'][0]['id']
                # Failed inspection: don't postpone due date.
                click('navigate','panels');click('new-inspection','CSP-01')
                fill('technician','Anna Serwis');fill('desc','Nieprawidłowości podczas kontroli');fill('recom','Wymienić uszkodzony element');choose('result','Negatywny')
                for i in range(6):choose('check-'+str(i),'Usterka' if i==0 else 'OK')
                page.locator('#editor button[value=final]').click();expect(page.locator('#editor')).not_to_be_visible()
                assert current()['panels'][0]['lastInspection']=='2025-01-31 09:00'
                assert current()['panels'][0]['condition']=='Wymaga serwisu'
                # Incomplete inspection stays editable after server validation fails.
                click('new-inspection','CSP-01');fill('technician','Anna Serwis');fill('desc','Kontrola po naprawie');choose('result','Pozytywny')
                page.locator('#editor button[value=final]').click()
                expect(page.locator('#form-error')).to_contain_text('listy kontrolnej')
                expect(page.locator('#editor [name=desc]')).to_have_value('Kontrola po naprawie')
                page.locator('#editor button[value=draft]').click();expect(page.locator('#editor')).not_to_be_visible()
                draft=current()['history'][-1]['id'];assert current()['history'][-1]['protocolNo']==''
                page.reload();click('navigate','protocols');click('edit-protocol',draft)
                for i in range(6):choose('check-'+str(i),'OK')
                page.locator('#editor button[value=final]').click();expect(page.locator('#editor')).not_to_be_visible()
                assert current()['panels'][0]['lastInspection'].startswith(page.evaluate('today()'))
                # Printed document uses immutable snapshots, even after config/panel edits.
                click('navigate','settings');click('edit-settings');fill('company','Nowa firma');save()
                click('navigate','panels');click('edit-panel','CSP-01');fill('location','Nowa lokalizacja');save()
                click('navigate','protocols');click('view-protocol',first)
                expect(page.locator('.protocol-preview')).to_contain_text('Serwis Testowy Łódź')
                expect(page.locator('.protocol-preview')).not_to_contain_text('Nowa firma')
                page.evaluate('window.print=()=>{}');click('print-protocol',first)
                expect(page.locator('#print-area')).to_contain_text('Akumulator 12V 18Ah')
                page.emulate_media(media='print')
                expect(page.locator('#print-area')).to_be_visible()
                page.pdf(path='/tmp/ssp-protocol-v2-test.pdf',format='A4',print_background=True)
                page.emulate_media(media='screen')
                # Stale second window cannot overwrite changes.
                stale=browser.new_page();stale.on('dialog',lambda d:d.accept());stale.goto(url)
                stale.locator('[data-action=navigate][data-id=panels]').click()
                stale.locator('[data-action=edit-panel]').first.click();stale.locator('[name=location]').fill('Stale change')
                click('navigate','panels');click('edit-panel','CSP-01');fill('spot','Nowe miejsce');save()
                stale.locator('#editor button[type=submit]').click();expect(stale.locator('#form-error')).to_contain_text('Baza zmieniła się')
                assert current()['panels'][0]['location']=='Nowa lokalizacja'
                stale.close()
                # Export and import old format, keeping a backup of current data.
                with page.expect_download() as info:click('export')
                exported=json.loads(Path(info.value.path()).read_text());assert len(exported['history'])==3
                click('navigate','backups');click('backup')
                expect(page.locator('#backup-list tbody tr').first).to_be_visible()
                legacy={'panels':[{'id':'OLD-1','location':'Stary obiekt','model':'Polon 4000'}], 'faults':[], 'history':[]}
                page.locator('#import-file').set_input_files({'name':'legacy.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()})
                expect(page.locator('#notification')).to_contain_text('Baza zaimportowana')
                assert current()['panels'][0]['id']=='OLD-1'
                click('navigate','panels');click('panel-card','OLD-1');click('archive-panel','OLD-1')
                expect(page.locator('#notification')).to_contain_text('Zmieniono status')
                assert current()['panels'][0]['archived'] is True
                click('archive-panel','OLD-1');expect(page.locator('[data-action=archive-panel]')).to_contain_text('Archiwizuj')
                # Verify a fresh server process state reads the same on-disk database/config.
                saved_port=http.server_port
                http.shutdown();http.server_close();thread.join()
                http,_=server.make_server(root,saved_port)
                thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
                page.reload();expect(page.get_by_role('heading',name='Pulpit serwisowy')).to_be_visible()
                assert page.evaluate('db.panels[0].id')=='OLD-1'
                assert page.evaluate('service.company')=='Nowa firma'
                page.screenshot(path='/tmp/ssp-dashboard-v2.png',full_page=True)
                assert not errors,errors
                assert not external,external
                browser.close()
                print('PASS: settings, panel CRUD/archive, fault closure, draft/final protocols, negative/positive inspection, immutable print snapshots, PDF, concurrency conflict, export/import, backup, migration, server restart, reload, XSS escaping, leap-month dates, zero external requests.')
        finally:
            http.shutdown();http.server_close();thread.join()


if __name__=='__main__':run()
