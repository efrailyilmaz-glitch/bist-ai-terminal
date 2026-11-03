import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from app import xs_scheduler as s
from app import xs_tournament as t

class XSSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.tdb=Path(self.tmp.name)/'t.db';self.pdb=Path(self.tmp.name)/'p.db'
        self.a=patch('app.xs_tournament._db',return_value=self.tdb);self.a.start()
        self.b=patch('app.xs_paper._db',return_value=self.pdb);self.b.start()
        self.c=patch('app.xs_paper._price',return_value=100.0);self.c.start()
        self.tid=t.create()['tournament_id'];t.start(self.tid)
        s.configure(self.tid,enabled=True,rebalance_every_days=5)
    def tearDown(self):
        self.a.stop();self.b.stop();self.c.stop();self.tmp.cleanup()
    def test_waits_without_model_and_never_falls_back(self):
        with patch('app.xs_scheduler.current_ranking',return_value={'status':'ADAPTER_UNAVAILABLE'}),patch('app.xs_scheduler.xs_tournament.mark_all',return_value={'status':'OK','rows':[]}):
            r=s.run_once(self.tid,today='2026-11-03',force_rebalance=True)
        self.assertEqual(r['status'],'WAIT_MODEL')
        self.assertEqual(r['ranking_status'],'ADAPTER_UNAVAILABLE')
    def test_rebalances_all_variants(self):
        ranking={'status':'OK','as_of':'2026-11-03','symbols':20,'rows':[{'ticker':f'T{i}','score':20-i,'price':100,'value_turnover':100000000} for i in range(20)]}
        built={'status':'OK','rows':[{'ticker':'AAA','weight_pct':50},{'ticker':'BBB','weight_pct':50}],'annual_volatility_pct':20,'avg_correlation':.2,'liquidity_flags':[]}
        with patch('app.xs_scheduler.current_ranking',return_value=ranking),patch('app.xs_scheduler.construct',return_value=built),patch('app.xs_scheduler.xs_tournament.mark_all',return_value={'status':'OK','rows':[]}),patch('app.xs_scheduler.xs_tournament.rebalance_variant',return_value={'status':'OK'}) as rb:
            r=s.run_once(self.tid,today='2026-11-03',force_rebalance=True)
        self.assertEqual(r['status'],'REBALANCED')
        self.assertEqual(rb.call_count,3)
    def test_same_day_mark_not_duplicated(self):
        with patch('app.xs_scheduler.current_ranking',return_value={'status':'ADAPTER_UNAVAILABLE'}),patch('app.xs_scheduler.xs_tournament.mark_all',return_value={'status':'OK','rows':[]}) as mark:
            s.run_once(self.tid,today='2026-11-03',force_rebalance=True)
            s.run_once(self.tid,today='2026-11-03',force_rebalance=False)
        self.assertEqual(mark.call_count,1)

if __name__=='__main__':unittest.main()
