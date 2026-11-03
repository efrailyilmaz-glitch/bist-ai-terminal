import unittest,tempfile,sqlite3
from pathlib import Path
from unittest.mock import patch
from app import xs_paper as xp
from app import model_registry as mr

class LineageHashChainTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.pdb=Path(self.tmp.name)/'p.db';self.mdb=Path(self.tmp.name)/'m.db'
        self.a=patch('app.xs_paper._db',return_value=self.pdb);self.a.start()
        self.b=patch('app.model_registry._db',return_value=self.mdb);self.b.start()
        self.c=patch('app.xs_paper._price',return_value=100.0);self.c.start()
    def tearDown(self):
        self.a.stop();self.b.stop();self.c.stop();self.tmp.cleanup()
    def make_rebalance(self):
        art=mr.register({'model_name':'X','model_version':'1','seed':56,'features':['a'],'train_rows':100,'train_dates':50,'train_cutoff':'2026-10-01','as_of':'2026-11-01'})
        pid=xp.create()['portfolio_id']
        xp.rebalance(pid,[{'ticker':'AAA','weight_pct':50},{'ticker':'BBB','weight_pct':50}],20,
            {'model_artifact':art,'ranking_as_of':'2026-11-01','ranking_snapshot':[{'ticker':'AAA','score':1.0}]})
        return pid
    def test_chain_passes(self):
        self.make_rebalance()
        v=xp.verify_lineage_ledger()
        self.assertEqual(v['status'],'PASS')
        self.assertEqual(v['rows'],1)
    def test_tampering_is_detected(self):
        self.make_rebalance()
        c=sqlite3.connect(self.pdb)
        c.execute("UPDATE rebalances SET model_fingerprint='tampered' WHERE id=1");c.commit();c.close()
        v=xp.verify_lineage_ledger()
        self.assertEqual(v['status'],'FAIL')
        self.assertIn(1,v['bad_ids'])

if __name__=='__main__':unittest.main()
