import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from copy import deepcopy
import server as app

class ElementTests(unittest.TestCase):
    def setUp(self):
        self.db=app.validate_database({'schemaVersion':7,'panels':[{'id':'C01','elements':[{'id':'E1','address':'Pętla 1 / 42','type':'Czujka','location':'Hala'}]},{'id':'C02'}],
            'faults':[],'history':[]})
    def new_fault(self,old):
        new=deepcopy(old);new['faults'].append({'id':'F1','panelId':'C01','date':'2026-10-20','desc':'Brak odpowiedzi czujki','elementId':'E1','elementAddress':'Fałszywy adres'})
        return app.apply_workflow(app.validate_database(new),old,app.DEFAULT_SERVICE)
    def test_migration_and_authoritative_snapshot(self):
        saved=self.new_fault(self.db);f=saved['faults'][0]
        self.assertEqual(saved['schemaVersion'],8);self.assertEqual(f['elementAddress'],'Pętla 1 / 42')
        self.assertEqual(f['elementType'],'Czujka');self.assertEqual(f['elementLocation'],'Hala')
        self.assertEqual(saved['panels'][1]['elements'],[])
    def test_dictionary_edits_do_not_rewrite_faults(self):
        old=self.new_fault(self.db);new=deepcopy(old);new['panels'][0]['elements'][0].update(address='Pętla 1 / 43',location='Magazyn')
        saved=app.apply_workflow(app.validate_database(new),old,app.DEFAULT_SERVICE)
        self.assertEqual(saved['faults'][0],old['faults'][0])
        self.assertTrue(any('Element:' in line for line in saved['audit'][-1]['details']))
    def test_normalized_duplicate_address_rejected(self):
        new=deepcopy(self.db);new['panels'][0]['elements'].append({'id':'E2','address':' pĘTLA   1 / 42 '})
        with self.assertRaisesRegex(ValueError,'już istnieje'):app.validate_database(new)
    def test_no_delete_but_archive_is_allowed(self):
        new=deepcopy(self.db);new['panels'][0]['elements']=[]
        with self.assertRaisesRegex(ValueError,'archiwizacji'):app.apply_workflow(app.validate_database(new),self.db,app.DEFAULT_SERVICE)
        new=deepcopy(self.db);new['panels'][0]['elements'][0]['archived']=True
        archived=app.apply_workflow(app.validate_database(new),self.db,app.DEFAULT_SERVICE)
        with self.assertRaisesRegex(ValueError,'aktywny'):self.new_fault(archived)
    def test_wrong_panel_and_tampered_snapshot_rejected(self):
        new=deepcopy(self.db);new['faults']=[{'id':'F1','panelId':'C02','elementId':'E1'}]
        with self.assertRaisesRegex(ValueError,'należeć'):app.validate_database(new)
        old=self.new_fault(self.db);new=deepcopy(old);new['faults'][0]['elementAddress']='Podmieniony'
        with self.assertRaisesRegex(ValueError,'historyczne'):app.apply_workflow(app.validate_database(new),old,app.DEFAULT_SERVICE)
    def test_old_link_survives_archiving(self):
        old=self.new_fault(self.db);new=deepcopy(old);new['panels'][0]['elements'][0]['archived']=True
        saved=app.apply_workflow(app.validate_database(new),old,app.DEFAULT_SERVICE)
        new=deepcopy(saved);new['faults'][0]['assignee']='Serwis'
        result=app.apply_workflow(app.validate_database(new),saved,app.DEFAULT_SERVICE)
        self.assertEqual(result['faults'][0]['elementId'],'E1')
    def test_partial_client_and_full_import_validation(self):
        old=self.new_fault(self.db);partial=deepcopy(old);partial['panels']=[]
        app.validate_database(partial,partial=True)
        with self.assertRaises(ValueError):app.validate_database(partial)

if __name__=='__main__':unittest.main()
