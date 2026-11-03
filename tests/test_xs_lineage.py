import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from app import xs_paper as xp
from app import model_registry as mr

class LineageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.pdb=Path(self.tmp.name)/'p.db';self.mdb=Path(self.tmp.name)/'m.db'
        self.a=patch('app.xs_paper._db',return_value=self.pdb);self.a.start()
        self.b=patch('app.model_registry._db',return_value=self.mdb);self.b.start()
        self.c=patch('app.xs_paper._price',return_value=100.0);self.c.start()
    def tearDown(self):
        self.a.stop();self.b.stop();self.c.stop();self.tmp.cleanup()
    def test_rebalance_links_model_artifact(self):
        art=mr.register({'model_name':'X','model_version':'1','seed':56,'features':['a'],'train_rows':100,'train_dates':50,'train_cutoff':'2026-10-01','as_of':'2026-11-01'})
        pid=xp.create()['portfolio_id']
        r=xp.rebalance(pid,[{'ticker':'AAA','weight_pct':50},{'ticker':'BBB','weight_pct':50}],20,
            {'model_artifact':art,'ranking_as_of':'2026-11-01','ranking_snapshot':[{'ticker':'AAA','score':1.0}]})
        self.assertEqual(r['status'],'OK')
        h=xp.history(pid)
        rid=h['rebalances'][0]['id']
        lin=xp.lineage(rid)
        self.assertEqual(lin['model_artifact']['status'],'OK')
        self.assertEqual(lin['model_artifact']['row']['id'],art['registry_id'])
        self.assertEqual(lin['ranking_snapshot'][0]['ticker'],'AAA')

if __name__=='__main__':unittest.main()
