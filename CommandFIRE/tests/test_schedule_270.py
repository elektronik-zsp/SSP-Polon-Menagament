import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
from copy import deepcopy
import server as app

class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.db=app.validate_database({'schemaVersion':5,'panels':[{'id':'C01','lastInspection':'2026-01-01'}],'faults':[],'history':[]})
    def plan(self,old,day='2026-10-19'):
        new=deepcopy(old);new['panels'][0].update(inspectionPlanDate=day,inspectionPlanAssignee='Technik',inspectionPlanNote='Próby czujek')
        return app.apply_workflow(app.validate_database(new),old,app.DEFAULT_SERVICE)
    def protocol(self,data,plan_id,positive=True):
        new=deepcopy(data);new['history'].append({'id':'H01','panelId':'C01','type':'Przegląd','date':'2026-10-19 10:00',
            'protocolStatus':'final','technician':'Technik','desc':'Wykonano kontrolę','result':'Pozytywny' if positive else 'Negatywny',
            'recom':'' if positive else 'Naprawa czujki','inspectionPlanId':plan_id,
            'checklist':[{'label':'Kontrola','result':'OK' if positive else 'Usterka','note':''}]})
        return app.apply_workflow(app.validate_database(new),data,app.DEFAULT_SERVICE)
    def test_plan_does_not_move_technical_due_date(self):
        planned=self.plan(self.db);p=planned['panels'][0]
        self.assertEqual(p['lastInspection'],'2026-01-01');self.assertTrue(p['inspectionPlanId'])
        self.assertIn('Data wizyty: — → 2026-10-19',planned['audit'][-1]['details'][0])
    def test_final_protocol_closes_exact_appointment(self):
        planned=self.plan(self.db);token=planned['panels'][0]['inspectionPlanId'];final=self.protocol(planned,token)
        self.assertEqual(final['panels'][0]['inspectionPlanDate'],'')
        self.assertEqual(final['history'][0]['inspectionPlanSnapshot']['inspectionPlanId'],token)
        self.assertEqual(final['panels'][0]['lastInspection'],'2026-10-19 10:00')
    def test_old_draft_cannot_close_rescheduled_appointment(self):
        planned=self.plan(self.db);old_id=planned['panels'][0]['inspectionPlanId']
        changed=self.plan(planned,'2026-10-22');new_id=changed['panels'][0]['inspectionPlanId']
        self.assertNotEqual(old_id,new_id)
        final=self.protocol(changed,old_id)
        self.assertEqual(final['panels'][0]['inspectionPlanDate'],'2026-10-22')
        self.assertEqual(final['panels'][0]['inspectionPlanId'],new_id)
    def test_negative_visit_keeps_old_positive_inspection(self):
        planned=self.plan(self.db);final=self.protocol(planned,planned['panels'][0]['inspectionPlanId'],False)
        self.assertEqual(final['panels'][0]['inspectionPlanDate'],'')
        self.assertEqual(final['panels'][0]['lastInspection'],'2026-01-01')
        self.assertEqual(final['panels'][0]['condition'],'Wymaga serwisu')
    def test_cancel_and_archive_protection(self):
        planned=self.plan(self.db);archived=deepcopy(planned);archived['panels'][0]['archived']=True
        with self.assertRaisesRegex(ValueError,'odwołaj'):app.apply_workflow(archived,planned,app.DEFAULT_SERVICE)
        cancelled=deepcopy(planned)
        for key in ('inspectionPlanDate','inspectionPlanAssignee','inspectionPlanNote','inspectionPlanId'):cancelled['panels'][0][key]=''
        result=app.apply_workflow(app.validate_database(cancelled),planned,app.DEFAULT_SERVICE)
        self.assertEqual(result['panels'][0]['inspectionPlanId'],'')
    def test_invalid_dates_and_id_tampering(self):
        for day in ('2026-02-30','2026-10-20T10:00','20261020'):
            with self.subTest(day=day),self.assertRaises(ValueError):self.plan(self.db,day)
        planned=self.plan(self.db);changed=deepcopy(planned);changed['panels'][0]['inspectionPlanId']='invented'
        with self.assertRaisesRegex(ValueError,'Identyfikator'):app.apply_workflow(changed,planned,app.DEFAULT_SERVICE)
    def test_schema5_migrates_without_data_loss(self):
        self.assertEqual(self.db['schemaVersion'],8)
        self.assertEqual(self.db['panels'][0]['inspectionPlanDate'],'')

if __name__=='__main__':unittest.main()
