import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import pandas as pd
from app import pit_universe as pu
from app import model_registry as mr

class PITUniverseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.udb=Path(self.tmp.name)/'u.db';self.mdb=Path(self.tmp.name)/'m.db'
        self.a=patch('app.pit_universe._db',return_value=self.udb);self.a.start()
        self.b=patch('app.model_registry._db',return_value=self.mdb);self.b.start()
    def tearDown(self):
        self.a.stop();self.b.stop();self.tmp.cleanup()
    def test_no_complete_dataset_stays_proxy(self):
        s=pu.dataset_status()
        self.assertEqual(s['status'],'CURRENT_UNIVERSE_PROXY')
        r=pu.training_universe(['AAA','BBB'],10)
        self.assertEqual(r['integrity']['status'],'CAUTION')
    def test_complete_dataset_enables_pit(self):
        pu.register_dataset([
            {'ticker':'AAA','start_date':'2020-01-01','end_date':None},
            {'ticker':'OLD','start_date':'2018-01-01','end_date':'2021-06-30'}],
            'OFFICIAL_TEST','COMPLETE','2018-01-01','2026-11-04','hash1')
        r=pu.training_universe(['AAA'],10)
        self.assertEqual(r['integrity']['status'],'PASS')
        self.assertIn('OLD',r['tickers'])
        self.assertTrue(pu.date_allowed('OLD','2020-01-01',r['integrity']['dataset_id']))
        self.assertFalse(pu.date_allowed('OLD','2022-01-01',r['integrity']['dataset_id']))
    def test_filter_frame_respects_membership(self):
        pu.register_dataset([{'ticker':'AAA','start_date':'2020-01-02','end_date':'2020-01-03'}],
            'OFFICIAL_TEST','COMPLETE','2020-01-01','2020-12-31','hash2')
        integ=pu.training_universe(['AAA'],10)['integrity']
        f=pd.DataFrame({'x':[1,2,3]},index=['2020-01-01','2020-01-02','2020-01-03'])
        out=pu.filter_frame('AAA',f,integ)
        self.assertEqual(list(out.index),['2020-01-02','2020-01-03'])
    def test_model_data_fingerprint_changes_with_universe(self):
        base={'model_name':'X','model_version':'1','seed':1,'features':['a'],'train_rows':100,'train_dates':50,'train_cutoff':'2026-10-01','as_of':'2026-11-01','symbols':20}
        a=mr.register({**base,'universe_integrity':{'dataset_id':1,'source_hash':'A'}})
        b=mr.register({**base,'universe_integrity':{'dataset_id':2,'source_hash':'B'}})
        self.assertNotEqual(a['data_fingerprint'],b['data_fingerprint'])
        self.assertNotEqual(a['model_fingerprint'],b['model_fingerprint'])

if __name__=='__main__':unittest.main()
