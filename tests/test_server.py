import http.client
import json
from pathlib import Path
import tempfile
import threading
import unittest
from copy import deepcopy
from datetime import date, timedelta
import server


def panel():
    return {'id': 'CSP-01', 'model': 'Polon 6000', 'location': 'Łódź', 'intervalMonths': 3,
            'lastInspection': '2025-01-31 09:00', 'condition': 'Sprawna'}


def protocol(id='P-1', result='Pozytywny'):
    return {'id': id, 'panelId': 'CSP-01', 'date': date.today().isoformat()+' 09:00',
            'protocolStatus': 'final', 'type': 'Przegląd', 'technician': 'Jan Kowalski',
            'result': result, 'desc': 'Wykonano próby.', 'recom': 'Usunąć usterkę.' if result!='Pozytywny' else '',
            'checklist': [{'label': 'Zasilanie', 'result': 'OK' if result=='Pozytywny' else 'Usterka', 'note': '24 V'}]}


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'index.html').write_text('SSP')
        self.server,_=server.make_server(self.root,0)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()

    def request(self,method='GET',data=None,path='/api/database',headers=None):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port)
        connection.request(method,path,None if data is None else json.dumps(data),headers or {'X-SSP-Client':'local'})
        response=connection.getresponse();body=response.read();connection.close()
        return response.status,json.loads(body)

    def save(self,data,rev=None,mode=None):
        return self.request('PUT',{'revision':rev,'database':data,'mode':mode})

    def base(self):
        return {'panels':[panel()],'faults':[],'history':[]}

    def test_migration_and_utf16(self):
        legacy=self.base();legacy['custom']={'keep':True}
        legacy['history']=[{'id':'HIST-1','panelId':'CSP-01','date':'2025-01-01 10:00','protocolNo':'OLD/1','desc':'stare dane'}]
        path=self.root/'db_polon_ssp.json';raw=json.dumps(legacy).encode('utf-16');path.write_bytes(raw)
        status,value=self.request();self.assertEqual(status,200)
        self.assertEqual(value['database']['history'][0]['protocolStatus'],'legacy')
        self.assertEqual(value['database']['custom'],{'keep':True})
        self.assertEqual(path.read_bytes(),raw)  # Read never changes the original.
        status,saved=self.save(value['database'],value['revision']);self.assertEqual(status,200)
        self.assertEqual((self.root/'db_polon_ssp.json.bak').read_bytes(),raw)
        self.assertEqual(saved['database']['custom'],{'keep':True})

    def test_save_backup_and_conflict(self):
        status,first=self.save(self.base());self.assertEqual(status,200)
        data=first['database'];data['panels'][0]['location']='Nowy budynek'
        status,second=self.save(data,first['revision']);self.assertEqual(status,200)
        self.assertEqual(json.loads((self.root/'db_polon_ssp.json.bak').read_text())['panels'][0]['location'],'Łódź')
        self.assertEqual(self.save(data,first['revision'])[0],409)
        self.assertEqual(self.request()[1]['database'],second['database'])
        self.assertEqual(len(self.request(path='/api/backups')[1]),1)

    def test_corruption_is_not_overwritten(self):
        path=self.root/'db_polon_ssp.json';path.write_text('broken')
        self.assertEqual(self.request()[0],500)
        self.assertEqual(self.save(self.base())[0],400)
        self.assertEqual(path.read_text(),'broken')

    def test_private_files_and_cross_origin(self):
        for path in ['/config.json','/db_polon_ssp.json','/server.py','/../config.json']:
            self.assertEqual(self.request(path=path)[0],404)
        self.assertEqual(self.request(headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('PUT',{},headers={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.save({})[0],400)

    def test_positive_protocol_snapshot_numbering_immutable(self):
        data=self.base();data['history']=[protocol()]
        status,first=self.save(data);self.assertEqual(status,200,first)
        final=first['database']['history'][0]
        self.assertEqual(final['protocolNo'],f'SSP/{date.today().year}/0001')
        self.assertEqual(final['panelSnapshot']['location'],'Łódź')
        self.assertEqual(first['database']['panels'][0]['lastInspection'],protocol()['date'])
        change=deepcopy(first['database']);change['history'][0]['desc']='Edited'
        self.assertEqual(self.save(change,first['revision'])[0],400)
        change=deepcopy(first['database']);change['history']=[]
        self.assertEqual(self.save(change,first['revision'])[0],400)
        change=deepcopy(first['database']);change['panels'][0]['location']='Budynek 2';change['history'].append(protocol('P-2'))
        status,second=self.save(change,first['revision']);self.assertEqual(status,200,second)
        self.assertEqual(second['database']['history'][1]['protocolNo'],f'SSP/{date.today().year}/0002')
        self.assertEqual(second['database']['history'][0]['panelSnapshot']['location'],'Łódź')

    def test_negative_inspection_does_not_postpone_deadline(self):
        data=self.base();data['history']=[protocol(result='Negatywny')]
        status,saved=self.save(data);self.assertEqual(status,200,saved)
        self.assertEqual(saved['database']['panels'][0]['lastInspection'],panel()['lastInspection'])
        self.assertEqual(saved['database']['panels'][0]['condition'],'Wymaga serwisu')

    def test_incomplete_or_contradictory_inspection_rejected(self):
        for checks in [[],[{'label':'Zasilanie','result':'','note':''}],
                       [{'label':'Zasilanie','result':'Nie dotyczy','note':''}],
                       [{'label':'Zasilanie','result':'Usterka','note':''}]]:
            data=self.base();h=protocol();h['checklist']=checks;data['history']=[h]
            self.assertEqual(self.save(data)[0],400)
        data=self.base();h=protocol();h['date']=(date.today()+timedelta(days=1)).isoformat();data['history']=[h]
        self.assertEqual(self.save(data)[0],400)

    def test_fault_requires_final_positive_protocol_to_close(self):
        data=self.base();data['faults']=[{'id':'A-1','panelId':'CSP-01','status':'Zamknięte'}]
        self.assertEqual(self.save(data)[0],400)
        h=protocol();h.update(faultId='A-1',closeFault=True);data['history']=[h]
        status,saved=self.save(data);self.assertEqual(status,200,saved)
        self.assertEqual(saved['database']['faults'][0]['status'],'Zamknięte')
        self.assertIn('closedAt',saved['database']['faults'][0])

    def test_draft_does_not_change_inspection_date(self):
        data=self.base();h=protocol();h.update(protocolStatus='draft',technician='',result='');data['history']=[h]
        status,saved=self.save(data);self.assertEqual(status,200)
        self.assertEqual(saved['database']['panels'][0]['lastInspection'],panel()['lastInspection'])
        self.assertEqual(saved['database']['history'][0]['protocolNo'],'')

    def test_config_roundtrip_and_conflict(self):
        status,old=self.request(path='/api/config');self.assertEqual(status,200)
        service=old['service'];service['company']='Serwis Łódź';service['protocolPrefix']='ZSP'
        status,new=self.request('PUT',{'revision':old['revision'],'service':service},'/api/config');self.assertEqual(status,200)
        self.assertEqual(self.request('PUT',{'revision':old['revision'],'service':service},'/api/config')[0],409)
        self.assertEqual(self.request(path='/api/config')[1]['service']['company'],'Serwis Łódź')
        self.assertEqual(json.loads((self.root/'config.json').read_text())['database'],'db_polon_ssp.json')
        data=self.base();data['history']=[protocol()]
        status,saved=self.save(data);self.assertEqual(status,200)
        self.assertTrue(saved['database']['history'][0]['protocolNo'].startswith('ZSP/'))
        self.assertEqual(saved['database']['history'][0]['serviceSnapshot']['company'],'Serwis Łódź')

    def test_import_and_backup_rotation(self):
        status,saved=self.save(self.base());self.assertEqual(status,200)
        for _ in range(32):
            self.assertEqual(self.request('POST',path='/api/backup')[0],200)
        self.assertEqual(len(self.request(path='/api/backups')[1]),30)
        empty={'panels':[],'faults':[],'history':[]}
        self.assertEqual(self.save(empty,saved['revision'])[0],400)
        status,imported=self.save(empty,saved['revision'],'replace');self.assertEqual(status,200)
        self.assertEqual(imported['database']['panels'],[])
        self.assertEqual(imported['database']['audit'][-1]['action'],'Import / przywrócenie bazy')

    def test_archive_with_open_fault_blocked_and_draft_deletion_audited(self):
        data=self.base();data['faults']=[{'id':'A-1','panelId':'CSP-01','status':'Nowe'}]
        h=protocol();h['protocolStatus']='draft';data['history']=[h]
        status,saved=self.save(data);self.assertEqual(status,200)
        data=deepcopy(saved['database']);data['panels'][0]['archived']=True
        self.assertEqual(self.save(data,saved['revision'])[0],400)
        data=deepcopy(saved['database']);data['history']=[]
        status,deleted=self.save(data,saved['revision']);self.assertEqual(status,200)
        self.assertTrue(any('usunięto' in line for line in deleted['database']['audit'][-1]['details']))

    def test_malformed_audit_rejected(self):
        data=self.base();data['audit']=[{'action': 'x', 'details': 'not a list'}]
        self.assertEqual(self.save(data)[0],400)

    def test_unknown_schema_and_invalid_date_rejected(self):
        data=self.base();data['schemaVersion']=99
        self.assertEqual(self.save(data)[0],400)
        data=self.base();data['panels'][0]['lastInspection']='not a date'
        self.assertEqual(self.save(data)[0],400)


if __name__=='__main__':
    unittest.main()
