import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from copy import deepcopy
from datetime import date,timedelta
import server as app

class CostTests(unittest.TestCase):
    def setUp(self):
        self.db=app.validate_database({'schemaVersion':6,'panels':[{'id':'C01'}],'faults':[],
            'history':[{'id':'H01','panelId':'C01','date':'2026-01-01','protocolStatus':'final','protocolNo':'SSP/2026/0001'}]})
    def cost(self,key='K1',amount=12345,**kwargs):
        return dict(id=key,protocolId='H01',date='2026-01-01',category='Części',amountGrosz=amount,
                    description='Czujka',reference='FV 1',**kwargs)
    def post(self,old,cost):
        new=deepcopy(old);new['costs'].append(cost)
        return app.apply_workflow(app.validate_database(new),old,app.DEFAULT_SERVICE,actor={'id':'U1','displayName':'Technik'})
    def test_migration_and_document_immutability(self):
        self.assertEqual(self.db['schemaVersion'],8);self.assertEqual(self.db['costs'],[])
        after=self.post(self.db,self.cost(createdBy='Fałszywa osoba'))
        self.assertEqual(after['history'],self.db['history'])
        self.assertEqual(after['costs'][0]['createdBy'],'Technik');self.assertTrue(after['costs'][0]['createdAt'])
    def test_exact_reversal_keeps_both_entries(self):
        first=self.post(self.db,self.cost())
        correction=self.cost('K2',-12345,reversesId='K1');correction['description']='Błędna faktura'
        after=self.post(first,correction)
        self.assertEqual(sum(c['amountGrosz'] for c in after['costs']),0);self.assertEqual(len(after['costs']),2)
        with self.assertRaisesRegex(ValueError,'jeden raz'):self.post(after,self.cost('K3',-12345,reversesId='K1'))
    def test_no_edit_or_removal(self):
        first=self.post(self.db,self.cost())
        for removal in (False,True):
            changed=deepcopy(first)
            if removal:changed['costs']=[]
            else:changed['costs'][0]['description']='Nadpisano'
            with self.assertRaisesRegex(ValueError,'niezmienny'):app.apply_workflow(changed,first,app.DEFAULT_SERVICE)
    def test_invalid_money_or_unlinked_cost(self):
        for amount in (0,True,12.3,-123,10000000001):
            with self.subTest(amount=amount),self.assertRaises(ValueError):self.post(self.db,self.cost(amount=amount))
        wrong=self.cost();wrong['protocolId']='missing'
        with self.assertRaises(ValueError):self.post(self.db,wrong)
        draft=deepcopy(self.db);draft['history'][0]['protocolStatus']='draft'
        with self.assertRaises(ValueError):self.post(draft,self.cost())
    def test_wrong_or_backdated_reversal(self):
        first=self.post(self.db,self.cost())
        with self.assertRaises(ValueError):self.post(first,self.cost('K2',-12344,reversesId='K1'))
        correction=self.cost('K2',-12345,reversesId='K1');correction['date']='2025-12-31'
        with self.assertRaises(ValueError):self.post(first,correction)
        future=self.cost();future['date']=(date.today()+timedelta(days=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'przyszłej'):self.post(self.db,future)
    def test_concurrent_append_and_double_reversal(self):
        first=self.post(self.db,self.cost());second=deepcopy(self.db);second['costs'].append(self.cost('K2',5000))
        merged=app.merge_changed_rows(first,self.db,app.validate_database(second),{},'')
        saved=app.apply_workflow(merged,first,app.DEFAULT_SERVICE)
        self.assertEqual(sum(c['amountGrosz'] for c in saved['costs']),17345)
        reversed_once=self.post(first,self.cost('R1',-12345,reversesId='K1'))
        second=deepcopy(first);second['costs'].append(self.cost('R2',-12345,reversesId='K1'))
        merged=app.merge_changed_rows(reversed_once,first,app.validate_database(second),{},'')
        with self.assertRaisesRegex(ValueError,'jeden raz'):app.apply_workflow(merged,reversed_once,app.DEFAULT_SERVICE)

if __name__=='__main__':unittest.main()
