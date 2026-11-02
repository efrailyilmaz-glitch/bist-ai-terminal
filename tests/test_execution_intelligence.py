import unittest
from app.execution_intelligence import execution_diagnostics,slippage_price

class ExecutionIntelligenceTests(unittest.TestCase):
    def q(self,high=101,low=99,volume=1_000_000):
        return {'high':high,'low':low,'volume':volume}
    def test_slippage_never_better_than_base(self):
        d=execution_diagnostics(self.q(),100,100,10,'BUY')
        self.assertGreaterEqual(d['effective_slippage_bps'],10)
        self.assertGreater(slippage_price(100,'BUY',d['effective_slippage_bps']),100)
        self.assertLess(slippage_price(100,'SELL',d['effective_slippage_bps']),100)
    def test_high_participation_blocks(self):
        d=execution_diagnostics(self.q(volume=1000),100,100,10,'BUY')
        self.assertEqual(d['status'],'BLOCK');self.assertEqual(d['risk_multiplier'],0)
        self.assertIn('EXTREME_PARTICIPATION',d['flags'])
    def test_high_range_worsens_cost(self):
        calm=execution_diagnostics(self.q(high=100.5,low=99.5),100,100,10,'BUY')
        wild=execution_diagnostics(self.q(high=104,low=96),100,100,10,'BUY')
        self.assertGreater(wild['effective_slippage_bps'],calm['effective_slippage_bps'])
    def test_quadratic_volume_share_and_fillability(self):
        low=execution_diagnostics(self.q(volume=1_000_000),1000,100,10,'BUY')
        high=execution_diagnostics(self.q(volume=1_000_000),25000,100,10,'BUY')
        self.assertGreater(high['volume_share_impact_bps'],low['volume_share_impact_bps'])
        self.assertEqual(high['execution_horizon_bars'],1)
        over=execution_diagnostics(self.q(volume=1_000_000),60000,100,10,'BUY')
        self.assertGreater(over['execution_horizon_bars'],1)
        self.assertLess(over['expected_fill_ratio_pct'],100)
    def test_observed_spread_can_only_worsen_cost(self):
        q=self.q();q['bid']=99.9;q['ask']=100.1
        a=execution_diagnostics(self.q(),100,100,10,'BUY')
        b=execution_diagnostics(q,100,100,10,'BUY')
        self.assertGreater(b['effective_slippage_bps'],a['effective_slippage_bps'])
        self.assertGreater(b['spread_bps'],0)
    def test_missing_data_derisks(self):
        d=execution_diagnostics({},100,100,10,'BUY')
        self.assertEqual(d['status'],'UNKNOWN');self.assertLess(d['risk_multiplier'],1)

if __name__=='__main__':unittest.main()
