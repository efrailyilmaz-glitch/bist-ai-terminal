import unittest, tempfile
from pathlib import Path
from unittest.mock import patch
from app import xs_paper as xp

class XSPaperTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.p=Path(self.tmp.name)/'xs.db'
        self.dbp=patch('app.xs_paper._db',return_value=self.p);self.dbp.start()
        self.pr=patch('app.xs_paper._price',side_effect=lambda t:100.0 if t!='XU100' else 10000.0);self.pr.start()
    def tearDown(self):
        self.dbp.stop();self.pr.stop();self.tmp.cleanup()
    def test_create_rebalance_and_history(self):
        pid=xp.create(capital=1_000_000)['portfolio_id']
        r=xp.rebalance(pid,[{'ticker':'AAA','weight_pct':50},{'ticker':'BBB','weight_pct':50}],one_way_cost_bps=20)
        self.assertEqual(r['status'],'OK')
        self.assertGreater(r['cost'],0)
        h=xp.history(pid)
        self.assertEqual(len(h['positions']),2)
        self.assertEqual(len(h['rebalances']),1)
    def test_second_same_rebalance_low_turnover(self):
        pid=xp.create()['portfolio_id']
        rows=[{'ticker':'AAA','weight_pct':50},{'ticker':'BBB','weight_pct':50}]
        xp.rebalance(pid,rows,20)
        r=xp.rebalance(pid,rows,20)
        self.assertAlmostEqual(r['turnover_pct'],0.0,places=2)

if __name__=='__main__':unittest.main()
