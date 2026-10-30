import unittest
from app.meta_portfolio import arena_regime,allocate

class MetaPortfolioTests(unittest.TestCase):
    def rows(self):
        return [
          {'id':'tsmomentum','name':'TSM','decay':{'status':'STABLE'}},
          {'id':'donchian55','name':'DON','decay':{'status':'STABLE'}},
          {'id':'meanrev','name':'MR','decay':{'status':'STABLE'}},
          {'id':'kama_regime','name':'KAMA','decay':{'status':'WATCH'}},
          {'id':'codex','name':'CODEX','decay':{'status':'DECAY'}},
        ]
    def ranking(self):
        return [
          {'id':'tsmomentum','status':'ELIGIBLE','score':8},
          {'id':'donchian55','status':'ELIGIBLE','score':7},
          {'id':'meanrev','status':'ELIGIBLE','score':6},
          {'id':'kama_regime','status':'ELIGIBLE','score':5},
          {'id':'codex','status':'ELIGIBLE','score':20},
        ]
    def test_regime_classification(self):
        self.assertEqual(arena_regime({'breadth_pct':70},{'cash_adjusted_pct':4}),'BULL_TREND')
        self.assertEqual(arena_regime({'breadth_pct':30},{'cash_adjusted_pct':1}),'RISK_OFF')
    def test_decay_is_excluded_and_cap_respected(self):
        x=allocate(self.rows(),self.ranking(),'BULL_TREND')
        ids={r['id'] for r in x['allocations']}
        self.assertNotIn('codex',ids)
        self.assertTrue(all(r['weight_pct']<=25 for r in x['allocations']))
        self.assertGreaterEqual(x['cash_weight_pct'],20)
    def test_risk_off_keeps_large_cash_floor(self):
        x=allocate(self.rows(),self.ranking(),'RISK_OFF')
        self.assertGreaterEqual(x['cash_weight_pct'],70)
    def test_no_eligible_means_all_cash(self):
        x=allocate(self.rows(),[{'id':'tsmomentum','status':'OBSERVE','score':99}],'BULL_TREND')
        self.assertEqual(x['status'],'ALL_CASH');self.assertEqual(x['cash_weight_pct'],100)

if __name__=='__main__':unittest.main()
