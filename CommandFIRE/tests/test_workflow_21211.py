"""Report lifecycle and approval authorization regressions."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest, tempfile, threading, json, urllib.request, urllib.error
from copy import deepcopy
import server as app
from auth_users import new_user, ROLE_DEFAULTS

class ProtocolWorkflowTests(unittest.TestCase):
    def baseline(self,closed=False,archived=False):
        db=app.validate_database({'panels':[{'id':'C1','archived':archived}], 'faults':[{'id':'F1','panelId':'C1','status':'Zakończone' if closed else 'W realizacji','closedAt':'2026-10-20T12:00:00+02:00','cause':'Uszkodzenie','resolution':'Wymieniono czujkę','verification':'Próba OK'}],'history':[]})
        return db
    def protocol(self,db,final=True,close=False):
        new=deepcopy(db)
        new['history'].append({'id':'H1','panelId':'C1','faultId':'F1','date':'2026-10-20 11:00','type':'Naprawa','technician':'Technik','desc':'Dokumentacja naprawy','result':'Pozytywny','closeFault':close,'protocolStatus':'final' if final else 'draft'})
        return app.validate_database(new)
    def test_completed_report_preserves_closure_even_with_stale_close_flag(self):
        for close in (False,True):
            old=self.baseline(closed=True);new=self.protocol(old,close=close)
            saved=app.apply_workflow(new,old,app.DEFAULT_SERVICE,actor={'id':'U1','displayName':'Kierownik'})
            for field in ('closedAt','cause','resolution','verification','status'):
                self.assertEqual(saved['faults'][0][field],old['faults'][0][field])
            self.assertEqual(saved['history'][0]['finalizedBy'],'Kierownik')
            self.assertEqual(saved['faults'][0]['timeline'][-1]['type'],'protocol')
    def test_draft_has_no_closing_side_effect_and_final_can_close(self):
        old=self.baseline();draft=app.apply_workflow(self.protocol(old,False,True),old,app.DEFAULT_SERVICE)
        self.assertEqual(draft['faults'][0]['status'],'W realizacji')
        self.assertFalse(draft['history'][0]['protocolNo'])
        final=deepcopy(draft);final['history'][0]['protocolStatus']='final'
        final=app.apply_workflow(final,draft,app.DEFAULT_SERVICE)
        self.assertEqual(final['faults'][0]['status'],'Zakończone')
        self.assertTrue(final['history'][0]['protocolNo'])
    def test_archived_completed_fault_can_be_documented(self):
        old=self.baseline(True,True)
        saved=app.apply_workflow(self.protocol(old),old,app.DEFAULT_SERVICE)
        self.assertTrue(saved['history'][0]['protocolNo'])
        self.assertEqual(saved['panels'],old['panels'])
    def test_draft_rejects_wrong_panel(self):
        old=self.baseline();new=self.protocol(old,False);new['panels'].append({'id':'C2'});new['history'][0]['panelId']='C2'
        with self.assertRaisesRegex(ValueError,'tej samej centrali'):
            app.apply_workflow(app.validate_database(new),old,app.DEFAULT_SERVICE)
    def test_cancelled_and_negative_cannot_close(self):
        for cancelled in (True,False):
            old=self.baseline();old['faults'][0]['status']='Anulowane' if cancelled else 'W realizacji'
            new=self.protocol(old,close=True)
            if not cancelled:new['history'][0].update(result='Negatywny',recom='Dalsza naprawa')
            with self.assertRaises(ValueError):app.apply_workflow(new,old,app.DEFAULT_SERVICE)

class ApprovalApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name);self.path=root/'db_polon_ssp.json'
        data=ProtocolWorkflowTests().baseline(True)
        data=ProtocolWorkflowTests().protocol(data,False)
        data['users']=[new_user('technik','Technik','TestPassword123!','SERWISANT',None,False),new_user('reviewer','Kierownik','TestPassword123!','ODCZYT',['protocols.view','protocols.finalize','panels.view','faults.view'],False)]
        self.path.write_bytes(app.encode(data));self.http,_=app.make_server(root,0)
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.http.server_port);self.token=''
    def tearDown(self):self.http.shutdown();self.http.server_close();self.thread.join();self.tmp.cleanup()
    def call(self,path,data=None,method=None):
        req=urllib.request.Request(self.url+path,data=app.encode(data) if data is not None else None,method=method,headers={'X-SSP-Client':'local','X-SSP-Session':self.token,'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as r:return json.load(r)
    def attempt(self,login,tamper=False):
        self.token=self.call('/api/auth/login',{'username':login,'password':'TestPassword123!'})['token']
        self.call('/api/lock',{'action':'claim','resource':'history/H1','token':'a'*32})
        current=self.call('/api/database');candidate=deepcopy(current['database']);candidate['history'][0]['protocolStatus']='final'
        if tamper:candidate['history'][0]['desc']='Changed by approver'
        return self.call('/api/database',{'base':current['database'],'revision':current['revision'],'database':candidate,'token':'a'*32},'PUT')
    def test_technician_cannot_approve_even_direct_api(self):
        self.assertNotIn('protocols.finalize',ROLE_DEFAULTS['SERWISANT'])
        with self.assertRaises(urllib.error.HTTPError) as caught:self.attempt('technik')
        self.assertEqual(caught.exception.code,403)
        self.assertEqual(app.decode_database(self.path.read_bytes())['history'][0]['protocolStatus'],'draft')
    def test_reviewer_can_approve_without_edit_permission(self):
        self.assertEqual(self.attempt('reviewer')['database']['history'][0]['finalizedBy'],'Kierownik')
    def test_reviewer_cannot_change_document_during_approval(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:self.attempt('reviewer',True)
        self.assertEqual(caught.exception.code,403)

if __name__=='__main__':unittest.main()
