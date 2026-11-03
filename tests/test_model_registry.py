import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from app import model_registry as mr

class ModelRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)/'m.db'
        self.pat=patch('app.model_registry._db',return_value=self.p);self.pat.start()
    def tearDown(self):
        self.pat.stop();self.tmp.cleanup()
    def test_deterministic_fingerprints(self):
        meta={'model_name':'X','model_version':'1','seed':56,'features':['a','b'],'train_rows':100,'train_dates':50,'train_cutoff':'2026-10-01','as_of':'2026-11-01','symbols':20,'label':'y','params':{'x':1}}
        a=mr.register(meta);b=mr.register(meta)
        self.assertEqual(a['model_fingerprint'],b['model_fingerprint'])
        self.assertEqual(a['feature_schema_hash'],b['feature_schema_hash'])
    def test_history_and_get(self):
        r=mr.register({'model_name':'X','model_version':'1','seed':1,'features':['a']})
        h=mr.history()
        self.assertEqual(h['status'],'OK')
        self.assertEqual(h['rows'][0]['id'],r['registry_id'])
        g=mr.get(r['registry_id'])
        self.assertEqual(g['status'],'OK')

if __name__=='__main__':unittest.main()
