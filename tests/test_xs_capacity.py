import unittest
from app.xs_capacity import assess

class XSCapacityTests(unittest.TestCase):
    def test_small_trade_is_clear(self):
        r=assess(50_000,0,100_000_000,25,price=100,high=101,low=99,adv_limit_pct=1)
        self.assertEqual(r['status'],'CLEAR')
        self.assertEqual(r['execution_horizon_days'],1)
    def test_large_trade_blocks_long_horizon(self):
        r=assess(5_000_000,0,20_000_000,45,price=100,high=104,low=96,adv_limit_pct=1)
        self.assertEqual(r['status'],'BLOCK')
        self.assertGreater(r['execution_horizon_days'],2)
        self.assertEqual(r['risk_multiplier'],0.0)
    def test_missing_adv_never_boosts(self):
        r=assess(100_000,0,0,30)
        self.assertEqual(r['status'],'UNKNOWN')
        self.assertLess(r['risk_multiplier'],1.0)

if __name__=='__main__':unittest.main()
