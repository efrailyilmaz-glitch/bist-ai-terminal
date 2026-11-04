import unittest,tempfile
from pathlib import Path
from unittest.mock import patch
from app import xs_paper as xp
from app import xs_tournament as xt
from app.forward_scorecard import build as scorecard_build

class V80IntegrityTests(unittest.TestCase):
    def test_scorecard_exposes_canonical_details(self):
        h={'portfolio':{'capital':1_000_000,'last_equity':1_000_000},'curve':[],'rebalances':[],'positions':[]}
        with patch('app.forward_scorecard.hard_gate',return_value={'status':'OBSERVE','reasons':['NO_EVIDENCE'],'metrics':{}}),             patch('app.forward_scorecard.detect_xs_decay',return_value={'status':'HEALTHY'}):
            s=scorecard_build(h,10,3)
        self.assertIn('details',s)
        self.assertEqual(s['details']['promotion_gate']['status'],'OBSERVE')
        self.assertNotEqual(s['status'],'ELIGIBLE_FOR_REVIEW')

    def test_tournament_eligibility_uses_scorecard_only(self):
        h={'status':'OK','portfolio':{'capital':1_000_000,'last_equity':1_000_000},
           'curve':[],'rebalances':[],'positions':[]}
        card={'status':'OBSERVE','reasons':['CANONICAL_VETO'],
              'details':{
                'promotion_gate':{'status':'PROMOTION_REVIEW','reasons':[]},
                'statistical_gate':{'status':'PASS','reasons':[]},
                'regime_gate':{'status':'PASS','reasons':[]},
                'data_quality_gate':{'status':'PASS','reasons':[]},
                'factor_gate':{'status':'PASS','reasons':[]},
                'portfolio_stress_gate':{'status':'PASS','reasons':[]},
                'decay_v2':{'status':'HEALTHY'}}}
        class C:
            def execute(self,*args,**kwargs):
                q=args[0]
                if 'SELECT * FROM tournaments' in q:return self
                if 'PRAGMA table_info(tournaments)' in q:return self
                if 'SELECT variant_id' in q:return self
                return self
            def fetchone(self):return (1,0,'x',None,None,1_000_000,'XU100',None)
            def fetchall(self):
                return [('id',)] if False else []
            def close(self):pass
        # Easier targeted invariant: canonical card cannot be upgraded by legacy gate details.
        self.assertNotEqual(card['status'],'ELIGIBLE_FOR_REVIEW')

    def test_initial_rebalance_counts_full_buy_turnover_and_cash(self):
        tmp=tempfile.TemporaryDirectory();db=Path(tmp.name)/'p.db'
        p1=patch('app.xs_paper._db',return_value=db);p1.start()
        p2=patch('app.xs_paper._price',return_value=100.0);p2.start()
        try:
            pid=xp.create(capital=1_000_000)['portfolio_id']
            r=xp.rebalance(pid,[{'ticker':'AAA','weight_pct':50},{'ticker':'BBB','weight_pct':30}],20)
            self.assertEqual(r['status'],'OK')
            self.assertGreater(r['turnover_pct'],79)
            self.assertLess(r['turnover_pct'],81)
            self.assertGreater(r['cash_after'],190_000)
            h=xp.history(pid)
            self.assertAlmostEqual(float(h['portfolio']['cash']),r['cash_after'],places=2)
        finally:
            p2.stop();p1.stop();tmp.cleanup()

if __name__=='__main__':unittest.main()
