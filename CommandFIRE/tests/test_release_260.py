import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import unittest, tempfile, threading, json, urllib.request, urllib.error
from copy import deepcopy
import server as app
from auth_users import new_user

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.db=app.validate_database({'schemaVersion':4,'panels':[{'id':'C01'}],
            'faults':[{'id':'F01','panelId':'C01','date':'2026-10-20 10:00','desc':'Usterka','reporter':'Jan'}], 'history':[]})
        self.db=app.apply_workflow(self.db,None,app.DEFAULT_SERVICE)
    def test_migration_preserves_numbers_and_history(self):
        original=deepcopy(self.db);result=app.decode_database(app.encode(original))
        self.assertEqual(result['faults'][0]['number'],'ZG/2026/0001')
        self.assertEqual(result['faults'][0]['timeline'],self.db['faults'][0]['timeline'])
        self.assertEqual(result['schemaVersion'],8)
    def test_details_closure_reopen_and_append_only(self):
        changed=deepcopy(self.db);f=changed['faults'][0];f['assignee']='Serwis'
        changed=app.apply_workflow(changed,self.db,app.DEFAULT_SERVICE)
        self.assertIn('Odpowiedzialny: — → Serwis',changed['faults'][0]['timeline'][-1]['text'])
        closed=deepcopy(changed);f=closed['faults'][0];f['status']='Zakończone'
        f['timeline'].append({'id':'LOG-2','at':'','type':'action','author':'Technik','text':'Naprawiono'})
        with self.assertRaisesRegex(ValueError,'Zakończenie'):app.apply_workflow(deepcopy(closed),changed,app.DEFAULT_SERVICE)
        f.update(cause='Uszkodzona czujka',resolution='Wymiana',verification='Próba poprawna')
        closed=app.apply_workflow(closed,changed,app.DEFAULT_SERVICE)
        self.assertTrue(closed['faults'][0]['closedAt'])
        reopened=deepcopy(closed);f=reopened['faults'][0];f['status']='W realizacji'
        f['timeline'].append({'id':'LOG-3','at':'','type':'action','author':'Technik','text':'Nawrót'})
        reopened=app.apply_workflow(reopened,closed,app.DEFAULT_SERVICE)
        self.assertNotIn('closedAt',reopened['faults'][0])
        tampered=deepcopy(reopened);tampered['faults'][0]['timeline'][0]['text']='nadpisano'
        with self.assertRaisesRegex(ValueError,'niezmienna'):app.apply_workflow(tampered,reopened,app.DEFAULT_SERVICE)
    def test_relation_validation(self):
        broken=deepcopy(self.db);broken['faults'][0].update(relatedFaultId='F01',relationType='Nawrót')
        with self.assertRaises(ValueError):app.validate_database(broken)
    def test_document_validation_and_backup(self):
        db=deepcopy(self.db);db['panels'][0]['documents']=[{'id':'D01','name':'instrukcja.txt','data':'VGVzdA=='}]
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'copy.json';p.write_bytes(app.encode(db));info=app.inspect_backup(p)
            self.assertTrue(info['valid']);self.assertEqual(info['summary']['documents'],1)
            p.write_text('{broken');self.assertFalse(app.inspect_backup(p)['valid'])
        db['panels'][0]['documents'][0]['name']='../test.txt'
        with self.assertRaises(ValueError):app.validate_database(db)
    def test_protocol_closes_fault_without_manual_action(self):
        db=deepcopy(self.db);db['history'].append({'id':'H01','panelId':'C01','date':'2026-10-19 10:00',
            'type':'Naprawa','technician':'Technik','desc':'Naprawiono czujkę','result':'Pozytywny',
            'protocolStatus':'final','faultId':'F01','closeFault':True})
        db=app.validate_database(db);result=app.apply_workflow(db,self.db,app.DEFAULT_SERVICE)
        f=result['faults'][0];self.assertEqual(f['status'],'Zakończone');self.assertTrue(f['verification'])

class ApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.path=root/'db_polon_ssp.json'
        user=new_user('admin','Administrator','TestPassword123!','ADMIN',None,False)
        data=deepcopy(app.EMPTY_DB);data['users']=[user];self.path.write_bytes(app.encode(data))
        self.http,_=app.make_server(root,0);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.http.server_port);self.token=''
        self.token=self.call('/api/auth/login',{'username':'admin','password':'TestPassword123!'})['token']
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def call(self,path,data=None,method=None):
        request=urllib.request.Request(self.url+path,data=app.encode(data) if data is not None else None,method=method,
            headers={'X-SSP-Client':'local','X-SSP-Session':self.token,'Content-Type':'application/json'})
        with urllib.request.urlopen(request) as response:return json.load(response)
    def test_schedule_api_roundtrip(self):
        current=self.call('/api/database')
        candidate=deepcopy(current['database']);candidate['panels'].append({'id':'C01'})
        saved=self.call('/api/database',{'revision':current['revision'],'base':current['database'],'database':candidate,'token':'a'*32},'PUT')
        self.call('/api/lock',{'action':'claim','resource':'panels/C01','token':'a'*32})
        candidate=deepcopy(saved['database']);candidate['panels'][0].update(inspectionPlanDate='2026-11-10',inspectionPlanAssignee='Technik')
        saved=self.call('/api/database',{'revision':saved['revision'],'base':saved['database'],'database':candidate,'token':'a'*32},'PUT')
        self.assertTrue(saved['database']['panels'][0]['inspectionPlanId'])
        self.assertEqual(saved['database']['panels'][0]['inspectionPlanDate'],'2026-11-10')
        self.assertTrue(self.call('/api/backups')[0]['valid'])
    def test_technician_can_lock_inspection_but_not_edit_panel(self):
        data=app.decode_database(self.path.read_bytes());data['users'].append(new_user('technik','Technik','TestPassword123!','SERWISANT',None,False));data['panels']=[{'id':'C01'}]
        data=app.validate_database(data);self.path.write_bytes(app.encode(data))
        self.token=self.call('/api/auth/login',{'username':'technik','password':'TestPassword123!'})['token']
        self.call('/api/lock',{'action':'claim','resource':'panels/C01','token':'b'*32})
        current=self.call('/api/database');candidate=deepcopy(current['database']);candidate['panels'][0]['location']='Nieuprawniona zmiana'
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.call('/api/database',{'revision':current['revision'],'base':current['database'],'database':candidate,'token':'b'*32},'PUT')
        self.assertEqual(caught.exception.code,403)
    def test_cost_api_visibility_and_write_permissions(self):
        data=app.decode_database(self.path.read_bytes())
        data['panels']=[{'id':'C01'}]
        data['history']=[{'id':'H01','panelId':'C01','protocolStatus':'legacy','date':'2026-01-01'}]
        data['users'].append(new_user('odczyt','Odczyt','TestPassword123!','ODCZYT',None,False))
        data['users'].append(new_user('limited','Ograniczony','TestPassword123!','ODCZYT',['dashboard.view'],False))
        self.path.write_bytes(app.encode(app.validate_database(data)))
        current=self.call('/api/database');candidate=deepcopy(current['database'])
        candidate['costs'].append({'id':'K1','protocolId':'H01','date':'2026-01-01','category':'Części','amountGrosz':12345,'description':'Czujka'})
        saved=self.call('/api/database',{'revision':current['revision'],'base':current['database'],'database':candidate,'token':'a'*32},'PUT')
        self.assertEqual(saved['database']['costs'][0]['amountGrosz'],12345)
        self.assertEqual(saved['database']['costs'][0]['createdBy'],'Administrator')
        self.token=self.call('/api/auth/login',{'username':'odczyt','password':'TestPassword123!'})['token']
        current=self.call('/api/database');self.assertEqual(len(current['database']['costs']),1)
        candidate=deepcopy(current['database']);candidate['costs'].append(dict(candidate['costs'][0],id='K2'))
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.call('/api/database',{'revision':current['revision'],'base':current['database'],'database':candidate,'token':'a'*32},'PUT')
        self.assertEqual(caught.exception.code,403)
        self.token=self.call('/api/auth/login',{'username':'limited','password':'TestPassword123!'})['token']
        self.assertEqual(self.call('/api/database')['database']['costs'],[])
    def test_linked_fault_can_be_edited_without_dictionary_permission(self):
        data=app.decode_database(self.path.read_bytes())
        data['panels']=[{'id':'C01','elements':[{'id':'E1','address':'P1/42','type':'Czujka','location':'Hala'}]}]
        data['faults']=[{'id':'F1','panelId':'C01','elementId':'E1','elementAddress':'P1/42','elementType':'Czujka','elementLocation':'Hala','date':'2026-01-01','desc':'Usterka'}]
        data['users'].append(new_user('faults','Dyspozytor','TestPassword123!','DYSPOZYTOR',['faults.view','faults.edit'],False))
        self.path.write_bytes(app.encode(app.validate_database(data)))
        self.token=self.call('/api/auth/login',{'username':'faults','password':'TestPassword123!'})['token']
        current=self.call('/api/database');self.assertEqual(current['database']['panels'],[])
        self.call('/api/lock',{'action':'claim','resource':'faults/F1','token':'c'*32})
        candidate=deepcopy(current['database']);candidate['faults'][0]['assignee']='Serwis'
        saved=self.call('/api/database',{'revision':current['revision'],'base':current['database'],'database':candidate,'token':'c'*32},'PUT')
        self.assertEqual(saved['database']['faults'][0]['elementId'],'E1')
        self.assertEqual(saved['database']['faults'][0]['assignee'],'Serwis')
    def test_preview_backup_and_corruption(self):
        preview=self.call('/api/import-preview',{'database':deepcopy(app.EMPTY_DB)})
        self.assertTrue(preview['accountsPreserved']);self.assertEqual(preview['summary']['panels'],0)
        result=self.call('/api/backup',{});self.assertTrue(result['name'])
        backups=self.call('/api/backups');self.assertTrue(backups[0]['valid'])
        p=self.path.parent/'backups'/result['name'];p.write_text('broken')
        self.assertFalse(self.call('/api/backups')[0]['valid'])
        with self.assertRaises(urllib.error.HTTPError):self.call('/api/backups/'+result['name'])
        with self.assertRaises(urllib.error.HTTPError):self.call('/api/import-preview',{'database':{'schemaVersion':999}})

if __name__=='__main__':unittest.main()
