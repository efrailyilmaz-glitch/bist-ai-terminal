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
    def test_missing_data_derisks(self):
        d=execution_diagnostics({},100,100,10,'BUY')
        self.assertEqual(d['status'],'UNKNOWN');self.assertLess(d['risk_multiplier'],1)

if __name__=='__main__':unittest.main()
